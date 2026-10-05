"""Shadow replay of the proposed qualification rules against real provider
data (ADR-078). Offline: reads two captured JSON files. Changes nothing.

    python 2026-10-05-qualification_shadow_replay.py <provider_earnings_rows.json> <provider_quotes.json> [out.json]

Two passes over the earnings rows:

  STRICT        only what the provider row actually establishes. Unknown
                stays unknown.
  HYPOTHETICAL  the same rows *as if* fiscal period, pre-release estimate
                timestamp, currency, split status, restatement status and
                revenue definition had all been established. This is NOT a
                result; it exists only to see how the revenue band table
                would distribute once the inputs can be proven. EPS basis is
                left unknown even here, because nothing available can
                establish it.
"""

import collections
import json
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from logan_core.trigger_detection.qualification_shadow import (  # noqa: E402
    EstimateActualEvidence,
    qualify_eps_beat,
    qualify_price_move,
    qualify_revenue_surprise,
)


def _reported(rows):
    return [row for row in rows if row.get("epsActual") is not None][0]


def _strict(symbol, row, actual_key, estimate_key):
    release = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return EstimateActualEvidence(
        actual=row.get(actual_key),
        estimate=row.get(estimate_key),
        actual_issuer=symbol,  # one row, one symbol
        estimate_issuer=symbol,
        release_at=release,  # the row's report date (a date, not a time)
        actual_source="fmp:/earnings",
        estimate_source="fmp:/earnings",
        # Not in the payload: fiscal period, estimate timestamp, currency,
        # split status, restatement status, EPS basis, share basis, revenue
        # definition. All stay None.
    )


def _hypothetical(evidence):
    return replace(
        evidence,
        actual_fiscal_period="established",
        estimate_fiscal_period="established",
        estimate_as_of=evidence.release_at - timedelta(days=1),
        actual_currency="USD",
        estimate_currency="USD",
        split_between=False,
        restated=False,
        revenue_definition_matched=True,
    )


def _row(symbol, kind, result, extra=None):
    return {
        "symbol": symbol,
        "trigger_family": kind,
        "state": result.state,
        "reason_codes": list(result.reason_codes),
        "magnitude_pct": None if result.magnitude_pct is None else round(result.magnitude_pct, 2),
        "materiality": result.materiality,
        "direction": result.direction,
        **(extra or {}),
    }


def main() -> None:
    earnings = json.load(open(sys.argv[1], encoding="utf-8"))["symbols"]
    quotes = json.load(open(sys.argv[2], encoding="utf-8"))["quotes"]

    strict, hypothetical, price = [], [], []
    for symbol in sorted(earnings):
        row = _reported(earnings[symbol]["rows"])
        eps = _strict(symbol, row, "epsActual", "epsEstimated")
        revenue = _strict(symbol, row, "revenueActual", "revenueEstimated")
        inputs = {
            "report_date": row["date"],
            "eps_actual": row.get("epsActual"),
            "eps_estimate": row.get("epsEstimated"),
            "revenue_actual": row.get("revenueActual"),
            "revenue_estimate": row.get("revenueEstimated"),
        }
        strict.append(_row(symbol, "earnings_eps_beat", qualify_eps_beat(eps), inputs))
        strict.append(_row(symbol, "revenue_surprise", qualify_revenue_surprise(revenue)))
        hypothetical.append(
            _row(symbol, "earnings_eps_beat", qualify_eps_beat(_hypothetical(eps)))
        )
        hypothetical.append(
            _row(symbol, "revenue_surprise", qualify_revenue_surprise(_hypothetical(revenue)))
        )

    for symbol in sorted(quotes):
        q = quotes[symbol]
        quote_at = (
            datetime.fromtimestamp(q["timestamp"], tz=timezone.utc) if q.get("timestamp") else None
        )
        # Evaluated as of the quote's own time: this replays the rule, not
        # how long ago the snapshot was taken.
        result = qualify_price_move(
            price=q.get("price"),
            previous_close=q.get("previousClose"),
            quote_at=quote_at,
            now=quote_at or datetime.now(timezone.utc),
            source_id="fmp:/quote",
        )
        change = None
        if q.get("price") and q.get("previousClose"):
            change = round((q["price"] - q["previousClose"]) / q["previousClose"] * 100, 2)
        price.append(_row(symbol, "price_move", result, {"observed_change_pct": change}))

    def dist(rows, family, key):
        return dict(
            sorted(
                collections.Counter(
                    str(r[key]) for r in rows if r["trigger_family"] == family
                ).items()
            )
        )

    def reasons(rows, family):
        counter = collections.Counter(
            code for r in rows if r["trigger_family"] == family for code in r["reason_codes"]
        )
        return dict(counter.most_common())

    summary = {
        "strict": {
            "earnings_eps_beat_states": dist(strict, "earnings_eps_beat", "state"),
            "earnings_eps_beat_reasons": reasons(strict, "earnings_eps_beat"),
            "revenue_surprise_states": dist(strict, "revenue_surprise", "state"),
            "revenue_surprise_reasons": reasons(strict, "revenue_surprise"),
        },
        "hypothetical_inputs_established": {
            "earnings_eps_beat_states": dist(hypothetical, "earnings_eps_beat", "state"),
            "revenue_surprise_states": dist(hypothetical, "revenue_surprise", "state"),
            "revenue_surprise_bands": dist(hypothetical, "revenue_surprise", "materiality"),
        },
        "price_move": {
            "states": dist(price, "price_move", "state"),
            "bands": dist(price, "price_move", "materiality"),
        },
    }

    print("STRICT -- what the current provider row can establish")
    for r in strict:
        if r["trigger_family"] == "earnings_eps_beat":
            print(f"  {r['symbol']:<6} EPS {r['eps_actual']} vs {r['eps_estimate']:<7} -> {r['state']}")
    print("  reasons:", summary["strict"]["earnings_eps_beat_reasons"])
    print("  revenue:", summary["strict"]["revenue_surprise_states"])
    print("\nHYPOTHETICAL -- revenue bands if the inputs were established (not a result)")
    for r in hypothetical:
        if r["trigger_family"] == "revenue_surprise":
            print(f"  {r['symbol']:<6} {str(r['magnitude_pct']):>7}%  {r['state']:<14} {r['materiality'] or '-'}")
    print("\nPRICE MOVE -- today's quotes for the 30 monitored symbols")
    for r in price:
        print(f"  {r['symbol']:<6} {str(r['observed_change_pct']):>7}%  {r['state']:<14} {r['materiality'] or '-'}")
    print("\nSUMMARY", json.dumps(summary, indent=1))
    if len(sys.argv) > 3:
        json.dump(
            {"summary": summary, "strict": strict, "hypothetical": hypothetical, "price_move": price},
            open(sys.argv[3], "w", encoding="utf-8", newline="\n"),
            indent=1,
        )


if __name__ == "__main__":
    main()
