"""ADR-084 -- the Beta 1 company-filing catalyst contract (SEC Form 8-K).

A filing becomes an opportunity input only when a governed rule validly
fires on its structured fields: the form type and the item numbers the
issuer itself assigned. Nothing here reads the filing's text, estimates
importance, or scores materiality. An 8-K existing is not a reason to
surface anything; most 8-K items are deliberately not governed.

The issuer's own item designation is the only "materiality" used: the SEC
form defines each item, and the issuer decided the event belonged under it.
STRATUS repeats that designation and adds nothing to it.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Optional

from .qualification_shadow import QualificationState

# --- governed taxonomy ---------------------------------------------------------

STOCK_FILING_RESULTS_REPORTED = "STOCK_FILING_RESULTS_REPORTED"
STOCK_FILING_LEADERSHIP_CHANGE = "STOCK_FILING_LEADERSHIP_CHANGE"
STOCK_FILING_MATERIAL_AGREEMENT = "STOCK_FILING_MATERIAL_AGREEMENT"
STOCK_FILING_ACQUISITION_DISPOSITION = "STOCK_FILING_ACQUISITION_DISPOSITION"
STOCK_FILING_BANKRUPTCY = "STOCK_FILING_BANKRUPTCY"
STOCK_FILING_CHANGE_IN_CONTROL = "STOCK_FILING_CHANGE_IN_CONTROL"
STOCK_FILING_ACCOUNTING_CHANGE = "STOCK_FILING_ACCOUNTING_CHANGE"
STOCK_FILING_IMPAIRMENT_OR_EXIT_COSTS = "STOCK_FILING_IMPAIRMENT_OR_EXIT_COSTS"
STOCK_FILING_LISTING_COMPLIANCE = "STOCK_FILING_LISTING_COMPLIANCE"
STOCK_FILING_OBLIGATION_ACCELERATED = "STOCK_FILING_OBLIGATION_ACCELERATED"
STOCK_FILING_CYBERSECURITY_INCIDENT = "STOCK_FILING_CYBERSECURITY_INCIDENT"


@dataclass(frozen=True)
class FilingCategory:
    trigger_code: str
    # The plain, objective statement of what the item number means. Used
    # verbatim in the headline; says only what the item designation says.
    phrase: str
    # "earnings_result" for the one category that is a results release;
    # "company_event" for the rest. Used for feed composition only.
    family: Literal["earnings_result", "company_event"]


# 8-K item number -> governed category. Order is the precedence used to pick
# the primary category when one filing carries several governed items: the
# rarer and more consequential designations lead.
GOVERNED_ITEMS: dict[str, FilingCategory] = {
    "1.03": FilingCategory(
        STOCK_FILING_BANKRUPTCY, "bankruptcy or receivership", "company_event"
    ),
    "5.01": FilingCategory(
        STOCK_FILING_CHANGE_IN_CONTROL, "change in control", "company_event"
    ),
    "3.01": FilingCategory(
        STOCK_FILING_LISTING_COMPLIANCE,
        "notice of delisting or listing non-compliance",
        "company_event",
    ),
    "4.02": FilingCategory(
        STOCK_FILING_ACCOUNTING_CHANGE,
        "non-reliance on previously issued financial statements",
        "company_event",
    ),
    "4.01": FilingCategory(
        STOCK_FILING_ACCOUNTING_CHANGE,
        "change of certifying accountant",
        "company_event",
    ),
    "2.04": FilingCategory(
        STOCK_FILING_OBLIGATION_ACCELERATED,
        "event accelerating a financial obligation",
        "company_event",
    ),
    "1.05": FilingCategory(
        STOCK_FILING_CYBERSECURITY_INCIDENT,
        "material cybersecurity incident",
        "company_event",
    ),
    "2.06": FilingCategory(
        STOCK_FILING_IMPAIRMENT_OR_EXIT_COSTS, "material impairment", "company_event"
    ),
    "2.05": FilingCategory(
        STOCK_FILING_IMPAIRMENT_OR_EXIT_COSTS,
        "costs of an exit or disposal activity",
        "company_event",
    ),
    "2.01": FilingCategory(
        STOCK_FILING_ACQUISITION_DISPOSITION,
        "completed acquisition or disposition of assets",
        "company_event",
    ),
    "1.01": FilingCategory(
        STOCK_FILING_MATERIAL_AGREEMENT,
        "entry into a material definitive agreement",
        "company_event",
    ),
    "1.02": FilingCategory(
        STOCK_FILING_MATERIAL_AGREEMENT,
        "termination of a material definitive agreement",
        "company_event",
    ),
    "5.02": FilingCategory(
        STOCK_FILING_LEADERSHIP_CHANGE,
        "director or principal officer change",
        "company_event",
    ),
    "2.02": FilingCategory(
        STOCK_FILING_RESULTS_REPORTED, "financial results furnished", "earnings_result"
    ),
}

FILING_TRIGGER_CODES = frozenset(c.trigger_code for c in GOVERNED_ITEMS.values())
EARNINGS_RESULT_FILING_CODES = frozenset({STOCK_FILING_RESULTS_REPORTED})

# Items that are valid 8-K items and deliberately not governed. An item not
# in this set and not in GOVERNED_ITEMS is unrecognized, which blocks.
UNGOVERNED_ITEMS: dict[str, str] = {
    "1.04": "mine safety",
    "2.03": "creation of a direct financial obligation (routine financing)",
    "3.02": "unregistered sale of equity securities",
    "3.03": "modification of security holders' rights",
    "5.03": "amendment of articles or bylaws",
    "5.04": "temporary suspension of trading under employee benefit plans",
    "5.05": "code of ethics amendment or waiver",
    "5.06": "change in shell company status",
    "5.07": "submission of matters to a vote of security holders",
    "5.08": "shareholder director nominations",
    "6.01": "asset-backed securities",
    "6.02": "asset-backed securities",
    "6.03": "asset-backed securities",
    "6.04": "asset-backed securities",
    "6.05": "asset-backed securities",
    "7.01": "Regulation FD disclosure (catch-all)",
    "8.01": "other events (catch-all)",
    "9.01": "financial statements and exhibits",
}

GOVERNED_FORMS = frozenset({"8-K", "8-K/A"})

# A filing older than this at detection does not start an opportunity. Aging
# after detection belongs to the lifecycle tracker. Provisional (REV4 2A.8):
# owner and review date to be assigned.
FILING_MAX_AGE_AT_DETECTION = timedelta(days=14)

REASON_CODES: dict[str, tuple[QualificationState, str]] = {
    "qualified": ("qualified", "A governed 8-K item validly fired."),
    "no_governed_item": (
        "not_qualified",
        "The filing carries no item STRATUS governs.",
    ),
    "routine_financing_not_governed": (
        "not_qualified",
        "A material agreement filed together with a new financial obligation "
        "is a financing; STRATUS cannot tell deterministically whether it is "
        "meaningful, so it is not surfaced.",
    ),
    "form_not_governed": ("not_qualified", "Only Form 8-K and 8-K/A are governed."),
    "filing_too_old": (
        "blocked_stale_or_missing_required_fields",
        "The filing is older than the allowed age at detection.",
    ),
    "accession_missing": (
        "blocked_stale_or_missing_required_fields",
        "The filing has no accession number.",
    ),
    "filing_timestamp_missing": (
        "blocked_stale_or_missing_required_fields",
        "The filing has no acceptance timestamp.",
    ),
    "items_missing": (
        "blocked_stale_or_missing_required_fields",
        "The filing lists no items.",
    ),
    "source_missing": (
        "blocked_stale_or_missing_required_fields",
        "The filing has no source identity.",
    ),
    "issuer_mismatch": (
        "blocked_invalid_input",
        "The filing's issuer is not the company it was fetched for.",
    ),
    "accession_malformed": (
        "blocked_invalid_input",
        "The accession number is not in the SEC format.",
    ),
    "item_unrecognized": (
        "blocked_invalid_input",
        "The filing lists an item number that is not a known 8-K item.",
    ),
    "filing_in_future": (
        "blocked_invalid_input",
        "The acceptance timestamp is later than now.",
    ),
}

_STATE_PRECEDENCE: tuple[QualificationState, ...] = (
    "blocked_invalid_input",
    "blocked_incomparable_basis",
    "blocked_stale_or_missing_required_fields",
    "not_qualified",
    "qualified",
)


@dataclass(frozen=True)
class FilingQualification:
    state: QualificationState
    reason_codes: tuple[str, ...]
    # Set only when state == "qualified".
    primary: Optional[FilingCategory] = None
    primary_item: Optional[str] = None
    # Every governed item in the filing, primary first. Several items in one
    # filing support one opportunity; they are never separate opportunities.
    governed_items: tuple[str, ...] = ()

    @property
    def is_qualified(self) -> bool:
        return self.state == "qualified"


def _accession_ok(accession: str) -> bool:
    parts = accession.split("-")
    return (
        len(parts) == 3
        and [len(p) for p in parts] == [10, 2, 6]
        and all(p.isdigit() for p in parts)
    )


def parse_items(items: object) -> list[str]:
    if isinstance(items, str):
        raw = items.split(",")
    elif isinstance(items, (list, tuple)):
        raw = [str(i) for i in items]
    else:
        return []
    return [i.strip() for i in raw if i and i.strip()]


def qualify_filing(
    *,
    form: Optional[str],
    items: object,
    accession_number: Optional[str],
    accepted_at: Optional[datetime],
    now: datetime,
    source_id: Optional[str],
    expected_issuer: Optional[str],
    filing_issuer: Optional[str],
) -> FilingQualification:
    """Pure. Did a governed catalyst rule validly fire on this filing?"""
    codes: list[str] = []
    parsed = parse_items(items)

    if not source_id:
        codes.append("source_missing")
    if not accession_number:
        codes.append("accession_missing")
    elif not _accession_ok(accession_number):
        codes.append("accession_malformed")
    if accepted_at is None:
        codes.append("filing_timestamp_missing")
    elif accepted_at > now + timedelta(minutes=5):
        codes.append("filing_in_future")
    elif now - accepted_at > FILING_MAX_AGE_AT_DETECTION:
        codes.append("filing_too_old")
    if not expected_issuer or not filing_issuer or expected_issuer != filing_issuer:
        codes.append("issuer_mismatch")
    if form not in GOVERNED_FORMS:
        codes.append("form_not_governed")
    if not parsed:
        codes.append("items_missing")
    elif any(i not in GOVERNED_ITEMS and i not in UNGOVERNED_ITEMS for i in parsed):
        codes.append("item_unrecognized")

    governed = [i for i in GOVERNED_ITEMS if i in parsed]  # precedence order
    # A material agreement filed with a new direct financial obligation is a
    # financing (a credit facility, a notes offering). Whether a financing
    # is meaningful cannot be decided from structured fields, so the
    # agreement items do not qualify in that combination.
    if "2.03" in parsed:
        without_financing = [i for i in governed if i not in ("1.01", "1.02")]
        if governed and not without_financing:
            codes.append("routine_financing_not_governed")
        governed = without_financing
    if parsed and not governed and "routine_financing_not_governed" not in codes:
        if "item_unrecognized" not in codes:
            codes.append("no_governed_item")

    if not codes:
        codes.append("qualified")
    ordered = tuple(dict.fromkeys(codes))
    states = {REASON_CODES[c][0] for c in ordered}
    state = next(s for s in _STATE_PRECEDENCE if s in states)
    if state != "qualified":
        return FilingQualification(state=state, reason_codes=ordered)
    return FilingQualification(
        state="qualified",
        reason_codes=ordered,
        primary=GOVERNED_ITEMS[governed[0]],
        primary_item=governed[0],
        governed_items=tuple(governed),
    )


def describe_filing(
    qualification: FilingQualification, *, form: str, filing_date: str
) -> str:
    """The objective one-line statement used as the signal's value. Built
    only from the form, the issuer-assigned item and the filing date. No
    parentheses: the headline template wraps this text in its own."""
    assert qualification.is_qualified and qualification.primary is not None
    amended = "amended disclosure, " if form == "8-K/A" else ""
    return (
        f"{form} Item {qualification.primary_item}: {amended}"
        f"{qualification.primary.phrase}, filed {filing_date}"
    )
