"""Self-corroboration fix (ADR-076), through the real feed pipeline: a
source re-reporting changed content no longer raises confidence, and
nothing else about the feed changes.

The "before" side is produced by the same code with the per-event source
memory wiped before every signal, which reproduces the old rule exactly
(any non-identical observation counted as corroboration).
"""

import backend.app.logan_feed as feed
from logan_core.world_model import WorldModel

USER = "demo_user"
POLLS = 12


def _run() -> list[dict]:
    feed.reset_pipeline_state()
    polls = []
    for _ in range(POLLS):
        items, _now, _alerts, _degraded = feed._run_feed_pipeline(USER)
        polls.append(
            {
                item.entity_id: {
                    "event_id": item.event_id,
                    "rank": item.rank,
                    "signal_type": item.signal_type,
                    "score": item.confidence_score,
                    "label": item.confidence_label,
                    "lifecycle": item.lifecycle_state,
                    "revision": item.opportunity_revision,
                }
                for item in items
            }
        )
    return polls


def _run_with_old_rule(monkeypatch) -> list[dict]:
    original = WorldModel.process

    def old_rule(self, *args, **kwargs):
        self._event_sources.clear()
        return original(self, *args, **kwargs)

    monkeypatch.setattr(WorldModel, "process", old_rule)
    try:
        return _run()
    finally:
        monkeypatch.setattr(WorldModel, "process", original)


def test_the_old_rule_did_inflate_and_the_fix_removes_it(monkeypatch):
    before = _run_with_old_rule(monkeypatch)
    after = _run()

    inflated = {
        entity
        for entity in before[-1]
        if before[-1][entity]["score"] > after[-1][entity]["score"] + 1e-6
    }
    assert inflated, "expected at least one self-corroborated entity in the fixture"
    # Never higher than before, for any entity, on any poll.
    for old_poll, new_poll in zip(before, after, strict=True):
        for entity, new in new_poll.items():
            assert new["score"] <= old_poll[entity]["score"] + 1e-6


def test_repeated_polling_no_longer_raises_any_score(monkeypatch):
    """With no new source, later polls can only match or decay (recency),
    never climb. Under the old rule some entities climbed poll over poll."""
    after = _run()
    for entity in after[0]:
        scores = [poll[entity]["score"] for poll in after if entity in poll]
        assert max(scores) <= scores[0] + 1e-6

    before = _run_with_old_rule(monkeypatch)
    climbed = [
        entity
        for entity in before[0]
        if before[-1][entity]["score"] > before[0][entity]["score"] + 1e-3
    ]
    assert climbed  # the behaviour being removed was real


def test_qualification_ids_and_lifecycle_are_unchanged(monkeypatch):
    before = _run_with_old_rule(monkeypatch)
    after = _run()

    for old_poll, new_poll in zip(before, after, strict=True):
        # Qualification: exactly the same opportunities surface.
        assert set(new_poll) == set(old_poll)
        for entity in new_poll:
            assert new_poll[entity]["signal_type"] == old_poll[entity]["signal_type"]
            assert new_poll[entity]["lifecycle"] == old_poll[entity]["lifecycle"]

    # Stable IDs: one event_id per entity for the whole run, both ways.
    for run in (before, after):
        for entity in run[0]:
            assert len({poll[entity]["event_id"] for poll in run}) == 1


def test_entities_that_were_never_self_corroborated_are_untouched(monkeypatch):
    before = _run_with_old_rule(monkeypatch)
    after = _run()
    untouched = [
        entity
        for entity in after[-1]
        if all(
            abs(new[entity]["score"] - old[entity]["score"]) < 1e-3
            for old, new in zip(before, after, strict=True)
        )
    ]
    assert len(untouched) >= len(after[-1]) - 3  # the fix is narrow
    for entity in untouched:
        for old, new in zip(before, after, strict=True):
            assert new[entity]["label"] == old[entity]["label"]
            assert new[entity]["revision"] == old[entity]["revision"]
    # Relative order among untouched entities is preserved.
    order = lambda poll: [  # noqa: E731
        e for e in sorted(poll, key=lambda k: poll[k]["rank"]) if e in untouched
    ]
    assert order(after[-1]) == order(before[-1])


def test_the_fix_never_creates_a_revision_the_old_rule_did_not(monkeypatch):
    before = _run_with_old_rule(monkeypatch)
    after = _run()
    for entity in after[-1]:
        # Demo entities are not lifecycle-tracked (revision None -> 0).
        assert (after[-1][entity]["revision"] or 0) <= (
            before[-1][entity]["revision"] or 0
        )
