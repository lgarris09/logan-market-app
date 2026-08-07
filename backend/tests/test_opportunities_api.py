"""V3.1.4 BATCH-4 contract tests for the real, versioned `/v1/opportunities` API:
schema-version metadata is present, no internal-only fields ever serialize, the
route delegates to the same pipeline run as the deprecated demo feed (no
duplicated business logic), and the category filter behaves like the old
static-data route it replaces.
"""

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.app.logan_feed import run_demo_feed
from backend.app.main import app
from backend.app.opportunities import OPPORTUNITIES_SCHEMA_VERSION, run_opportunities

client = TestClient(app)


def test_opportunities_response_has_schema_version():
    result = run_opportunities()
    assert result.schema_version == OPPORTUNITIES_SCHEMA_VERSION
    assert result.schema_version == "1.0"


def test_opportunities_response_has_no_internal_score_fields():
    result = run_opportunities()
    payload = result.model_dump()
    flat = str(payload)
    assert "priority_score" not in flat
    assert "internal_rank_score" not in flat


def test_opportunities_matches_demo_feed_pipeline_output():
    """Both routes must be thin wrappers over the same pipeline run -- not two
    independent computations that could silently drift apart.
    """
    opportunities_result = run_opportunities()
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


def test_demo_feed_route_still_works_but_is_deprecated():
    demo_route = next(
        r for r in app.routes if isinstance(r, APIRoute) and r.path == "/v1/demo/feed"
    )
    assert demo_route.deprecated is True
    response = client.get("/v1/demo/feed")
    assert response.status_code == 200
