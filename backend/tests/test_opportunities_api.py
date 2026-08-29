"""V3.1.4 BATCH-4 contract tests for the real, versioned `/v1/opportunities` API:
schema-version metadata is present, no internal-only fields ever serialize, the
route delegates to the same pipeline run as the deprecated demo feed (no
duplicated business logic), and the category filter behaves like the old
static-data route it replaces.
"""

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from backend.app.main import app
from backend.app.opportunities import OPPORTUNITIES_SCHEMA_VERSION, run_opportunities
from logan_core.contracts import LOCAL_FOUNDER_USER_ID

client = TestClient(app)


def test_opportunities_response_has_schema_version():
    result = run_opportunities(LOCAL_FOUNDER_USER_ID)
    assert result.schema_version == OPPORTUNITIES_SCHEMA_VERSION
    assert result.schema_version == "1.0"


def test_opportunities_response_has_no_internal_score_fields():
    result = run_opportunities(LOCAL_FOUNDER_USER_ID)
    payload = result.model_dump()
    flat = str(payload)
    assert "priority_score" not in flat
    assert "internal_rank_score" not in flat


def test_opportunities_matches_demo_feed_pipeline_output():
    """Both routes must be thin wrappers over the same pipeline run -- not two
    independent computations that could silently drift apart.

    Resets pipeline state between the two calls deliberately: the pipeline's
    Orchestrator now persists *across* calls (see logan_feed.py), so a second
    call within the dedup window legitimately corroborates the first (more
    supporting evidence -> higher trust_score -> possibly different rank
    order) rather than recomputing identically. That's the intended fix, not
    a bug -- but it means this test needs both calls to start from the same
    fresh state to isolate what it actually checks (two routes, one
    computation) from that new, deliberate cross-request behavior.
    """
    reset_pipeline_state()
    opportunities_result = run_opportunities(LOCAL_FOUNDER_USER_ID)
    reset_pipeline_state()
    demo_result = run_demo_feed()
    assert [item.entity_id for item in opportunities_result.items] == [
        item.entity_id for item in demo_result.items
    ]
    assert [item.rank for item in opportunities_result.items] == [
        item.rank for item in demo_result.items
    ]


def test_opportunities_route_returns_schema_version_and_items():
    response = client.get("/v1/opportunities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "1.0"
    assert len(payload["items"]) == 11
    for item in payload["items"]:
        assert "internal_rank_score" not in item
        assert "priority_score" not in item


def test_opportunities_route_category_filter():
    response = client.get("/v1/opportunities", params={"category": "stocks"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) > 0
    for item in payload["items"]:
        assert item["category"] == "stocks"


def test_opportunities_route_unknown_category_returns_empty():
    response = client.get(
        "/v1/opportunities", params={"category": "not-a-real-category"}
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_opportunities_route_category_filter_preserves_provider_degraded(monkeypatch):
    """V2.3A.1 propagation bug, fixed alongside the earnings-cache-store
    reliability work: the category-filter branch in main.py's opportunities()
    reconstructs OpportunitiesResponse from the filtered item list -- before
    this fix, that reconstruction silently reset provider_degraded to its
    default False, so a genuine live-data outage would misreport as
    "healthy" on any category-filtered request even though the unfiltered
    response correctly flagged it."""
    from backend.app.opportunities import OpportunitiesResponse

    unfiltered = run_opportunities(LOCAL_FOUNDER_USER_ID)
    degraded_response = OpportunitiesResponse(
        items=unfiltered.items,
        generated_at=unfiltered.generated_at,
        provider_degraded=True,
    )
    monkeypatch.setattr(
        "backend.app.main.run_opportunities", lambda user_id: degraded_response
    )

    response = client.get("/v1/opportunities", params={"category": "stocks"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) > 0  # the filter itself still worked
    assert payload["provider_degraded"] is True


def test_demo_feed_route_still_works_but_is_deprecated():
    demo_route = next(
        r for r in app.routes if isinstance(r, APIRoute) and r.path == "/v1/demo/feed"
    )
    assert demo_route.deprecated is True
    response = client.get("/v1/demo/feed")
    assert response.status_code == 200
