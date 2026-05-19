"""Spec discovery and dependency graph construction.

Implements task group 11: scanning a spec root directory for spec folders,
loading PRD metadata, building a dependency graph from tasks.json, and
detecting dependency cycles.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import re
from typing import Any

import yaml

# Regex pattern for spec folder names: {NN}_{snake_case_name}
# Matches one or more digits, underscore, then snake_case identifier
_SPEC_DIR_PATTERN = re.compile(r"^(\d+)_([a-z][a-z0-9_]*)$")

# Files required in a complete spec folder
_REQUIRED_FILES = ["prd.md", "requirements.json", "test_spec.json", "tasks.json"]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SpecEntry:
    """Metadata for a single discovered spec folder."""

    spec_id: str
    spec_name: str
    status: str
    path: pathlib.Path
    complete: bool


@dataclasses.dataclass(frozen=True)
class DependencyEdge:
    """A directed dependency edge in the spec dependency graph.

    An edge ``(from_spec_id → to_spec_id)`` means ``to_spec_id`` depends on
    ``from_spec_id``.  Topological sort produces ``from_spec_id`` before
    ``to_spec_id``.
    """

    from_spec_id: str  # The dependency (must come first in topological order)
    to_spec_id: str  # The spec that depends on from_spec_id


@dataclasses.dataclass(frozen=True)
class DependencyGraph:
    """Directed acyclic dependency graph across specs."""

    edges: list[DependencyEdge]

    def has_edge(self, from_spec_id: str, to_spec_id: str) -> bool:
        """Return True if there is a direct edge from from_spec_id to to_spec_id."""
        return any(
            e.from_spec_id == from_spec_id and e.to_spec_id == to_spec_id
            for e in self.edges
        )

    def has_cycle(self) -> bool:
        """Return True if the graph contains any cycle."""
        try:
            self.topological_sort()
            return False
        except CyclicDependencyError:
            return True

    def topological_sort(self) -> list[str]:
        """Return spec IDs in topological order (dependencies first).

        Uses Kahn's algorithm.  Sorting is applied at each step to ensure
        deterministic output.

        Raises:
            CyclicDependencyError: If the graph contains a cycle, with
                ``spec_ids`` listing the spec IDs involved in the cycle.
        """
        # Collect all nodes
        nodes: set[str] = set()
        for edge in self.edges:
            nodes.add(edge.from_spec_id)
            nodes.add(edge.to_spec_id)

        if not nodes:
            return []

        # Build adjacency list and in-degree map
        adj: dict[str, list[str]] = {n: [] for n in nodes}
        in_degree: dict[str, int] = {n: 0 for n in nodes}

        for edge in self.edges:
            adj[edge.from_spec_id].append(edge.to_spec_id)
            in_degree[edge.to_spec_id] += 1

        # Kahn's algorithm: start with all zero-in-degree nodes (sorted for determinism)
        queue: list[str] = sorted(n for n in nodes if in_degree[n] == 0)
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in sorted(adj[node]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    queue.sort()

        if len(result) < len(nodes):
            # Remaining nodes are part of a cycle
            in_cycle = sorted(n for n in nodes if n not in set(result))
            raise CyclicDependencyError(
                f"Dependency graph has a cycle involving spec IDs: {in_cycle}",
                spec_ids=in_cycle,
            )

        return result


@dataclasses.dataclass(frozen=True)
class DiscoveryResult:
    """Result of a spec root discovery scan."""

    entries: list[SpecEntry]
    dependency_graph: DependencyGraph


class CyclicDependencyError(Exception):
    """Raised when the spec dependency graph contains a cycle."""

    def __init__(self, message: str, spec_ids: list[str]) -> None:
        super().__init__(message)
        self.spec_ids = spec_ids


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_prd_metadata(prd_path: pathlib.Path) -> tuple[str, str, str] | None:
    """Read PRD frontmatter to extract (spec_id, spec_name, status).

    Returns ``None`` if the file cannot be parsed.  Does not raise.
    """
    try:
        content = prd_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return None
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        fm_yaml = parts[1]
        fm: Any = yaml.safe_load(fm_yaml)
        if not isinstance(fm, dict):
            return None
        spec_id = str(fm.get("spec_id", ""))
        spec_name = str(fm.get("spec_name", ""))
        status = str(fm.get("status", "draft"))
        return spec_id, spec_name, status
    except Exception:
        return None


def _load_tasks_dependencies(tasks_path: pathlib.Path) -> list[str]:
    """Read tasks.json and return a list of spec IDs that this spec depends on.

    Handles two dependency object formats:
    - ``{"depends_on_spec": "01", ...}`` — format used in discovery tests
    - ``{"spec_id": "01", "kind": "..."}`` — format used by the Tasks model/saver

    Returns an empty list if the file cannot be parsed or has no dependencies.
    """
    try:
        content = tasks_path.read_text(encoding="utf-8")
        data = json.loads(content)
        dep_ids: list[str] = []
        for dep in data.get("dependencies", []):
            # Try depends_on_spec first (discovery test format), then spec_id (model format)
            dep_spec_id = dep.get("depends_on_spec") or dep.get("spec_id")
            if dep_spec_id:
                dep_ids.append(str(dep_spec_id))
        return dep_ids
    except Exception:
        return []


def _scan_folders(spec_root: pathlib.Path) -> list[pathlib.Path]:
    """Find top-level directories in spec_root matching ``{NN}_{snake_case}``.

    Skips the ``archive/`` subdirectory and any non-matching names.
    Results are sorted by path for deterministic ordering.
    """
    archive_path = spec_root / "archive"
    folders: list[pathlib.Path] = []
    for item in spec_root.iterdir():
        # Skip archive directory
        if item == archive_path:
            continue
        if not item.is_dir():
            continue
        if _SPEC_DIR_PATTERN.match(item.name):
            folders.append(item)
    return sorted(folders)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def discover(spec_root: pathlib.Path | None = None) -> DiscoveryResult:
    """Discover spec folders in ``spec_root`` and build a dependency graph.

    Args:
        spec_root: Directory to scan.  Defaults to the current working directory.

    Returns:
        :class:`DiscoveryResult` with all discovered :class:`SpecEntry` objects
        and a :class:`DependencyGraph`.

    Raises:
        FileNotFoundError: If ``spec_root`` does not exist.
        NotADirectoryError: If ``spec_root`` is not a directory.
        CyclicDependencyError: If the dependency graph contains a cycle,
            with ``spec_ids`` listing the spec IDs involved.
    """
    if spec_root is None:
        spec_root = pathlib.Path.cwd()

    if not spec_root.exists():
        raise FileNotFoundError(f"Spec root directory does not exist: {spec_root}")
    if not spec_root.is_dir():
        raise NotADirectoryError(f"Spec root is not a directory: {spec_root}")

    folders = _scan_folders(spec_root)
    entries: list[SpecEntry] = []

    for folder in folders:
        prd_path = folder / "prd.md"
        if not prd_path.exists():
            # No prd.md — skip entirely (can't extract metadata)
            continue

        metadata = _load_prd_metadata(prd_path)
        if metadata is None:
            # Unparseable prd.md — skip
            continue

        spec_id, spec_name, status = metadata

        # Complete iff all four required files exist
        complete = all((folder / f).exists() for f in _REQUIRED_FILES)

        entries.append(
            SpecEntry(
                spec_id=spec_id,
                spec_name=spec_name,
                status=status,
                path=folder,
                complete=complete,
            )
        )

    # Build dependency graph from tasks.json files
    edges: list[DependencyEdge] = []
    for entry in entries:
        tasks_path = entry.path / "tasks.json"
        if not tasks_path.exists():
            continue
        dep_ids = _load_tasks_dependencies(tasks_path)
        for dep_id in dep_ids:
            # Edge goes FROM the dependency TO this spec (dep comes first in sort)
            edges.append(DependencyEdge(from_spec_id=dep_id, to_spec_id=entry.spec_id))

    graph = DependencyGraph(edges=edges)

    # Eagerly detect cycles — raises CyclicDependencyError if a cycle exists
    graph.topological_sort()

    return DiscoveryResult(entries=entries, dependency_graph=graph)


__all__ = [
    "discover",
    "SpecEntry",
    "DependencyEdge",
    "DependencyGraph",
    "DiscoveryResult",
    "CyclicDependencyError",
]
