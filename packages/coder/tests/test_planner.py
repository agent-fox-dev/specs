"""Tests for the execution plan builder.

Covers: TS-13-1, TS-13-2, TS-13-4 through TS-13-10,
        TS-13-E1, TS-13-E2, TS-13-E6 through TS-13-E10,
        TS-13-P1 through TS-13-P4,
        TS-13-SMOKE-1.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pytest
from coder.errors import DependencyCycleError
from coder.planner import build_execution_plan
from conftest import create_spec_pack
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def two_spec_campaign(tmp_path: Path) -> Path:
    """Campaign with two active specs: 01_base_app and 02_feature.

    No dependencies between them.
    """
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign, "01_base_app", spec_id="1", spec_name="base_app"
    )
    create_spec_pack(
        campaign, "02_feature", spec_id="2", spec_name="feature"
    )
    return campaign


@pytest.fixture()
def three_spec_campaign_unordered(tmp_path: Path) -> Path:
    """Campaign with three specs in unordered directories.

    Directories: 03_third, 01_first, 02_second.
    All active, no dependencies.
    """
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    # Create in non-sorted order to test discovery sorting
    create_spec_pack(
        campaign, "03_third", spec_id="3", spec_name="third"
    )
    create_spec_pack(
        campaign, "01_first", spec_id="1", spec_name="first"
    )
    create_spec_pack(
        campaign, "02_second", spec_id="2", spec_name="second"
    )
    return campaign


@pytest.fixture()
def mixed_status_campaign(tmp_path: Path) -> Path:
    """Campaign with one active and one draft spec."""
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign, "01_active", spec_id="1", spec_name="active", status="active"
    )
    create_spec_pack(
        campaign, "02_draft", spec_id="2", spec_name="draft", status="draft"
    )
    return campaign


@pytest.fixture()
def dependent_specs_campaign(tmp_path: Path) -> Path:
    """Campaign where 02_feature depends on 01_base.

    Both specs are active. The dependency is declared in 02's tasks.json.
    """
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign, "01_base", spec_id="1", spec_name="base"
    )
    create_spec_pack(
        campaign,
        "02_feature",
        spec_id="2",
        spec_name="feature",
        dependencies=[
            {
                "depends_on_spec": "1",
                "from_group": 1,
                "to_group": 1,
                "relationship": "feature depends on base",
                "sentinel": False,
            }
        ],
    )
    return campaign


@pytest.fixture()
def cyclic_campaign(tmp_path: Path) -> Path:
    """Campaign with a circular dependency: A depends on B, B depends on A."""
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign,
        "01_alpha",
        spec_id="1",
        spec_name="alpha",
        dependencies=[
            {
                "depends_on_spec": "2",
                "from_group": 1,
                "to_group": 1,
                "relationship": "alpha depends on beta",
                "sentinel": False,
            }
        ],
    )
    create_spec_pack(
        campaign,
        "02_beta",
        spec_id="2",
        spec_name="beta",
        dependencies=[
            {
                "depends_on_spec": "1",
                "from_group": 1,
                "to_group": 1,
                "relationship": "beta depends on alpha",
                "sentinel": False,
            }
        ],
    )
    return campaign


@pytest.fixture()
def three_active_campaign(tmp_path: Path) -> Path:
    """Campaign with three active specs and no dependencies."""
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign, "01_base", spec_id="1", spec_name="base"
    )
    create_spec_pack(
        campaign, "02_middle", spec_id="2", spec_name="middle"
    )
    create_spec_pack(
        campaign, "03_top", spec_id="3", spec_name="top"
    )
    return campaign


@pytest.fixture()
def external_dep_campaign(tmp_path: Path) -> Path:
    """Campaign with spec 02 depending on spec 01, but spec 01 not present.

    Only spec 02 exists in the campaign directory.
    """
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign,
        "02_feature",
        spec_id="2",
        spec_name="feature",
        dependencies=[
            {
                "depends_on_spec": "1",
                "from_group": 1,
                "to_group": 1,
                "relationship": "depends on external spec",
                "sentinel": False,
            }
        ],
    )
    return campaign


@pytest.fixture()
def no_status_campaign(tmp_path: Path) -> Path:
    """Campaign with one spec whose status field is absent."""
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign,
        "01_nostatus",
        spec_id="1",
        spec_name="nostatus",
        include_status=False,
    )
    return campaign


@pytest.fixture()
def all_draft_campaign(tmp_path: Path) -> Path:
    """Campaign where all specs are draft (no active specs)."""
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign, "01_draft_one", spec_id="1", spec_name="draft_one",
        status="draft",
    )
    create_spec_pack(
        campaign, "02_draft_two", spec_id="2", spec_name="draft_two",
        status="draft",
    )
    return campaign


@pytest.fixture()
def smoke_campaign(tmp_path: Path) -> Path:
    """Campaign with realistic spec packs for smoke testing.

    Creates a multi-spec campaign with proper YAML frontmatter,
    valid JSON artifacts, and a dependency relationship. Uses real
    filesystem I/O (no mocking).

    Note: Uses a generated fixture instead of examples/golang_service/
    because the example prd.md lacks YAML frontmatter required by
    afspec.discovery.discover_specs().
    """
    campaign = tmp_path / "smoke_campaign"
    campaign.mkdir()
    create_spec_pack(
        campaign,
        "01_foundation",
        spec_id="1",
        spec_name="foundation",
        status="active",
    )
    create_spec_pack(
        campaign,
        "02_api_layer",
        spec_id="2",
        spec_name="api_layer",
        status="active",
        dependencies=[
            {
                "depends_on_spec": "1",
                "from_group": 1,
                "to_group": 2,
                "relationship": "api_layer builds on foundation",
                "sentinel": False,
            }
        ],
    )
    return campaign


# ---------------------------------------------------------------------------
# Unit tests: TS-13-1 through TS-13-10
# ---------------------------------------------------------------------------


class TestDiscovery:
    """Tests for spec discovery via build_execution_plan."""

    def test_discover_specs(self, two_spec_campaign: Path) -> None:
        """TS-13-1: Discover specs in campaign directory.

        Requirement: 13-REQ-1.1, 13-REQ-1.2
        Verify spec discovery finds all spec pack folders and returns
        SpecMeta objects with correct IDs.
        """
        plan = build_execution_plan(two_spec_campaign)

        assert plan.count == 2
        ids = [s.meta.spec_id for s in plan.specs]
        assert "1" in ids
        assert "2" in ids

    def test_sorted_by_prefix(
        self, three_spec_campaign_unordered: Path
    ) -> None:
        """TS-13-2: Specs sorted by numeric prefix.

        Requirement: 13-REQ-1.3
        Verify discovered specs are in ascending numeric order
        regardless of filesystem directory creation order.
        """
        plan = build_execution_plan(three_spec_campaign_unordered)

        ids = [s.meta.spec_id for s in plan.specs]
        assert ids == ["1", "2", "3"]


class TestStatusFiltering:
    """Tests for spec status validation and filtering."""

    def test_active_only(self, mixed_status_campaign: Path) -> None:
        """TS-13-4: Only active specs included in plan.

        Requirement: 13-REQ-3.1, 13-REQ-3.3
        Verify non-active specs are filtered out of the execution plan.
        """
        plan = build_execution_plan(mixed_status_campaign)

        assert plan.count == 1
        assert plan.specs[0].meta.spec_name == "active"

    def test_skip_warning(
        self,
        mixed_status_campaign: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """TS-13-5: Non-active spec logs warning.

        Requirement: 13-REQ-3.2
        Verify skipped specs produce a log warning with the spec name
        and its status.
        """
        with caplog.at_level(logging.WARNING):
            build_execution_plan(mixed_status_campaign)

        log_text = " ".join(r.message for r in caplog.records)
        assert "draft" in log_text.lower()
        assert "skip" in log_text.lower() or "skipped" in log_text.lower()


class TestDependencyOrdering:
    """Tests for dependency analysis and topological sorting."""

    def test_dependency_order(
        self, dependent_specs_campaign: Path
    ) -> None:
        """TS-13-6: Dependency ordering respected.

        Requirement: 13-REQ-4.1, 13-REQ-4.2
        Verify dependent specs come after their dependencies in the
        execution plan.
        """
        plan = build_execution_plan(dependent_specs_campaign)

        names = [s.meta.spec_name for s in plan.specs]
        assert names.index("base") < names.index("feature")

    def test_cycle_detection(self, cyclic_campaign: Path) -> None:
        """TS-13-7: Cycle detection raises error.

        Requirement: 13-REQ-4.3
        Verify circular dependencies are caught and raise
        DependencyCycleError.
        """
        with pytest.raises(DependencyCycleError):
            build_execution_plan(cyclic_campaign)


class TestPlanConstruction:
    """Tests for execution plan construction and features."""

    def test_plan_serializable(
        self, two_spec_campaign: Path
    ) -> None:
        """TS-13-8: Execution plan is serializable (via planner).

        Requirement: 13-REQ-5.1, 13-REQ-5.3
        Verify ExecutionPlan produced by build_execution_plan can be
        serialized to JSON.
        """
        import json

        plan = build_execution_plan(two_spec_campaign)

        json_str = plan.model_dump_json()
        data = json.loads(json_str)

        assert "specs" in data
        assert "count" in data
        assert data["count"] == 2

    def test_spec_filter(self, three_active_campaign: Path) -> None:
        """TS-13-9: Spec filter restricts plan.

        Requirement: 13-REQ-6.2
        Verify spec_filter limits which specs appear in the plan.
        Uses spec_name to filter (name component without numeric prefix).
        """
        plan = build_execution_plan(
            three_active_campaign, spec_filter=["base"]
        )

        assert plan.count == 1
        assert plan.specs[0].meta.spec_name == "base"

    def test_logs_steps(
        self,
        two_spec_campaign: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """TS-13-10: Build plan entry point logs steps.

        Requirement: 13-REQ-6.1
        Verify the build function logs discovery, parsing, and sorting
        steps for observability.
        """
        with caplog.at_level(logging.DEBUG):
            build_execution_plan(two_spec_campaign)

        log_text = " ".join(r.message for r in caplog.records).lower()
        assert "discover" in log_text
        assert "pars" in log_text  # "parse" or "parsed" or "parsing"


# ---------------------------------------------------------------------------
# Edge-case tests: TS-13-E1, TS-13-E2, TS-13-E6 through TS-13-E10
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case tests for the planner."""

    def test_empty_campaign(self, tmp_path: Path) -> None:
        """TS-13-E1: Empty campaign directory.

        Requirement: 13-REQ-1.E1
        Verify empty campaign produces empty plan without error.
        """
        empty_dir = tmp_path / "empty_campaign"
        empty_dir.mkdir()

        plan = build_execution_plan(empty_dir)

        assert plan.count == 0
        assert plan.specs == []

    def test_non_spec_ignored(self, tmp_path: Path) -> None:
        """TS-13-E2: Non-spec folders ignored.

        Requirement: 13-REQ-1.E2
        Verify folders not matching NN_name pattern are skipped.
        """
        campaign = tmp_path / "campaign"
        campaign.mkdir()

        # Create a valid spec pack
        create_spec_pack(
            campaign, "01_valid", spec_id="1", spec_name="valid"
        )
        # Create non-matching folders
        (campaign / "notes").mkdir()
        (campaign / ".git").mkdir()
        (campaign / "README.md").touch()

        plan = build_execution_plan(campaign)

        assert plan.count == 1
        assert plan.specs[0].meta.spec_name == "valid"

    def test_external_dep(
        self,
        external_dep_campaign: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """TS-13-E6: External dependency treated as satisfied.

        Requirement: 13-REQ-4.E1
        Verify dependencies on specs outside the campaign don't block
        execution, and a warning is logged.
        """
        with caplog.at_level(logging.WARNING):
            plan = build_execution_plan(external_dep_campaign)

        assert plan.count == 1
        log_text = " ".join(r.message for r in caplog.records).lower()
        assert "dependency" in log_text or "depend" in log_text

    def test_missing_dir(self) -> None:
        """TS-13-E7: Campaign directory does not exist.

        Requirement: 13-REQ-6.E1
        Verify nonexistent directory raises FileNotFoundError.
        """
        with pytest.raises(FileNotFoundError):
            build_execution_plan(Path("/nonexistent/campaign/path"))

    def test_missing_status_treated_as_draft(
        self,
        no_status_campaign: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """TS-13-E8: Missing status field treated as draft.

        Requirement: 13-REQ-3.E1
        Verify a spec with missing status is treated as draft and
        skipped with a warning.
        """
        with caplog.at_level(logging.WARNING):
            plan = build_execution_plan(no_status_campaign)

        assert plan.count == 0
        log_text = " ".join(r.message for r in caplog.records).lower()
        assert "draft" in log_text
        assert "nostatus" in log_text

    def test_no_deps_prefix_order(
        self, three_active_campaign: Path
    ) -> None:
        """TS-13-E9: No dependency specs ordered by prefix.

        Requirement: 13-REQ-4.E2
        Verify specs with no dependencies are ordered by numeric prefix.
        """
        plan = build_execution_plan(three_active_campaign)

        ids = [s.meta.spec_id for s in plan.specs]
        assert ids == ["1", "2", "3"]

    def test_empty_plan_zero_count(
        self, all_draft_campaign: Path
    ) -> None:
        """TS-13-E10: Empty plan has count zero.

        Requirement: 13-REQ-5.E1
        Verify empty execution plan (no active specs) has zero count
        and empty list.
        """
        plan = build_execution_plan(all_draft_campaign)

        assert plan.count == 0
        assert plan.specs == []


# ---------------------------------------------------------------------------
# Property tests: TS-13-P1 through TS-13-P4
# ---------------------------------------------------------------------------


def _build_campaign_from_spec_list(
    specs: list[tuple[str, str, str]],
    dependencies: list[tuple[str, str]] | None = None,
) -> Path:
    """Create a temporary campaign directory from a list of specs.

    Parameters
    ----------
    specs:
        List of (folder_name, spec_id, spec_name) tuples.
    dependencies:
        List of (from_spec_id, to_spec_id) tuples representing
        dependency edges (to_spec depends on from_spec).

    Returns the campaign directory path.
    """
    campaign = Path(tempfile.mkdtemp()) / "campaign"
    campaign.mkdir()

    dep_map: dict[str, list[dict[str, object]]] = {}
    for from_id, to_id in dependencies or []:
        dep_map.setdefault(to_id, []).append(
            {
                "depends_on_spec": from_id,
                "from_group": 1,
                "to_group": 1,
                "relationship": f"{to_id} depends on {from_id}",
                "sentinel": False,
            }
        )

    for folder_name, spec_id, spec_name in specs:
        create_spec_pack(
            campaign,
            folder_name,
            spec_id=spec_id,
            spec_name=spec_name,
            status="active",
            dependencies=dep_map.get(spec_id),
        )

    return campaign


class TestPropertyTopologicalOrder:
    """TS-13-P1: Topological order respects all dependencies.

    Property 1 from design.md.
    Validates: 13-REQ-4.2

    For any valid DAG of 2-6 specs with random edges, every dependency
    appears before its dependent in the plan.
    """

    @given(
        st.integers(min_value=2, max_value=6).flatmap(
            lambda n: st.tuples(
                st.just(n),
                # Generate edges as pairs (i, j) where i < j (ensures DAG)
                st.lists(
                    st.tuples(
                        st.integers(min_value=0, max_value=n - 2),
                        st.integers(min_value=1, max_value=n - 1),
                    ).filter(lambda pair: pair[0] < pair[1]),
                    max_size=n * 2,
                    unique=True,
                ),
            )
        )
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_topological_order(
        self, n_and_edges: tuple[int, list[tuple[int, int]]]
    ) -> None:
        """For any DAG, every dependency precedes its dependent."""
        n, edges = n_and_edges

        # Build spec descriptors
        specs = [
            (f"{i + 1:02d}_spec_{i + 1}", str(i + 1), f"spec_{i + 1}")
            for i in range(n)
        ]
        # Convert index-based edges to spec_id-based edges
        dep_edges = [(str(i + 1), str(j + 1)) for i, j in edges]

        campaign = _build_campaign_from_spec_list(specs, dep_edges)
        plan = build_execution_plan(campaign)

        plan_ids = [s.meta.spec_id for s in plan.specs]

        for from_id, to_id in dep_edges:
            if from_id in plan_ids and to_id in plan_ids:
                assert plan_ids.index(from_id) < plan_ids.index(to_id), (
                    f"Dependency {from_id} should precede {to_id} "
                    f"but got order: {plan_ids}"
                )


class TestPropertyActiveFiltering:
    """TS-13-P2: Active-only filtering is complete.

    Property 2 from design.md.
    Validates: 13-REQ-3.1, 13-REQ-3.3

    The plan never contains non-active specs.
    """

    @given(
        st.lists(
            st.sampled_from(["draft", "active", "sealed", "superseded", "archived"]),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_active_only_filtering(
        self, statuses: list[str]
    ) -> None:
        """Every spec in the plan has status 'active'."""
        campaign = Path(tempfile.mkdtemp()) / "campaign"
        campaign.mkdir()

        for i, status in enumerate(statuses, start=1):
            create_spec_pack(
                campaign,
                f"{i:02d}_spec_{i}",
                spec_id=str(i),
                spec_name=f"spec_{i}",
                status=status,
            )

        plan = build_execution_plan(campaign)

        for spec in plan.specs:
            assert spec.meta.status == "active" or spec.meta.status.value == "active", (
                f"Non-active spec {spec.meta.spec_name} with status "
                f"{spec.meta.status} found in plan"
            )


class TestPropertyStableSort:
    """TS-13-P3: Stable sort by numeric prefix.

    Property 3 from design.md.
    Validates: 13-REQ-4.4

    Unrelated specs (no dependencies) are ordered by ascending spec_id.
    """

    @given(
        st.lists(
            st.integers(min_value=1, max_value=50),
            min_size=2,
            max_size=6,
            unique=True,
        )
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_stable_sort(self, spec_nums: list[int]) -> None:
        """Specs with no dependencies are ordered by numeric prefix."""
        campaign = Path(tempfile.mkdtemp()) / "campaign"
        campaign.mkdir()

        for num in spec_nums:
            create_spec_pack(
                campaign,
                f"{num:02d}_spec_{num}",
                spec_id=str(num),
                spec_name=f"spec_{num}",
            )

        plan = build_execution_plan(campaign)

        result_ids = [s.meta.spec_id for s in plan.specs]
        # IDs are strings, so sort numerically
        expected_ids = sorted(result_ids, key=lambda x: int(x))
        assert result_ids == expected_ids, (
            f"Expected ascending order {expected_ids} but got {result_ids}"
        )


class TestPropertyCycleDetection:
    """TS-13-P4: Cycle detection is reliable.

    Property 4 from design.md.
    Validates: 13-REQ-4.3

    Any graph with a cycle raises DependencyCycleError.
    """

    @given(
        st.integers(min_value=2, max_value=5).flatmap(
            lambda n: st.tuples(
                st.just(n),
                # Pick a random position where we insert a back-edge
                st.integers(min_value=0, max_value=n - 2),
            )
        )
    )
    @settings(max_examples=20, deadline=10000)
    def test_property_cycle_detection(
        self, n_and_back: tuple[int, int]
    ) -> None:
        """Any graph with a cycle raises DependencyCycleError."""
        n, back_pos = n_and_back

        # Build a chain: 1 -> 2 -> 3 -> ... -> n
        # Then add back-edge from (back_pos+1) to some later node
        # creating a cycle
        specs = [
            (f"{i + 1:02d}_spec_{i + 1}", str(i + 1), f"spec_{i + 1}")
            for i in range(n)
        ]

        # Chain edges: each spec depends on the previous
        chain_edges = [(str(i), str(i + 1)) for i in range(1, n)]
        # Back-edge: last spec is depended on by first spec (cycle)
        back_edge = (str(n), str(back_pos + 1))
        all_edges = chain_edges + [back_edge]

        campaign = _build_campaign_from_spec_list(specs, all_edges)

        with pytest.raises(DependencyCycleError):
            build_execution_plan(campaign)


# ---------------------------------------------------------------------------
# Integration smoke test: TS-13-SMOKE-1
# ---------------------------------------------------------------------------


class TestSmoke:
    """Integration smoke tests using real filesystem I/O."""

    @pytest.mark.smoke
    def test_smoke_build_plan_from_example(
        self, smoke_campaign: Path
    ) -> None:
        """TS-13-SMOKE-1: Build plan from example specs.

        Execution Path: Path 1 from design.md
        Verify end-to-end plan building using real spec packs with
        valid JSON artifacts. No mocking of afspec discovery or I/O.

        Note: Uses a generated campaign fixture because the example
        at examples/golang_service/service_mvp/ lacks YAML frontmatter
        in prd.md, which is required by afspec.discovery.discover_specs().
        """
        plan = build_execution_plan(smoke_campaign)

        assert plan.count >= 1

        for spec in plan.specs:
            assert spec.requirements is not None
            assert spec.test_spec is not None
            assert spec.tasks is not None
            assert spec.meta.spec_name != ""

        # Verify topological order: foundation before api_layer
        names = [s.meta.spec_name for s in plan.specs]
        if "foundation" in names and "api_layer" in names:
            assert names.index("foundation") < names.index("api_layer")
