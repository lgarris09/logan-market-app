"""ADR-084 -- maps a qualified CompanyFiling into the RawSignal the
pipeline consumes. A receptor captures; it decides nothing. Qualification is
trigger_detection's (logan_core/trigger_detection/filings.py); this module
is only called for a filing that already qualified, and carries every
provenance field through unchanged.
"""

from logan_core.contracts import RawSignal
from logan_core.trigger_detection.filings import FilingQualification, describe_filing

from .providers.base import CompanyFiling

COMPANY_FILING_SIGNAL_TYPE = "company_filing"


def filing_to_raw_signal(
    filing: CompanyFiling, qualification: FilingQualification
) -> RawSignal:
    if not qualification.is_qualified:
        raise ValueError("only a qualified filing becomes a signal")
    if filing.accepted_at is None or filing.filing_date is None:
        raise ValueError("a qualified filing always has its timestamps")
    raw_value: dict = {
        "entity_id": filing.entity_id,
        "entity_type": "ticker",
        "signal_type": COMPANY_FILING_SIGNAL_TYPE,
        "value": describe_filing(
            qualification, form=filing.form, filing_date=filing.filing_date
        ),
        "unit": None,
        "form": filing.form,
        "items": filing.items,
        "accession_number": filing.accession_number,
        "accepted_at": filing.accepted_at.isoformat(),
        "filing_date": filing.filing_date,
        "issuer_ticker": filing.issuer_ticker,
        "issuer_cik": filing.issuer_cik,
    }
    if filing.report_date:
        raw_value["report_date"] = filing.report_date
    if filing.filing_url:
        raw_value["filing_url"] = filing.filing_url
    return RawSignal(
        domain="stocks",
        source_id=filing.source_id,
        source_name=filing.source_name,
        raw_value=raw_value,
        # The acceptance time is when the event became public -- the same
        # role report_timestamp plays for an earnings report.
        captured_at=filing.accepted_at,
    )
