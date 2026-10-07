"""Read-only replay: Beta 1 feed composition with the EPS gate on and the
SEC 8-K catalyst path added. No network; reads the real cohort filing sample
(logan_core/tests/data/sec_8k_cohort_sample_2026-10-07.json) and the gated
baseline (docs/baselines/2026-10-06-gated-feed/gated_feed_replay.json).

Run from the repository root:
    python docs/sessions/2026-10-07-catalyst_feed_replay.py
"""

import collections
import json
import statistics
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from logan_core.receptors.providers.sec_edgar import SEC_SOURCE_ID  # noqa: E402
from logan_core.trigger_detection.filings import qualify_filing  # noqa: E402

SAMPLE = "logan_core/tests/data/sec_8k_cohort_sample_2026-10-07.json"
BASELINE = "docs/baselines/2026-10-06-gated-feed/gated_feed_replay.json"
EXPIRE = timedelta(hours=336)  # the lifecycle expire window for filing codes
STALE = timedelta(hours=168)
MONITORING = timedelta(hours=48)

rows = json.load(open(SAMPLE, encoding="utf-8"))
baseline = json.load(open(BASELINE, encoding="utf-8"))
analyst_standing = sorted(baseline["feed_items_surviving_gate"])  # ABT, CAT, DE

qualified = []
declined = collections.Counter()
for ticker, form, filing_date, accepted, report_date, items, accession in rows:
    accepted_at = datetime.fromisoformat(accepted.replace("Z", "+00:00"))
    q = qualify_filing(
        form=form,
        items=items,
        accession_number=accession,
        accepted_at=accepted_at,
        now=accepted_at + timedelta(hours=1),  # detected within the hour
        source_id=SEC_SOURCE_ID,
        expected_issuer=ticker,
        filing_issuer=ticker,
    )
    if q.is_qualified:
        qualified.append(
            {
                "ticker": ticker,
                "form": form,
                "accepted_at": accepted_at,
                "filing_date": filing_date,
                "items": items,
                "primary_item": q.primary_item,
                "code": q.primary.trigger_code,
                "family": q.primary.family,
                "accession": accession,
            }
        )
    else:
        declined[",".join(q.reason_codes)] += 1


def standing(as_of):
    """One opportunity per company: its newest qualified filing still inside
    the expire window."""
    by_company = {}
    for f in qualified:
        age = as_of - f["accepted_at"]
        if timedelta(0) <= age <= EXPIRE:
            if (
                f["ticker"] not in by_company
                or f["accepted_at"] > by_company[f["ticker"]]["accepted_at"]
            ):
                by_company[f["ticker"]] = f
    return by_company


def bucket(age):
    if age <= MONITORING:
        return "active (first 48h)"
    if age <= STALE:
        return "cooling (2-7 days)"
    return "stale (7-14 days)"


def compose(as_of):
    filings = standing(as_of)
    companies = {}
    for t in analyst_standing:
        companies[t] = ["analyst_grade"]
    for t, f in filings.items():
        companies.setdefault(t, []).insert(0, f["family"])
    primary = collections.Counter(v[0] for v in companies.values())
    return {
        "as_of": as_of.isoformat(),
        "opportunities": len(companies),
        "unique_companies": len(companies),
        "by_primary_family": dict(primary),
        "share_by_family_pct": {
            k: round(100 * v / len(companies), 1) for k, v in primary.items()
        },
        "largest_family_share_pct": round(
            100 * max(primary.values()) / len(companies), 1
        ),
        "multi_family_opportunities": sorted(
            t for t, v in companies.items() if len(v) > 1
        ),
        "filing_opportunities": {
            t: {
                "item": f["primary_item"],
                "form": f["form"],
                "filed": f["filing_date"],
                "lifecycle_bucket": bucket(as_of - f["accepted_at"]),
            }
            for t, f in sorted(filings.items())
        },
        "new_companies_added_by_catalysts": sorted(
            set(filings) - set(analyst_standing)
        ),
        "lifecycle_buckets": dict(
            collections.Counter(
                bucket(as_of - f["accepted_at"]) for f in filings.values()
            )
        ),
    }


out = {
    "sample": {
        "filings": len(rows),
        "qualified": len(qualified),
        "declined_by_reason": dict(declined),
        "qualified_by_code": dict(collections.Counter(f["code"] for f in qualified)),
        "companies_with_a_qualified_filing": len({f["ticker"] for f in qualified}),
    },
    "gated_baseline": {
        "opportunities": len(analyst_standing),
        "by_family": {"analyst_grade": len(analyst_standing)},
        "companies": analyst_standing,
    },
    "with_catalysts_at_window_start": compose(
        datetime(2026, 10, 5, 20, 57, tzinfo=timezone.utc)
    ),
    "with_catalysts_at_sample_time": compose(
        datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc)
    ),
}

# Day by day: how many companies carry a standing filing opportunity, and how
# many filings qualify that day (new opportunities or revisions).
daily = []
day = datetime(2026, 9, 4, 21, 0, tzinfo=timezone.utc)
while day <= datetime(2026, 10, 6, 21, 0, tzinfo=timezone.utc):
    s = standing(day)
    new_today = [
        f for f in qualified if day - timedelta(days=1) < f["accepted_at"] <= day
    ]
    revisions = [
        f
        for f in new_today
        if any(
            g["ticker"] == f["ticker"]
            and g["accepted_at"] < f["accepted_at"]
            and f["accepted_at"] - g["accepted_at"] <= EXPIRE
            for g in qualified
        )
    ]
    daily.append((day.date().isoformat(), len(s), len(new_today), len(revisions)))
    day += timedelta(days=1)
counts = [d[1] for d in daily]
out["daily_2026-09-04_to_10-06"] = {
    "days": len(daily),
    "standing_filing_opportunities": {
        "min": min(counts),
        "median": statistics.median(counts),
        "max": max(counts),
    },
    "days_with_a_newly_qualified_filing": sum(1 for d in daily if d[2]),
    "newly_qualified_filings": sum(d[2] for d in daily),
    "of_which_revisions_of_a_standing_opportunity": sum(d[3] for d in daily),
    "series": daily,
}
print(json.dumps(out, indent=1, default=str))
