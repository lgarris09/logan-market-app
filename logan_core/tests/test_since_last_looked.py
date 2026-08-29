"""Stock Opportunity Logic V2.3D -- "Since You Last Looked". Pure unit tests
for compute_since_last_looked (opportunity_lifecycle/sync.py). No backend/
SQLite/Orchestrator involved -- see backend/tests/test_since_last_looked.py
for the wired-through-backend tests (real /v1/opportunities responses,
durable revision history, record_interaction, user isolation).
"""

from datetime import datetime, timezone

from logan_core.contracts import MeaningfulChangeType, OpportunityRevision
from logan_core.opportunity_lifecycle import (
    UserOpportunityKnowledge,
    compute_since_last_looked,
)

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)


def _knowledge(opened: int | None) -> UserOpportunityKnowledge:
    return UserOpportunityKnowledge(
        user_id="user-a",
        entity_id="NVDA",
        last_opened_revision=opened,
        updated_at=NOW,
    )


def _revision(
    revision: int,
    change_type: MeaningfulChangeType = "confidence_increased",
    reason: str = "reason",
) -> OpportunityRevision:
    return OpportunityRevision(
        entity_id="NVDA",
        revision=revision,
        lifecycle_state="developing",
        confidence_score=0.7,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        change_type=change_type,
        reason=reason,
        created_at=NOW,
    )


def test_no_lifecycle_tracking_returns_none():
    result = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=None,
        knowledge=None,
        revisions_since_last_open=[],
        provider_degraded=False,
        now=NOW,
    )
    assert result is None


def test_never_opened_before_is_first_view():
    """No fake "since you last looked" language for a genuine first
    exposure -- knowledge=None and an explicit last_opened_revision=None
    both mean the same thing."""
    for knowledge in (None, _knowledge(opened=None)):
        result = compute_since_last_looked(
            entity_id="NVDA",
            user_id="user-a",
            current_revision=3,
            knowledge=knowledge,
            revisions_since_last_open=[],
            provider_degraded=False,
            now=NOW,
        )
        assert result is not None
        assert result.status == "first_view"
        assert result.change_type is None
        assert result.detail is None


def test_opened_at_current_revision_is_no_material_change():
    result = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=3,
        knowledge=_knowledge(opened=3),
        revisions_since_last_open=[],
        provider_degraded=False,
        now=NOW,
    )
    assert result is not None
    assert result.status == "no_material_change"
    assert result.detail is not None
    assert "still monitoring" in result.detail.lower()


def test_opened_ahead_of_current_revision_is_no_material_change():
    """Defensive: opened should never exceed current_revision in practice
    (last_opened_revision only ever advances to a real observed revision),
    but the comparison must not misclassify this as a change if it does."""
    result = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=3,
        knowledge=_knowledge(opened=5),
        revisions_since_last_open=[],
        provider_degraded=False,
        now=NOW,
    )
    assert result is not None
    assert result.status == "no_material_change"


def test_material_change_uses_the_matching_revision():
    result = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=4,
        knowledge=_knowledge(opened=3),
        revisions_since_last_open=[
            _revision(
                4,
                change_type="trajectory_strengthening",
                reason="Trajectory strengthened.",
            )
        ],
        provider_degraded=False,
        now=NOW,
    )
    assert result is not None
    assert result.status == "material_change"
    assert result.change_type == "trajectory_strengthening"
    assert result.detail == "Trajectory strengthened."


def test_multiple_revisions_since_last_open_uses_the_latest_only():
    """Not a generic activity log -- the freshest fact wins, not a
    concatenation of every intervening revision."""
    result = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=6,
        knowledge=_knowledge(opened=3),
        revisions_since_last_open=[
            _revision(
                4, change_type="confidence_increased", reason="Confidence strengthened."
            ),
            _revision(
                6, change_type="trajectory_weakening", reason="Trajectory weakened."
            ),
            _revision(
                5, change_type="new_signal_appeared", reason="New evidence appeared."
            ),
        ],
        provider_degraded=False,
        now=NOW,
    )
    assert result is not None
    assert result.status == "material_change"
    assert result.change_type == "trajectory_weakening"
    assert result.detail == "Trajectory weakened."


def test_material_change_with_no_matching_history_falls_back_honestly():
    """The revision counter advanced but no durable history row backs it
    (e.g. persistence was off across the gap) -- an honest generic signal,
    never a fabricated specific reason."""
    result = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=4,
        knowledge=_knowledge(opened=3),
        revisions_since_last_open=[],
        provider_degraded=False,
        now=NOW,
    )
    assert result is not None
    assert result.status == "material_change"
    assert result.change_type is None
    assert result.detail is not None


def test_degraded_provider_state_overrides_no_material_change():
    result = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=3,
        knowledge=_knowledge(opened=3),
        revisions_since_last_open=[],
        provider_degraded=True,
        now=NOW,
    )
    assert result is not None
    assert result.status == "degraded"
    assert result.detail is not None
    assert "unavailable" in result.detail.lower()


def test_degraded_provider_state_does_not_override_a_real_material_change():
    """A durably-recorded revision is a historical fact, unaffected by
    whether *this specific poll's* live fetch happened to succeed."""
    result = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=4,
        knowledge=_knowledge(opened=3),
        revisions_since_last_open=[_revision(4)],
        provider_degraded=True,
        now=NOW,
    )
    assert result is not None
    assert result.status == "material_change"


def test_user_isolation_is_the_callers_responsibility_and_is_reflected_in_output():
    """The function itself is stateless/pure -- isolation comes from the
    caller passing each user's own knowledge; this just proves the output
    carries the given user_id through untouched, never swapped."""
    result_a = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=3,
        knowledge=_knowledge(opened=None),
        revisions_since_last_open=[],
        provider_degraded=False,
        now=NOW,
    )
    result_b = compute_since_last_looked(
        entity_id="NVDA",
        user_id="user-b",
        current_revision=3,
        knowledge=UserOpportunityKnowledge(
            user_id="user-b",
            entity_id="NVDA",
            last_opened_revision=3,
            updated_at=NOW,
        ),
        revisions_since_last_open=[],
        provider_degraded=False,
        now=NOW,
    )
    assert result_a is not None and result_a.user_id == "user-a"
    assert result_a.status == "first_view"
    assert result_b is not None and result_b.user_id == "user-b"
    assert result_b.status == "no_material_change"
