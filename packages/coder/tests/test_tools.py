"""Tests for LangChain coding tools.

Covers: TS-14-13 through TS-14-16, TS-14-28 (tool behavior).
Edge cases: TS-14-E3, TS-14-E4, TS-14-E10.
Property tests: TS-14-P3.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from coder.tools import create_coding_tools
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.fixture()
def worktree_dir(tmp_path: Path) -> Path:
    """Create a temporary worktree directory for tool tests."""
    wt = tmp_path / "worktree"
    wt.mkdir()
    return wt


@pytest.fixture()
def coding_tools(worktree_dir: Path) -> dict:
    """Create coding tools bound to a temporary worktree."""
    return create_coding_tools(worktree_dir)


# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestReadFile:
    """TS-14-13: read_file tool returns file contents.

    Requirement: 14-REQ-4.1
    """

    def test_reads_file_contents(
        self, coding_tools: dict, worktree_dir: Path
    ) -> None:
        """Verify read_file reads from worktree."""
        src = worktree_dir / "src"
        src.mkdir()
        (src / "main.py").write_text("hello")
        result = coding_tools["read_file"].invoke(
            {"path": "src/main.py"}
        )
        assert result == "hello"


class TestWriteFile:
    """TS-14-14: write_file tool creates file and parents.

    Requirement: 14-REQ-4.2
    """

    def test_creates_file_and_parents(
        self, coding_tools: dict, worktree_dir: Path
    ) -> None:
        """Verify write_file creates directories and file."""
        coding_tools["write_file"].invoke(
            {"path": "src/new/main.py", "content": "content"}
        )
        created = worktree_dir / "src" / "new" / "main.py"
        assert created.read_text() == "content"


class TestRunCommand:
    """TS-14-15: run_command tool executes in worktree.

    Requirement: 14-REQ-4.3
    """

    def test_executes_in_worktree(
        self, coding_tools: dict, worktree_dir: Path
    ) -> None:
        """Verify run_command executes in the worktree directory."""
        result = coding_tools["run_command"].invoke(
            {"command": "pwd"}
        )
        assert str(worktree_dir) in result


class TestPathTraversal:
    """TS-14-16: Path traversal rejected by tools.

    Requirement: 14-REQ-4.5
    """

    def test_dotdot_traversal_blocked(
        self, coding_tools: dict
    ) -> None:
        """Verify .. path escaping is blocked."""
        result = coding_tools["read_file"].invoke(
            {"path": "../../etc/passwd"}
        )
        assert (
            "error" in result.lower() or "denied" in result.lower()
        )

    def test_absolute_path_blocked(
        self, coding_tools: dict
    ) -> None:
        """Verify absolute paths outside worktree are blocked."""
        result = coding_tools["read_file"].invoke(
            {"path": "/etc/passwd"}
        )
        assert (
            "error" in result.lower() or "denied" in result.lower()
        )


class TestListDirectory:
    """TS-14-28: list_directory tool returns listing.

    Requirement: 14-REQ-4.4
    """

    def test_lists_files_and_dirs(
        self, coding_tools: dict, worktree_dir: Path
    ) -> None:
        """Verify list_directory lists files and directories."""
        src = worktree_dir / "src"
        src.mkdir()
        (src / "main.py").write_text("hello")
        (src / "lib").mkdir()
        result = coding_tools["list_directory"].invoke({"path": "src"})
        assert "main.py" in result
        assert "lib" in result


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestCommandTimeout:
    """TS-14-E3: Command timeout returns failure.

    Requirement: 14-REQ-4.E1
    """

    def test_timeout_returns_error(
        self, coding_tools: dict
    ) -> None:
        """Verify command timeout produces error result."""
        result = coding_tools["run_command"].invoke(
            {"command": "sleep 60", "timeout": 1}
        )
        assert "timeout" in result.lower()


class TestSymlinkWrite:
    """TS-14-E4: Symlink write rejected.

    Requirement: 14-REQ-4.E3
    """

    def test_symlink_write_blocked(
        self, coding_tools: dict, worktree_dir: Path
    ) -> None:
        """Verify writing to symlinks is blocked."""
        target = worktree_dir / "target.txt"
        target.write_text("original")
        link = worktree_dir / "link.txt"
        os.symlink(str(target), str(link))
        result = coding_tools["write_file"].invoke(
            {"path": "link.txt", "content": "x"}
        )
        assert "error" in result.lower()


class TestBinaryFileRead:
    """TS-14-E10: Binary file read returns error.

    Requirement: 14-REQ-4.E2
    """

    def test_binary_file_returns_error(
        self, coding_tools: dict, worktree_dir: Path
    ) -> None:
        """Verify read_file returns error for binary files."""
        (worktree_dir / "image.png").write_bytes(
            b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        )
        result = coding_tools["read_file"].invoke(
            {"path": "image.png"}
        )
        assert "binary" in result.lower() or "error" in result.lower()


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestPropertyPathContainment:
    """TS-14-P3: Path containment.

    Property 3 from design.md.
    Validates: 14-REQ-4.5

    All tool paths resolve within the worktree.
    """

    @given(
        segments=st.lists(
            st.sampled_from(
                ["..", ".", "etc", "passwd", "src", "tmp"]
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_path_containment(
        self, segments: list[str]
    ) -> None:
        """Paths with traversal attempts are rejected or contained."""
        wt = Path(tempfile.mkdtemp()) / "worktree"
        wt.mkdir()
        tools = create_coding_tools(wt)
        path = "/".join(segments)
        result = tools["read_file"].invoke({"path": path})
        # Either the tool rejects the path or any accessed file
        # is within the worktree boundary.
        if "error" not in result.lower() and "denied" not in result.lower():
            resolved = (wt / path).resolve()
            assert str(resolved).startswith(
                str(wt.resolve())
            ), f"Path {path} resolved to {resolved} outside worktree"
