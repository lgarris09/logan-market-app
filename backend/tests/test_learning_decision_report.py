"""V2.3B Phase 2 (Learning-Driven STRATUS) Block 10 -- Learning Decision
Report (backend/app/learning_decision_report.py) and
GET /v1/dev/learning-decision.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.learning_decision_report import (
    attention_judgment_for,
    build_learning_decision_report,
)
from backend.app.logan_feed import reset_pipeline_state
from backend.app.main import app
from backend.app.watch import create_watch
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider

client = TestClient(app)


@pytest.fixture(autouse=True)
def _no_real_fmp_calls(monkeypatch):
    """This report's World section calls build_ticker_quality_report(),
    which makes real FMP requests -- mocked here to an always-empty
    response (mirrors test_opportunity_quality_report.py's own pattern) so
    these tests never depend on real network access or a configured key,
    and stay fast/deterministic."""
    empty_client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[]))
    )
    monkeypatch.setattr(
        "backend.app.opportunity_quality_report.FmpEarningsProvider",
        lambda *a, **kw: FmpEarningsProvider(
            api_key="test-key-not-real", client=empty_client
        ),
    )
    monkeypatch.setattr(
        "backend.app.opportunity_quality_report.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real", client=empty_client
        ),
    )


def test_attention_judgment_mapping_matches_mobile():
    assert attention_judgment_for("alert") == "High attention"
    assert attention_judgment_for("wheel") == "High attention"
    assert attention_judgment_for("digest") == "Worth a look"
    assert attention_judgment_for("feed_card") == "Worth a look"
    assert attention_judgment_for("background") == "Developing"


def test_report_includes_world_learned_relevance_and_attention_sections():
    reset_pipeline_state()
    report = build_learning_decision_report(LOCAL_FOUNDER_USER_ID, "NVDA")
    assert "World" in report
    assert "Learned user context" in report
    assert "Personal relevance" in report
    assert "Attention decision" in report
    assert "Why not higher/lower" in report


def test_watched_entity_report_cites_watch_in_personal_relevance():
    reset_pipeline_state()
    create_watch(LOCAL_FOUNDER_USER_ID, "AAPL")
    report = build_learning_decision_report(LOCAL_FOUNDER_USER_ID, "AAPL")
    assert "actively watching" in report.lower()


def test_report_for_entity_not_in_the_feed_is_honest_not_fabricated():
    reset_pipeline_state()
    report = build_learning_decision_report(LOCAL_FOUNDER_USER_ID, "ZZZZ_NOT_REAL")
    assert "not currently surfaced" in report.lower()


def test_route_requires_a_real_resolved_identity_and_returns_a_report():
    reset_pipeline_state()
    response = client.get(
        "/v1/dev/learning-decision",
        params={"entity_id": "NVDA"},
        headers={"X-Stratus-User-Id": "decision-report-user"},
    )
    assert response.status_code == 200
    assert "World" in response.json()["report"]


def test_route_never_leaks_a_key():
    import os

    old = os.environ.get("FMP_API_KEY")
    os.environ["FMP_API_KEY"] = "totally-real-secret-key-value"
    try:
        response = client.get(
            "/v1/dev/learning-decision",
            params={"entity_id": "NVDA"},
            headers={"X-Stratus-User-Id": "decision-report-user-2"},
        )
        assert "totally-real-secret-key-value" not in response.text
    finally:
        if old is not None:
            os.environ["FMP_API_KEY"] = old
        else:
            os.environ.pop("FMP_API_KEY", None)
