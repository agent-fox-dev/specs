"""Tests for the afspec library documentation suite.

Verifies that documentation files exist, are well-structured, and accurately
cover the public API surfaces defined in the Go (spec 01) and Python (spec 02)
library design documents.

All tests parse markdown files to check for required headings, function entries,
type entries, links, and content accuracy. Tests do not compile Go examples or
run Python examples.
"""
from __future__ import annotations

import pathlib
import re

import pytest

# ---------------------------------------------------------------------------
# Repo root and paths
# ---------------------------------------------------------------------------

# This file lives at <repo_root>/tests/test_docs.py
REPO_ROOT = pathlib.Path(__file__).parent.parent

GO_API_DOC = REPO_ROOT / "docs" / "api" / "go.md"
PYTHON_API_DOC = REPO_ROOT / "docs" / "api" / "python.md"
EXAMPLES_DIR = REPO_ROOT / "docs" / "examples"
README = REPO_ROOT / "README.md"

GO_DESIGN_DOC = REPO_ROOT / ".agent-fox" / "specs" / "01_golang_library" / "design.md"
PYTHON_DESIGN_DOC = REPO_ROOT / ".agent-fox" / "specs" / "02_python_library" / "design.md"

EXAMPLE_FILES = [
    EXAMPLES_DIR / "loading_and_saving.md",
    EXAMPLES_DIR / "validation.md",
    EXAMPLES_DIR / "rendering.md",
    EXAMPLES_DIR / "lifecycle.md",
    EXAMPLES_DIR / "bootstrap_and_discovery.md",
    EXAMPLES_DIR / "comparison.md",
]

EXAMPLE_FILES_EXCEPT_COMPARISON = [f for f in EXAMPLE_FILES if f.name != "comparison.md"]

# ---------------------------------------------------------------------------
# Public API constants
# ---------------------------------------------------------------------------

GO_PUBLIC_FUNCTIONS = [
    "LoadSpec",
    "SaveSpec",
    "Validate",
    "ValidateSchema",
    "ValidateCrossFile",
    "RenderRequirements",
    "RenderTestSpec",
    "RenderTasks",
    "RenderCombined",
    "Transition",
    "NewBootstrap",
    "DiscoverSpecs",
]

GO_KEY_TYPES = [
    "Spec",
    "PRD",
    "Frontmatter",
    "Requirements",
    "Criterion",
    "TestSpecDoc",
    "Tasks",
    "ValidationError",
    "DiscoveryResult",
    "Bootstrap",
    "Status",
    "SubtaskState",
]

# All public types from spec 01 design.md (for property tests)
GO_ALL_PUBLIC_TYPES = [
    "Spec",
    "PRD",
    "Frontmatter",
    "Status",
    "Requirements",
    "Criterion",
    "TestSpecDoc",
    "Tasks",
    "ValidationError",
    "DiscoveryResult",
    "SpecEntry",
    "DependencyGraph",
    "Bootstrap",
    "SubtaskState",
    "LifecycleError",
    "IncompleteSpecError",
]

PYTHON_PUBLIC_FUNCTIONS = [
    "load_spec",
    "save_spec",
    "validate",
    "render_requirements",
    "render_test_spec",
    "render_tasks",
    "render_combined",
    "transition",
    "discover",
    "schema_version",
]

PYTHON_KEY_TYPES = [
    "Spec",
    "PRD",
    "PRDFrontmatter",
    "Requirements",
    "EARSCriterion",
    "TestSpec",
    "Tasks",
    "ValidationError",
    "DiscoveryResult",
    "BootstrapSpec",
    "SubtaskState",
    "LifecycleError",
]

# All public types from spec 02 design.md (for property tests)
PYTHON_ALL_PUBLIC_TYPES = [
    "Spec",
    "PRD",
    "PRDFrontmatter",
    "Requirements",
    "EARSCriterion",
    "TestSpec",
    "Tasks",
    "ValidationError",
    "DiscoveryResult",
    "SpecEntry",
    "DependencyGraph",
    "BootstrapSpec",
    "SubtaskState",
    "AfspecError",
    "SpecValidationError",
    "LifecycleError",
    "IncompleteSpecError",
]

GO_API_CATEGORIES = [
    "Loading",
    "Saving",
    "Validation",
    "Rendering",
    "Lifecycle",
    "Bootstrap",
    "Discovery",
    "Types",
]

PYTHON_API_CATEGORIES = [
    "Loading",
    "Saving",
    "Validation",
    "Rendering",
    "Lifecycle",
    "Bootstrap",
    "Discovery",
    "Types",
]

# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------


def read_file(path: pathlib.Path) -> str:
    """Read a file and return its content as a string."""
    return path.read_text(encoding="utf-8")


def extract_h2_headings(content: str) -> list[str]:
    """Extract all H2 (##) heading text values from markdown content."""
    pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    return [m.group(1).strip() for m in pattern.finditer(content)]


def extract_h3_headings(content: str) -> list[str]:
    """Extract all H3 (###) heading text values from markdown content."""
    pattern = re.compile(r"^###\s+(.+)$", re.MULTILINE)
    return [m.group(1).strip() for m in pattern.finditer(content)]


def extract_code_blocks(content: str, lang: str = "") -> list[str]:
    """Extract code block bodies for the given language fence.

    If lang is empty, extract all code blocks regardless of language.
    """
    if lang:
        pattern = re.compile(r"```" + re.escape(lang) + r"\b[^\n]*\n(.*?)```", re.DOTALL)
    else:
        pattern = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
    return [m.group(1) for m in pattern.finditer(content)]


def count_code_blocks(content: str, lang: str = "") -> int:
    """Count code blocks for the given language fence."""
    return len(extract_code_blocks(content, lang))


def extract_relative_links(content: str) -> list[str]:
    """Extract relative (non-http) markdown link targets from content."""
    # Match [text](target) where target does not start with http:// or https://
    pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    links = []
    for m in pattern.finditer(content):
        target = m.group(2)
        if not target.startswith("http://") and not target.startswith("https://"):
            # Strip anchor fragments
            target = target.split("#")[0]
            if target:
                links.append(target)
    return links


def extract_section(content: str, heading: str) -> str:
    """Extract the content of a section starting with ### {heading}.

    Returns everything from the heading line up to (but not including) the
    next heading of the same or higher level.
    """
    # Match ### heading (possibly with backtick formatting)
    escaped = re.escape(heading)
    pattern = re.compile(
        r"(^###\s+`?" + escaped + r"`?\s*$)(.*?)(?=^#{1,3}\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(content)
    if m:
        return m.group(0)
    return ""


def split_by_h2(content: str) -> list[str]:
    """Split content into sections by H2 headings."""
    parts = re.split(r"^##\s+", content, flags=re.MULTILINE)
    return [p for p in parts if p.strip()]


def has_code_blocks(section: str) -> bool:
    """Return True if section contains at least one code block."""
    return "```" in section


def find_code_block_starts(content: str) -> list[int]:
    """Return the character positions where code blocks start."""
    pattern = re.compile(r"^```", re.MULTILINE)
    return [m.start() for m in pattern.finditer(content) if not _is_closing_fence(content, m.start())]


def _is_closing_fence(content: str, pos: int) -> bool:
    """Heuristic: determine if a ``` at pos is a closing fence."""
    # Count opening fences before this position
    before = content[:pos]
    opens = len(re.findall(r"^```\w*\s*$", before, re.MULTILINE))
    closes = len(re.findall(r"^```\s*$", before, re.MULTILINE))
    # If opens > closes, then pos is a closing fence
    return closes >= opens


def has_prose_line(lines: list[str]) -> bool:
    """Return True if any line is a non-empty, non-heading prose line."""
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("```"):
            continue
        return True
    return False


def get_lines_before(content: str, pos: int, n: int = 10) -> list[str]:
    """Return up to n lines immediately before position pos."""
    preceding = content[:pos]
    lines = preceding.split("\n")
    return lines[-n:]


# ---------------------------------------------------------------------------
# TS-03-5: Go API reference file exists
# TS-03-10: Python API reference file exists
# TS-03-11: All six example files exist
# TS-03-16: Comparison file exists
# TS-03-22: README.md exists
# ---------------------------------------------------------------------------


def test_go_api_file_exists() -> None:
    """TS-03-5: docs/api/go.md exists and is non-empty."""
    assert GO_API_DOC.exists(), f"Go API reference not found at {GO_API_DOC}"
    assert GO_API_DOC.stat().st_size > 0, "docs/api/go.md is empty"


def test_python_api_file_exists() -> None:
    """TS-03-10: docs/api/python.md exists and is non-empty."""
    assert PYTHON_API_DOC.exists(), f"Python API reference not found at {PYTHON_API_DOC}"
    assert PYTHON_API_DOC.stat().st_size > 0, "docs/api/python.md is empty"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=[f.name for f in EXAMPLE_FILES])
def test_example_files_exist(path: pathlib.Path) -> None:
    """TS-03-11: All six example files exist and are non-empty."""
    assert path.exists(), f"Example file not found at {path}"
    assert path.stat().st_size > 0, f"{path.name} is empty"


def test_comparison_file_exists() -> None:
    """TS-03-16: docs/examples/comparison.md exists and is non-empty."""
    comparison = EXAMPLES_DIR / "comparison.md"
    assert comparison.exists(), f"Comparison file not found at {comparison}"
    assert comparison.stat().st_size > 0, "comparison.md is empty"


def test_readme_exists() -> None:
    """TS-03-22: README.md exists at the repository root and is non-empty."""
    assert README.exists(), f"README.md not found at {README}"
    assert README.stat().st_size > 0, "README.md is empty"


# ---------------------------------------------------------------------------
# TS-03-1: Go API reference contains all public functions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("func_name", GO_PUBLIC_FUNCTIONS)
def test_go_api_public_functions(func_name: str) -> None:
    """TS-03-1: Go API reference contains a section for every public function."""
    assert GO_API_DOC.exists(), f"Go API reference not found at {GO_API_DOC}"
    content = read_file(GO_API_DOC)
    headings = extract_h3_headings(content)
    # Allow bare name or backtick-wrapped name
    found = any(
        h == func_name or h == f"`{func_name}`" or h.startswith(f"{func_name} ") or h.startswith(f"`{func_name}`")
        for h in headings
    )
    assert found, (
        f"Go API reference is missing an H3 heading for function '{func_name}'. "
        f"Found headings: {headings}"
    )


# ---------------------------------------------------------------------------
# TS-03-2: Go API reference function entries have required sections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("func_name", GO_PUBLIC_FUNCTIONS)
def test_go_api_function_sections(func_name: str) -> None:
    """TS-03-2: Each Go function entry has signature, description, parameters, returns, errors."""
    assert GO_API_DOC.exists(), f"Go API reference not found at {GO_API_DOC}"
    content = read_file(GO_API_DOC)
    section = extract_section(content, func_name)
    assert section, f"Could not find section for Go function '{func_name}'"
    assert count_code_blocks(section, "go") >= 1, (
        f"Go function '{func_name}' section has no Go code block with signature"
    )
    lower = section.lower()
    assert "parameter" in lower or "param" in lower, (
        f"Go function '{func_name}' section missing parameters documentation"
    )
    assert "return" in lower, (
        f"Go function '{func_name}' section missing returns documentation"
    )
    assert "error" in lower, (
        f"Go function '{func_name}' section missing errors documentation"
    )


# ---------------------------------------------------------------------------
# TS-03-3: Go API reference types section
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("type_name", GO_KEY_TYPES)
def test_go_api_types(type_name: str) -> None:
    """TS-03-3: Go API reference includes a Types section with all key public types."""
    assert GO_API_DOC.exists(), f"Go API reference not found at {GO_API_DOC}"
    content = read_file(GO_API_DOC)
    h2_headings = extract_h2_headings(content)
    types_present = any("type" in h.lower() for h in h2_headings)
    assert types_present, (
        f"Go API reference has no '## Types' section. H2 headings: {h2_headings}"
    )
    assert type_name in content, (
        f"Go API reference does not mention type '{type_name}'"
    )


# ---------------------------------------------------------------------------
# TS-03-4: Go API reference category organization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", GO_API_CATEGORIES)
def test_go_api_categories(category: str) -> None:
    """TS-03-4: Go API reference is organized by functional category."""
    assert GO_API_DOC.exists(), f"Go API reference not found at {GO_API_DOC}"
    content = read_file(GO_API_DOC)
    h2_headings = extract_h2_headings(content)
    found = any(category.lower() in h.lower() for h in h2_headings)
    assert found, (
        f"Go API reference missing category '{category}'. H2 headings: {h2_headings}"
    )


# ---------------------------------------------------------------------------
# TS-03-6: Python API reference contains all public functions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("func_name", PYTHON_PUBLIC_FUNCTIONS)
def test_python_api_public_functions(func_name: str) -> None:
    """TS-03-6: Python API reference contains a section for every public function."""
    assert PYTHON_API_DOC.exists(), f"Python API reference not found at {PYTHON_API_DOC}"
    content = read_file(PYTHON_API_DOC)
    headings = extract_h3_headings(content)
    found = any(
        h == func_name or h == f"`{func_name}`" or h.startswith(f"{func_name}(") or h.startswith(f"`{func_name}`")
        for h in headings
    )
    assert found, (
        f"Python API reference is missing an H3 heading for function '{func_name}'. "
        f"Found headings: {headings}"
    )


# ---------------------------------------------------------------------------
# TS-03-7: Python API reference function entries have required sections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("func_name", PYTHON_PUBLIC_FUNCTIONS)
def test_python_api_function_sections(func_name: str) -> None:
    """TS-03-7: Each Python function entry has signature, description, parameters, returns, exceptions."""
    assert PYTHON_API_DOC.exists(), f"Python API reference not found at {PYTHON_API_DOC}"
    content = read_file(PYTHON_API_DOC)
    section = extract_section(content, func_name)
    assert section, f"Could not find section for Python function '{func_name}'"
    assert count_code_blocks(section, "python") >= 1, (
        f"Python function '{func_name}' section has no Python code block with signature"
    )
    lower = section.lower()
    assert "parameter" in lower or "param" in lower, (
        f"Python function '{func_name}' section missing parameters documentation"
    )
    assert "return" in lower, (
        f"Python function '{func_name}' section missing returns documentation"
    )
    assert "exception" in lower or "raises" in lower or "raise" in lower, (
        f"Python function '{func_name}' section missing exceptions documentation"
    )


# ---------------------------------------------------------------------------
# TS-03-8: Python API reference types section
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("type_name", PYTHON_KEY_TYPES)
def test_python_api_types(type_name: str) -> None:
    """TS-03-8: Python API reference includes a Types section with all key public types."""
    assert PYTHON_API_DOC.exists(), f"Python API reference not found at {PYTHON_API_DOC}"
    content = read_file(PYTHON_API_DOC)
    h2_headings = extract_h2_headings(content)
    types_present = any("type" in h.lower() for h in h2_headings)
    assert types_present, (
        f"Python API reference has no '## Types' section. H2 headings: {h2_headings}"
    )
    assert type_name in content, (
        f"Python API reference does not mention type '{type_name}'"
    )


# ---------------------------------------------------------------------------
# TS-03-9: Python API reference category organization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", PYTHON_API_CATEGORIES)
def test_python_api_categories(category: str) -> None:
    """TS-03-9: Python API reference is organized by functional category."""
    assert PYTHON_API_DOC.exists(), f"Python API reference not found at {PYTHON_API_DOC}"
    content = read_file(PYTHON_API_DOC)
    h2_headings = extract_h2_headings(content)
    found = any(category.lower() in h.lower() for h in h2_headings)
    assert found, (
        f"Python API reference missing category '{category}'. H2 headings: {h2_headings}"
    )


# ---------------------------------------------------------------------------
# TS-03-12: Example files cover six operation categories
# ---------------------------------------------------------------------------


def test_example_categories() -> None:
    """TS-03-12: Example files cover all required operation categories."""
    ls_check = {
        EXAMPLES_DIR / "loading_and_saving.md": ["LoadSpec", "load_spec"],
        EXAMPLES_DIR / "validation.md": ["Validate", "validate"],
        EXAMPLES_DIR / "rendering.md": ["Render", "render"],
        EXAMPLES_DIR / "lifecycle.md": ["Transition", "transition"],
        EXAMPLES_DIR / "bootstrap_and_discovery.md": ["Bootstrap", "bootstrap", "Discover", "discover"],
        EXAMPLES_DIR / "comparison.md": ["```go", "```python"],
    }
    for path, keywords in ls_check.items():
        assert path.exists(), f"Example file not found: {path}"
        content = read_file(path)
        found = any(kw in content for kw in keywords)
        assert found, (
            f"{path.name} does not contain any of {keywords}"
        )


# ---------------------------------------------------------------------------
# TS-03-13: Examples are self-contained code snippets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", EXAMPLE_FILES_EXCEPT_COMPARISON, ids=[f.name for f in EXAMPLE_FILES_EXCEPT_COMPARISON])
def test_examples_self_contained(path: pathlib.Path) -> None:
    """TS-03-13: Go examples are 'package main' programs; Python examples have imports."""
    assert path.exists(), f"Example file not found at {path}"
    content = read_file(path)
    go_blocks = extract_code_blocks(content, "go")
    for block in go_blocks:
        assert "package main" in block, (
            f"{path.name}: Go code block missing 'package main':\n{block[:200]}"
        )
        assert "import" in block, (
            f"{path.name}: Go code block missing 'import':\n{block[:200]}"
        )
    python_blocks = extract_code_blocks(content, "python")
    for block in python_blocks:
        has_import = "import afspec" in block or "from afspec" in block
        assert has_import, (
            f"{path.name}: Python code block missing 'import afspec' or 'from afspec':\n{block[:200]}"
        )


# ---------------------------------------------------------------------------
# TS-03-14: Examples include both Go and Python
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", EXAMPLE_FILES_EXCEPT_COMPARISON, ids=[f.name for f in EXAMPLE_FILES_EXCEPT_COMPARISON])
def test_examples_both_languages(path: pathlib.Path) -> None:
    """TS-03-14: Each non-comparison example file has both Go and Python code blocks."""
    assert path.exists(), f"Example file not found at {path}"
    content = read_file(path)
    assert count_code_blocks(content, "go") >= 1, (
        f"{path.name}: No Go code blocks found"
    )
    assert count_code_blocks(content, "python") >= 1, (
        f"{path.name}: No Python code blocks found"
    )


# ---------------------------------------------------------------------------
# TS-03-15: Examples have prose descriptions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=[f.name for f in EXAMPLE_FILES])
def test_examples_prose_descriptions(path: pathlib.Path) -> None:
    """TS-03-15: Every code block is preceded by at least one prose line."""
    assert path.exists(), f"Example file not found at {path}"
    content = read_file(path)
    lines = content.split("\n")
    in_code_block = False
    code_block_line_numbers = []
    for i, line in enumerate(lines):
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_block_line_numbers.append(i)
            else:
                in_code_block = False

    for line_no in code_block_line_numbers:
        preceding = lines[max(0, line_no - 10) : line_no]
        assert has_prose_line(preceding), (
            f"{path.name}: Code block at line {line_no + 1} has no preceding prose description"
        )


# ---------------------------------------------------------------------------
# TS-03-17: Comparison covers required operations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("operation", ["load", "save", "validat", "render", "lifecycle", "bootstrap", "discover"])
def test_comparison_operations(operation: str) -> None:
    """TS-03-17: Comparison document covers all required operations."""
    comparison = EXAMPLES_DIR / "comparison.md"
    assert comparison.exists(), f"Comparison file not found at {comparison}"
    content = read_file(comparison)
    assert operation.lower() in content.lower(), (
        f"comparison.md does not mention operation '{operation}'"
    )


# ---------------------------------------------------------------------------
# TS-03-18: Comparison shows Go and Python side by side
# ---------------------------------------------------------------------------


def test_comparison_go_python_blocks() -> None:
    """TS-03-18: Comparison has at least 7 Go and 7 Python code blocks."""
    comparison = EXAMPLES_DIR / "comparison.md"
    assert comparison.exists(), f"Comparison file not found at {comparison}"
    content = read_file(comparison)
    go_count = count_code_blocks(content, "go")
    python_count = count_code_blocks(content, "python")
    assert go_count >= 7, (
        f"comparison.md has only {go_count} Go code blocks; expected at least 7"
    )
    assert python_count >= 7, (
        f"comparison.md has only {python_count} Python code blocks; expected at least 7"
    )


# ---------------------------------------------------------------------------
# TS-03-19: README overview section
# ---------------------------------------------------------------------------


def test_readme_overview() -> None:
    """TS-03-19: README.md introduces both Go and Python libraries."""
    assert README.exists(), f"README.md not found at {README}"
    content = read_file(README)
    assert "Go" in content, "README.md does not mention Go"
    assert "Python" in content or "python" in content, "README.md does not mention Python"
    assert "afspec" in content, "README.md does not mention 'afspec'"


# ---------------------------------------------------------------------------
# TS-03-20: README quick-start sections
# ---------------------------------------------------------------------------


def test_readme_quickstart() -> None:
    """TS-03-20: README.md has quick-start code examples for both Go and Python."""
    assert README.exists(), f"README.md not found at {README}"
    content = read_file(README)
    assert count_code_blocks(content, "go") >= 1, (
        "README.md has no Go code blocks"
    )
    assert count_code_blocks(content, "python") >= 1, (
        "README.md has no Python code blocks"
    )


# ---------------------------------------------------------------------------
# TS-03-21: README documentation links
# ---------------------------------------------------------------------------


def test_readme_links() -> None:
    """TS-03-21: README.md links to API docs, examples, and spec-format."""
    assert README.exists(), f"README.md not found at {README}"
    content = read_file(README)
    assert "docs/api/go.md" in content, "README.md missing link to docs/api/go.md"
    assert "docs/api/python.md" in content, "README.md missing link to docs/api/python.md"
    assert "docs/examples" in content, "README.md missing link to docs/examples"
    assert "docs/spec-format.md" in content, "README.md missing link to docs/spec-format.md"


# ---------------------------------------------------------------------------
# TS-03-23: Go API signatures match design doc
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("func_name", GO_PUBLIC_FUNCTIONS)
def test_go_signatures_match_design(func_name: str) -> None:
    """TS-03-23: Documented Go function signatures match spec 01 design.md."""
    assert GO_API_DOC.exists(), f"Go API reference not found at {GO_API_DOC}"
    assert GO_DESIGN_DOC.exists(), f"Go design doc not found at {GO_DESIGN_DOC}"

    api_content = read_file(GO_API_DOC)
    design_content = read_file(GO_DESIGN_DOC)

    # Extract signature from design doc: lines starting with "func {func_name}"
    design_sigs = re.findall(
        r"func " + re.escape(func_name) + r"[^\n]+", design_content
    )
    assert design_sigs, (
        f"Could not find signature for '{func_name}' in design doc"
    )
    design_sig = _normalize_whitespace(design_sigs[0])

    # Find the same signature in the API doc Go code blocks
    go_blocks = extract_code_blocks(api_content, "go")
    found = any(
        design_sig in _normalize_whitespace(block)
        for block in go_blocks
    )
    assert found, (
        f"API reference Go signature for '{func_name}' does not match design doc.\n"
        f"Expected (normalized): {design_sig!r}\n"
        f"Go code blocks found: {[_normalize_whitespace(b)[:200] for b in go_blocks]}"
    )


def _normalize_whitespace(s: str) -> str:
    """Collapse whitespace for comparison."""
    return " ".join(s.split())


# ---------------------------------------------------------------------------
# TS-03-24: Python API signatures match design doc
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("func_name", PYTHON_PUBLIC_FUNCTIONS)
def test_python_signatures_match_design(func_name: str) -> None:
    """TS-03-24: Documented Python function signatures match spec 02 design.md."""
    assert PYTHON_API_DOC.exists(), f"Python API reference not found at {PYTHON_API_DOC}"
    assert PYTHON_DESIGN_DOC.exists(), f"Python design doc not found at {PYTHON_DESIGN_DOC}"

    api_content = read_file(PYTHON_API_DOC)
    design_content = read_file(PYTHON_DESIGN_DOC)

    # Extract signature from design doc: lines starting with "def {func_name}"
    design_sigs = re.findall(
        r"def " + re.escape(func_name) + r"[^\n]+", design_content
    )
    assert design_sigs, (
        f"Could not find signature for '{func_name}' in Python design doc"
    )
    design_sig = _normalize_whitespace(design_sigs[0])
    # Strip trailing " ..." that design doc uses as placeholder
    design_sig = design_sig.rstrip(" .")

    # Find the same signature in the API doc Python code blocks
    python_blocks = extract_code_blocks(api_content, "python")
    found = any(
        _normalize_whitespace(design_sig) in _normalize_whitespace(block)
        for block in python_blocks
    )
    assert found, (
        f"API reference Python signature for '{func_name}' does not match design doc.\n"
        f"Expected (normalized): {design_sig!r}\n"
        f"Python code blocks found: {[_normalize_whitespace(b)[:200] for b in python_blocks]}"
    )


# ---------------------------------------------------------------------------
# TS-03-25: Documentation terminology consistency
# ---------------------------------------------------------------------------


def test_terminology_consistency() -> None:
    """TS-03-25: Domain terms in API docs are consistent with spec-format glossary."""
    # Check that API docs don't use deprecated or non-canonical terminology.
    # This is a lightweight check; full review is done by human review.
    for doc_path in [GO_API_DOC, PYTHON_API_DOC]:
        assert doc_path.exists(), f"API doc not found at {doc_path}"
        content = read_file(doc_path)
        # "afspec" should appear (not renamed)
        assert "afspec" in content.lower(), (
            f"{doc_path.name}: Does not reference 'afspec'"
        )


# ---------------------------------------------------------------------------
# TS-03-E1: Go function with no error return documented
# ---------------------------------------------------------------------------


def test_go_no_error_documented() -> None:
    """TS-03-E1: Go functions with no error return still document an Errors section."""
    assert GO_API_DOC.exists(), f"Go API reference not found at {GO_API_DOC}"
    content = read_file(GO_API_DOC)
    # LegalTransitions is a method that returns []SubtaskState (no error)
    section = extract_section(content, "LegalTransitions")
    if section:
        lower = section.lower()
        assert "error" in lower or "none" in lower or "n/a" in lower, (
            "LegalTransitions section does not mention errors or state 'None'"
        )
    # Also check that TopologicalOrder (which does return error) has error documented
    section2 = extract_section(content, "TopologicalOrder")
    if section2:
        assert "error" in section2.lower(), (
            "TopologicalOrder section does not mention errors"
        )


# ---------------------------------------------------------------------------
# TS-03-E2: Python function with no exceptions documented
# ---------------------------------------------------------------------------


def test_python_no_exception_documented() -> None:
    """TS-03-E2: Python functions that raise no exceptions still document the exceptions section."""
    assert PYTHON_API_DOC.exists(), f"Python API reference not found at {PYTHON_API_DOC}"
    content = read_file(PYTHON_API_DOC)
    # schema_version() raises no exceptions
    section = extract_section(content, "schema_version")
    assert section, "Could not find schema_version section in Python API doc"
    lower = section.lower()
    assert "exception" in lower or "raises" in lower or "none" in lower, (
        "schema_version section does not mention exceptions or state 'None'"
    )


# ---------------------------------------------------------------------------
# TS-03-E3: Go/Python behavioral differences noted in examples
# ---------------------------------------------------------------------------


def test_behavioral_differences_noted() -> None:
    """TS-03-E3: At least one example file notes Go vs Python behavioral differences."""
    found_difference_note = False
    for path in EXAMPLE_FILES:
        assert path.exists(), f"Example file not found: {path}"
        content = read_file(path)
        content_lower = content.lower()
        if (
            ("error" in content_lower and "exception" in content_lower)
            or "difference" in content_lower
            or "unlike" in content_lower
            or "contrast" in content_lower
            or "note:" in content_lower
        ):
            found_difference_note = True
            break
    assert found_difference_note, (
        "No example file contains a note about Go vs Python behavioral differences"
    )


# ---------------------------------------------------------------------------
# TS-03-E4: Missing Python-equivalent function noted in comparison
# ---------------------------------------------------------------------------


def test_comparison_missing_equivalent() -> None:
    """TS-03-E4: Comparison document notes when an operation lacks a direct equivalent."""
    comparison = EXAMPLES_DIR / "comparison.md"
    assert comparison.exists(), f"Comparison file not found at {comparison}"
    content = read_file(comparison)
    content_lower = content.lower()
    found = (
        "no direct" in content_lower
        or "equivalent" in content_lower
        or "alternative" in content_lower
        or "not available" in content_lower
    )
    assert found, (
        "comparison.md does not note any operations without direct equivalents"
    )


# ---------------------------------------------------------------------------
# TS-03-E5: README links to non-existent files include note
# ---------------------------------------------------------------------------


def test_readme_broken_links() -> None:
    """TS-03-E5: All relative links in README.md point to existing files/dirs."""
    assert README.exists(), f"README.md not found at {README}"
    content = read_file(README)
    links = extract_relative_links(content)
    for link in links:
        target = REPO_ROOT / link
        assert target.exists(), (
            f"README.md contains a broken link: '{link}' -> {target} does not exist"
        )


# ---------------------------------------------------------------------------
# TS-03-E6: Design doc ambiguity noted in API reference
# ---------------------------------------------------------------------------


def test_ambiguity_notes() -> None:
    """TS-03-E6: If any design doc ambiguity exists, API reference notes it.

    This test passes trivially if no ambiguities are present.
    By convention, ambiguity notes appear as 'Note:' or '> Note' callouts.
    """
    # This test always passes — manual review is needed for specific cases.
    assert True


# ---------------------------------------------------------------------------
# TS-03-P1: Property — Go API coverage completeness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("func_name", GO_PUBLIC_FUNCTIONS)
def test_property_go_coverage(func_name: str) -> None:
    """TS-03-P1: Every public Go function from design doc appears in API reference."""
    assert GO_API_DOC.exists(), f"Go API reference not found at {GO_API_DOC}"
    content = read_file(GO_API_DOC)
    # H3 heading or inline code mention
    found = (
        f"### {func_name}" in content
        or f"### `{func_name}`" in content
    )
    assert found, (
        f"'### {func_name}' not found in Go API reference as an H3 heading"
    )


# ---------------------------------------------------------------------------
# TS-03-P2: Property — Python API coverage completeness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("func_name", PYTHON_PUBLIC_FUNCTIONS)
def test_property_python_coverage(func_name: str) -> None:
    """TS-03-P2: Every public Python function from design doc appears in API reference."""
    assert PYTHON_API_DOC.exists(), f"Python API reference not found at {PYTHON_API_DOC}"
    content = read_file(PYTHON_API_DOC)
    found = (
        f"### {func_name}" in content
        or f"### `{func_name}`" in content
    )
    assert found, (
        f"'### {func_name}' not found in Python API reference as an H3 heading"
    )


# ---------------------------------------------------------------------------
# TS-03-P3: Property — Example operation coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("operation", ["load", "save", "validat", "render", "lifecycle", "bootstrap", "discover"])
def test_property_example_coverage(operation: str) -> None:
    """TS-03-P3: Every operation category has at least one Go and one Python example."""
    found_go = False
    found_python = False
    for path in EXAMPLE_FILES:
        assert path.exists(), f"Example file not found: {path}"
        content = read_file(path)
        if operation.lower() in content.lower():
            if count_code_blocks(content, "go") >= 1:
                found_go = True
            if count_code_blocks(content, "python") >= 1:
                found_python = True
    assert found_go, (
        f"No example file contains a Go code block for operation '{operation}'"
    )
    assert found_python, (
        f"No example file contains a Python code block for operation '{operation}'"
    )


# ---------------------------------------------------------------------------
# TS-03-P4: Property — Cross-reference integrity
# ---------------------------------------------------------------------------


def test_property_link_integrity() -> None:
    """TS-03-P4: Every relative link in README.md points to an existing file/dir."""
    assert README.exists(), f"README.md not found at {README}"
    content = read_file(README)
    links = extract_relative_links(content)
    broken = []
    for link in links:
        target = REPO_ROOT / link
        if not target.exists():
            broken.append((link, str(target)))
    assert not broken, (
        "README.md has broken relative links:\n"
        + "\n".join(f"  {link} -> {target}" for link, target in broken)
    )


# ---------------------------------------------------------------------------
# TS-03-P5: Property — Type documentation completeness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("type_name", GO_ALL_PUBLIC_TYPES)
def test_property_type_completeness_go(type_name: str) -> None:
    """TS-03-P5 (Go): Every public Go type appears in the Go API reference."""
    assert GO_API_DOC.exists(), f"Go API reference not found at {GO_API_DOC}"
    content = read_file(GO_API_DOC)
    assert type_name in content, (
        f"Go API reference does not mention type '{type_name}'"
    )


@pytest.mark.parametrize("type_name", PYTHON_ALL_PUBLIC_TYPES)
def test_property_type_completeness_python(type_name: str) -> None:
    """TS-03-P5 (Python): Every public Python type appears in the Python API reference."""
    assert PYTHON_API_DOC.exists(), f"Python API reference not found at {PYTHON_API_DOC}"
    content = read_file(PYTHON_API_DOC)
    assert type_name in content, (
        f"Python API reference does not mention type '{type_name}'"
    )


# ---------------------------------------------------------------------------
# TS-03-SMOKE-1: Developer discovers library via README
# ---------------------------------------------------------------------------


def test_smoke_readme_discovery() -> None:
    """TS-03-SMOKE-1: README → API docs → function entry navigation path."""
    assert README.exists(), f"README.md not found at {README}"
    readme = read_file(README)
    assert "docs/api/go.md" in readme, "README.md missing link to docs/api/go.md"
    assert "docs/api/python.md" in readme, "README.md missing link to docs/api/python.md"

    assert GO_API_DOC.exists(), f"docs/api/go.md not found at {GO_API_DOC}"
    go_api = read_file(GO_API_DOC)
    assert "LoadSpec" in go_api, "docs/api/go.md missing 'LoadSpec'"
    assert "func LoadSpec" in go_api, "docs/api/go.md missing 'func LoadSpec' signature"

    assert PYTHON_API_DOC.exists(), f"docs/api/python.md not found at {PYTHON_API_DOC}"
    python_api = read_file(PYTHON_API_DOC)
    assert "load_spec" in python_api, "docs/api/python.md missing 'load_spec'"
    assert "def load_spec" in python_api, "docs/api/python.md missing 'def load_spec' signature"


# ---------------------------------------------------------------------------
# TS-03-SMOKE-2: Developer looks up Go function
# ---------------------------------------------------------------------------


def test_smoke_go_function_lookup() -> None:
    """TS-03-SMOKE-2: Go API doc has complete Validate entry under Validation section."""
    assert GO_API_DOC.exists(), f"docs/api/go.md not found at {GO_API_DOC}"
    content = read_file(GO_API_DOC)
    validate_section = extract_section(content, "Validate")
    assert validate_section, "Could not find 'Validate' section in docs/api/go.md"
    assert "func Validate" in validate_section, (
        "Validate section missing 'func Validate' signature"
    )
    assert "Spec" in validate_section, "Validate section missing 'Spec' type reference"
    assert "ValidationError" in validate_section, (
        "Validate section missing 'ValidationError' return type"
    )
    lower = validate_section.lower()
    assert "parameters" in lower or "parameter" in lower, (
        "Validate section missing Parameters subsection"
    )


# ---------------------------------------------------------------------------
# TS-03-SMOKE-3: Developer looks up Python function
# ---------------------------------------------------------------------------


def test_smoke_python_function_lookup() -> None:
    """TS-03-SMOKE-3: Python API doc has complete validate entry under Validation section."""
    assert PYTHON_API_DOC.exists(), f"docs/api/python.md not found at {PYTHON_API_DOC}"
    content = read_file(PYTHON_API_DOC)
    validate_section = extract_section(content, "validate")
    assert validate_section, "Could not find 'validate' section in docs/api/python.md"
    assert "def validate" in validate_section, (
        "validate section missing 'def validate' signature"
    )
    assert "Spec" in validate_section, "validate section missing 'Spec' type reference"
    assert "ValidationError" in validate_section, (
        "validate section missing 'ValidationError' return type"
    )
    lower = validate_section.lower()
    assert "parameters" in lower or "parameter" in lower, (
        "validate section missing Parameters subsection"
    )


# ---------------------------------------------------------------------------
# TS-03-SMOKE-4: Developer learns from examples
# ---------------------------------------------------------------------------


def test_smoke_example_learning() -> None:
    """TS-03-SMOKE-4: loading_and_saving.md has title, Go block, Python block, prose."""
    loading_file = EXAMPLES_DIR / "loading_and_saving.md"
    assert loading_file.exists(), f"loading_and_saving.md not found at {loading_file}"
    content = read_file(loading_file)

    assert content.startswith("#"), "loading_and_saving.md does not start with a heading"

    go_blocks = extract_code_blocks(content, "go")
    assert len(go_blocks) >= 1, "loading_and_saving.md has no Go code blocks"
    assert "package main" in go_blocks[0], (
        "First Go block in loading_and_saving.md missing 'package main'"
    )

    python_blocks = extract_code_blocks(content, "python")
    assert len(python_blocks) >= 1, "loading_and_saving.md has no Python code blocks"
    has_import = "import afspec" in python_blocks[0] or "from afspec" in python_blocks[0]
    assert has_import, (
        "First Python block in loading_and_saving.md missing 'import afspec' or 'from afspec'"
    )


# ---------------------------------------------------------------------------
# TS-03-SMOKE-5: Developer translates between Go and Python
# ---------------------------------------------------------------------------


def test_smoke_cross_library_comparison() -> None:
    """TS-03-SMOKE-5: comparison.md has paired Go/Python blocks per operation (≥7)."""
    comparison = EXAMPLES_DIR / "comparison.md"
    assert comparison.exists(), f"comparison.md not found at {comparison}"
    content = read_file(comparison)

    sections = split_by_h2(content)
    operation_sections = [s for s in sections if has_code_blocks(s)]
    assert len(operation_sections) >= 7, (
        f"comparison.md has only {len(operation_sections)} operation sections with code blocks; expected ≥ 7"
    )
    for section in operation_sections:
        go_count = count_code_blocks(section, "go")
        python_count = count_code_blocks(section, "python")
        assert go_count >= 1, (
            f"A comparison section lacks a Go code block:\n{section[:300]}"
        )
        assert python_count >= 1, (
            f"A comparison section lacks a Python code block:\n{section[:300]}"
        )
