"""BATCH-1 (V3.1.4): the Tesla demo response must not leak any internal
ranking field either, and the scenario must remain deterministic and
policy-advisory (not directive).
"""

from backend.app.logan_demo import run_tesla_demo


def test_tesla_demo_response_has_no_internal_score_fields():
    result = run_tesla_demo()
    payload = result.model_dump()
    flat = str(payload)
    assert "priority_score" not in flat
    assert "internal_rank_score" not in flat


def test_tesla_demo_is_deterministic():
    first = run_tesla_demo()
    second = run_tesla_demo()
    assert first.delivered_item.headline == second.delivered_item.headline
    assert first.confidence.classification == second.confidence.classification


def test_tesla_demo_respects_advice_boundary():
    result = run_tesla_demo()
    assert result.delivered_item.required_disclaimers
    headline = result.delivered_item.headline.lower()
    for phrase in ("buy ", "sell ", "you should"):
        assert phrase not in headline
