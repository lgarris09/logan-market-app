"""Operational Beta Hardening Block 1 -- Diagnostic Fault Codes framework
itself (logan_core/diagnostics/fault_codes.py). Wiring-site tests (fmp.py's
DATA-3xx, user_context.py's AUTH-1xx, ask_engine.py's ASK-400, watch.py's
WATCH-500) live in their own respective test files -- this file only proves
the shared framework's own contract: stable codes, secret-stripping,
bounded history, and "a healthy empty feed is never a fault."
"""

from logan_core.diagnostics import (
    FAULT_CATALOG,
    NOT_A_FAULT_NOTES,
    FaultOccurrence,
    fault_lookup,
    format_fault_catalog,
    format_recent_faults,
    recent_faults,
    record_fault,
    reset_fault_state,
    set_fault_sink,
)


def setup_function() -> None:
    reset_fault_state()


def test_every_catalog_code_matches_its_own_key():
    for code, definition in FAULT_CATALOG.items():
        assert definition.code == code


def test_every_catalog_code_matches_its_documented_family_prefix():
    for code, definition in FAULT_CATALOG.items():
        assert code.startswith(definition.family + "-")


def test_fault_lookup_known_code_is_precise_and_immediate():
    text = fault_lookup("DATA-302")
    assert "DATA-302" in text
    assert "DATA" in text
    assert FAULT_CATALOG["DATA-302"].summary in text


def test_fault_lookup_unrecognized_code_is_honest_not_a_crash():
    text = fault_lookup("ZZZZ-999")
    assert "unrecognized" in text.lower()


def test_fault_lookup_marks_registered_but_unwired_codes():
    text = fault_lookup("WATCH-501")
    assert "not yet triggered" in text.lower()


def test_fault_lookup_does_not_mark_wired_codes_as_unwired():
    text = fault_lookup("DATA-302")
    assert "not yet triggered" not in text.lower()


def test_record_fault_returns_a_stable_code_and_correlation_id():
    occurrence = record_fault("DATA-301", "test_subsystem")
    assert occurrence.code == "DATA-301"
    assert occurrence.family == "DATA"
    assert occurrence.correlation_id
    assert occurrence.subsystem == "test_subsystem"


def test_record_fault_two_calls_get_distinct_correlation_ids():
    first = record_fault("DATA-301", "test_subsystem")
    second = record_fault("DATA-301", "test_subsystem")
    assert first.correlation_id != second.correlation_id


def test_record_fault_unrecognized_code_still_records_never_raises():
    occurrence = record_fault("NOPE-1", "test_subsystem")
    assert occurrence.code == "NOPE-1"
    assert occurrence.family == "NOPE"


def test_record_fault_strips_a_key_that_looks_like_a_secret():
    record_fault(
        "DATA-301",
        "test_subsystem",
        context={"api_key": "sk-super-secret-value", "endpoint": "quote"},
    )
    occurrence = recent_faults(1)[0]
    assert "api_key" not in occurrence.safe_context
    assert occurrence.safe_context["endpoint"] == "quote"


def test_record_fault_strips_case_insensitively_and_common_variants():
    record_fault(
        "DATA-301",
        "test_subsystem",
        context={
            "Authorization": "Bearer xyz",
            "password": "hunter2",
            "credential_blob": "abc",
            "clerk_token": "abc",
        },
    )
    occurrence = recent_faults(1)[0]
    assert occurrence.safe_context == {}


def test_record_fault_truncates_an_overlong_value():
    record_fault("DATA-301", "test_subsystem", context={"detail": "x" * 5000})
    occurrence = recent_faults(1)[0]
    assert len(occurrence.safe_context["detail"]) < 5000
    assert occurrence.safe_context["detail"].endswith("...(truncated)")


def test_record_fault_never_leaks_a_real_looking_key_into_the_formatted_report():
    record_fault(
        "DATA-302", "test_subsystem", context={"fmp_api_key": "totally-real-secret"}
    )
    report = format_recent_faults()
    assert "totally-real-secret" not in report


def test_recent_faults_is_bounded():
    for i in range(250):
        record_fault("DATA-301", "test_subsystem", context={"i": str(i)})
    assert len(recent_faults(1000)) <= 200


def test_recent_faults_returns_most_recent_last():
    record_fault("DATA-301", "test_subsystem", context={"i": "first"})
    record_fault("DATA-301", "test_subsystem", context={"i": "second"})
    occurrences = recent_faults(2)
    assert occurrences[0].safe_context["i"] == "first"
    assert occurrences[1].safe_context["i"] == "second"


def test_format_recent_faults_empty_state_is_honest_not_a_fault():
    assert format_recent_faults() == "No faults recorded this process."


def test_format_fault_catalog_includes_every_registered_code():
    report = format_fault_catalog()
    for code in FAULT_CATALOG:
        assert code in report


def test_format_fault_catalog_documents_the_not_a_fault_notes():
    report = format_fault_catalog()
    for note in NOT_A_FAULT_NOTES:
        assert note in report


def test_reset_fault_state_clears_history():
    record_fault("DATA-301", "test_subsystem")
    reset_fault_state()
    assert recent_faults() == []


def test_fault_sink_receives_every_occurrence():
    """V1a Proof-Instrumentation Closeout: an injected sink (dependency
    injection, not a reverse import -- logan_core never imports
    backend/app) receives the exact same FaultOccurrence record_fault()
    itself just produced."""
    received: list[FaultOccurrence] = []
    set_fault_sink(received.append)
    try:
        occurrence = record_fault("DATA-301", "test_subsystem")
        assert received == [occurrence]
    finally:
        set_fault_sink(None)


def test_a_raising_fault_sink_never_breaks_the_caller():
    """A sink failure must never mask or interrupt the real fault the
    caller was already reporting."""

    def _raising_sink(occurrence):
        raise RuntimeError("simulated durable-mirror failure")

    set_fault_sink(_raising_sink)
    try:
        occurrence = record_fault("DATA-301", "test_subsystem")
        assert occurrence.code == "DATA-301"  # record_fault still returned normally
    finally:
        set_fault_sink(None)


def test_fault_sink_defaults_to_none_and_is_a_no_op():
    set_fault_sink(None)
    record_fault("DATA-301", "test_subsystem")  # must not raise with no sink set
