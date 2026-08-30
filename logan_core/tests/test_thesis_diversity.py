"""Universe Manager V1a Block 10 -- deterministic top-band thesis
diversity (logan_core/thesis/diversity.py).
"""

from uuid import uuid4

from logan_core.contracts import ThesisMetadata
from logan_core.thesis.diversity import ThesisCandidate, apply_diversity_caps


def _metadata(
    entity_id="AAPL",
    sector="Technology",
    signal_family="earnings",
    driver="EARNINGS_RESULT",
) -> ThesisMetadata:
    return ThesisMetadata(
        event_id=uuid4(),
        primary_entity_id=entity_id,
        sector=sector,
        primary_signal_family=signal_family,
        market_driver_tag=driver,
        thesis_state="developing",
    )


def _candidate(rank, is_watched=False, **metadata_kwargs) -> ThesisCandidate:
    return ThesisCandidate(
        event_id=uuid4(),
        rank=rank,
        metadata=_metadata(**metadata_kwargs),
        is_watched=is_watched,
    )


def test_fewer_than_top_n_candidates_are_all_selected_untouched():
    candidates = [_candidate(1, entity_id="AAPL"), _candidate(2, entity_id="MSFT")]
    # Both candidates default to the same sector/signal_family/driver combo --
    # relax every non-entity cap so this test isolates "no entity conflict,
    # nothing suppressed," not an incidental driver/sector/family collision.
    result = apply_diversity_caps(
        candidates, top_n=5, sector_cap=10, signal_family_cap=10, sector_driver_cap=10
    )
    assert len(result.selected) == 2
    assert result.suppressed == []


def test_entity_cap_suppresses_a_second_thesis_for_the_same_entity():
    candidates = [
        _candidate(1, entity_id="AAPL"),
        _candidate(2, entity_id="AAPL"),
    ]
    result = apply_diversity_caps(candidates, top_n=5)
    assert len(result.selected) == 1
    assert result.selected[0].rank == 1
    assert len(result.suppressed) == 1
    assert result.suppressed[0].suppression_reason == "ENTITY_CAP"
    assert result.suppressed[0].blocking_thesis_id == candidates[0].event_id


def test_watch_never_bypasses_the_entity_cap():
    candidates = [
        _candidate(1, entity_id="AAPL"),
        _candidate(2, entity_id="AAPL", is_watched=True),
    ]
    result = apply_diversity_caps(candidates, top_n=5)
    assert len(result.selected) == 1
    assert result.suppressed[0].suppression_reason == "ENTITY_CAP"


def test_sector_cap_suppresses_the_third_thesis_from_the_same_sector():
    candidates = [
        _candidate(1, entity_id="A", sector="Technology"),
        _candidate(2, entity_id="B", sector="Technology"),
        _candidate(3, entity_id="C", sector="Technology"),
    ]
    # signal_family_cap/sector_driver_cap relaxed to isolate the sector cap
    # specifically -- these three otherwise share the same default
    # signal_family/driver too.
    result = apply_diversity_caps(
        candidates, top_n=5, sector_cap=2, signal_family_cap=10, sector_driver_cap=10
    )
    assert len(result.selected) == 2
    assert result.suppressed[0].suppression_reason == "SECTOR_CAP"


def test_signal_family_cap_suppresses_the_third_thesis_of_the_same_family():
    candidates = [
        _candidate(1, entity_id="A", sector="Technology", signal_family="earnings"),
        _candidate(2, entity_id="B", sector="Healthcare", signal_family="earnings"),
        _candidate(3, entity_id="C", sector="Energy", signal_family="earnings"),
    ]
    result = apply_diversity_caps(candidates, top_n=5, signal_family_cap=2)
    assert len(result.selected) == 2
    assert result.suppressed[0].suppression_reason == "SIGNAL_FAMILY_CAP"


def test_driver_cap_suppresses_the_second_same_sector_driver_combo():
    candidates = [
        _candidate(1, entity_id="A", sector="Technology", driver="EARNINGS_RESULT"),
        _candidate(2, entity_id="B", sector="Technology", driver="EARNINGS_RESULT"),
    ]
    result = apply_diversity_caps(
        candidates, top_n=5, sector_cap=5, sector_driver_cap=1
    )
    assert len(result.selected) == 1
    assert result.suppressed[0].suppression_reason == "DRIVER_CAP"


def test_watch_bypasses_exactly_one_violated_cap():
    candidates = [
        _candidate(
            1,
            entity_id="A",
            sector="Technology",
            signal_family="earnings",
            driver="EARNINGS_RESULT",
        ),
        _candidate(
            2,
            entity_id="B",
            sector="Technology",
            signal_family="analyst_grade",
            driver="ANALYST_REASSESSMENT",
        ),
        _candidate(
            3,
            entity_id="C",
            sector="Technology",
            signal_family="price",
            driver="PRICE_DISLOCATION",
            is_watched=True,
        ),
    ]
    # Candidate 3 violates only SECTOR_CAP (signal_family/driver all differ
    # from 1 and 2) -- Watch bypasses that one cap.
    result = apply_diversity_caps(
        candidates, top_n=5, sector_cap=2, signal_family_cap=5, sector_driver_cap=5
    )
    assert len(result.selected) == 3
    assert result.suppressed == []


def test_watch_does_not_bypass_two_simultaneously_violated_caps():
    candidates = [
        _candidate(
            1,
            entity_id="A",
            sector="Technology",
            signal_family="earnings",
            driver="EARNINGS_RESULT",
        ),
        _candidate(
            2,
            entity_id="B",
            sector="Technology",
            signal_family="earnings",
            driver="EARNINGS_GUIDANCE",
        ),
        _candidate(
            3,
            entity_id="C",
            sector="Technology",
            signal_family="earnings",
            driver="EARNINGS_RESULT",
            is_watched=True,
        ),
    ]
    # Candidates 1 and 2 use distinct drivers so neither trips the driver
    # cap against each other, filling exactly the sector (2) and
    # signal_family (2) caps. Candidate 3 then violates BOTH SECTOR_CAP and
    # SIGNAL_FAMILY_CAP simultaneously -- Watch only bypasses one cap, not
    # several at once, so it must still be suppressed.
    result = apply_diversity_caps(
        candidates, top_n=5, sector_cap=2, signal_family_cap=2, sector_driver_cap=10
    )
    assert len(result.selected) == 2
    assert len(result.suppressed) == 1
    assert result.suppressed[0].event_id == candidates[2].event_id


def test_stops_once_top_n_slots_are_filled():
    candidates = [_candidate(i, entity_id=f"E{i}", sector=f"S{i}") for i in range(1, 8)]
    # Distinct entities/sectors already avoid entity/sector/driver caps
    # (sector is part of the driver-cap key too); signal_family_cap is
    # relaxed since every candidate defaults to the same "earnings" family.
    result = apply_diversity_caps(candidates, top_n=5, signal_family_cap=10)
    assert len(result.selected) == 5
    assert [c.rank for c in result.selected] == [1, 2, 3, 4, 5]
    # Candidates beyond the top_n were never even considered/suppressed --
    # they simply didn't rank high enough, unrelated to diversity.
    assert result.suppressed == []


def test_a_suppressed_candidates_underlying_thesis_is_never_mutated():
    candidates = [
        _candidate(1, entity_id="AAPL"),
        _candidate(2, entity_id="AAPL"),
    ]
    before_metadata = candidates[1].metadata.model_copy()
    apply_diversity_caps(candidates, top_n=5)
    assert candidates[1].metadata == before_metadata


def test_selection_is_deterministic_across_repeated_calls():
    candidates = [
        _candidate(1, entity_id="A", sector="Technology"),
        _candidate(2, entity_id="B", sector="Technology"),
        _candidate(3, entity_id="C", sector="Technology"),
    ]
    first = apply_diversity_caps(candidates, top_n=5, sector_cap=2)
    second = apply_diversity_caps(candidates, top_n=5, sector_cap=2)
    assert [c.event_id for c in first.selected] == [c.event_id for c in second.selected]
    assert [s.event_id for s in first.suppressed] == [
        s.event_id for s in second.suppressed
    ]


def test_missing_sector_falls_back_to_unknown_bucket_not_a_crash():
    candidates = [
        _candidate(1, entity_id="A", sector=None),
        _candidate(2, entity_id="B", sector=None),
        _candidate(3, entity_id="C", sector=None),
    ]
    result = apply_diversity_caps(
        candidates, top_n=5, sector_cap=2, signal_family_cap=10, sector_driver_cap=10
    )
    assert len(result.selected) == 2
    assert result.suppressed[0].suppression_reason == "SECTOR_CAP"
