"""Before/after analysis for the PROPOSED bounded magnitude-aware trigger
contribution (design only -- this function is not production code and is
imported by nothing).

    python 2026-10-05-magnitude_before_after.py <provider_rows.json> <live_feed_baseline.json> [out.json]

Inputs: the FMP /earnings rows captured for the current earnings
opportunities, and the production feed captured on 2026-10-05.
"""

import collections
import json
import math
import re
import sys

BASE = 0.375  # 0.35 * 0.5 source + 0.20 completeness (single unregistered source, aged)
F = 0.5  # share of the constant earned by qualifying at all
PARAMS = {  # trigger: (registry constant C, firing threshold T, saturation M)
    "earnings": (0.22, 5.0, 20.0),
    "price": (0.10, 5.0, 15.0),
    "analyst": (0.08, None, None),  # no magnitude dimension: unchanged
}


def label(score: float) -> str:
    if score >= 0.80:
        return "High"
    if score >= 0.55:
        return "Moderate"
    if score >= 0.35:
        return "Low"
    return "Speculative"


def strength(magnitude, threshold, saturation) -> float:
    if magnitude is None or magnitude <= 0:
        return 0.0
    return max(0.0, min(1.0, math.log(magnitude / threshold) / math.log(saturation / threshold)))


def proposed_contribution(family, magnitude, revenue_surprise=None):
    constant, threshold, saturation = PARAMS[family]
    if threshold is None:
        return constant, 1.0, "no magnitude dimension; registry constant unchanged"
    s = strength(magnitude, threshold, saturation)
    if (
        family == "earnings"
        and magnitude is not None
        and magnitude > saturation
        and (revenue_surprise is None or abs(revenue_surprise) < threshold)
    ):
        return (
            constant * F,
            0.0,
            f"EPS surprise {magnitude:.0f}% with revenue surprise "
            f"{'n/a' if revenue_surprise is None else '%+.1f%%' % revenue_surprise}: "
            "basis unverified, no magnitude share",
        )
    reason = (
        f"magnitude {magnitude:.1f}% vs threshold {threshold:.0f}% "
        f"(saturates at {saturation:.0f}%): strength {s:.2f}"
    )
    return constant * (F + (1 - F) * s), s, reason


def main() -> None:
    provider = json.load(open(sys.argv[1], encoding="utf-8"))
    feed = json.load(open(sys.argv[2], encoding="utf-8"))
    rows = []
    for item in feed["items"]:
        entity, signal = item["entity_id"], item["primary_signal_type"]
        current = item["confidence_score"]
        if signal == "earnings_signal":
            reported = [e for e in provider[entity]["rows"] if e.get("epsActual") is not None][0]
            actual, consensus = reported["epsActual"], reported["epsEstimated"]
            magnitude = (actual - consensus) / abs(consensus) * 100
            rev_a, rev_e = reported.get("revenueActual"), reported.get("revenueEstimated")
            revenue = (rev_a - rev_e) / abs(rev_e) * 100 if rev_a and rev_e else None
            contribution, s, reason = proposed_contribution("earnings", magnitude, revenue)
            evidence = f"EPS {actual} vs consensus {consensus}"
        elif signal == "price_change":
            magnitude = abs(float(re.search(r"(?:up|down) ([\d.]+)%", item["headline"]).group(1)))
            contribution, s, reason = proposed_contribution("price", magnitude)
            evidence = f"price move {magnitude:.2f}%"
        else:
            magnitude = None
            contribution, s, reason = proposed_contribution("analyst", None)
            evidence = "analyst rating change"
        proposed = BASE + contribution
        rows.append(
            {
                "entity": entity,
                "signal": signal,
                "evidence": evidence,
                "magnitude_pct": None if magnitude is None else round(magnitude, 1),
                "current_score": round(current, 3),
                "current_label": label(current),
                "proposed_score": round(proposed, 3),
                "proposed_label": label(proposed),
                "reason": reason,
            }
        )

    rows.sort(key=lambda r: (r["signal"], r["magnitude_pct"] or 0))
    print(f"{'entity':<6} {'signal':<16} {'magnitude':>9}  {'current':>14}  {'proposed':>14}  reason")
    for r in rows:
        mag = "-" if r["magnitude_pct"] is None else f"{r['magnitude_pct']}%"
        print(
            f"{r['entity']:<6} {r['signal']:<16} {mag:>9}  "
            f"{r['current_score']:.3f} {r['current_label']:<8}  "
            f"{r['proposed_score']:.3f} {r['proposed_label']:<8}  {r['reason']}"
        )

    def dist(key):
        return dict(sorted(collections.Counter(r[key] for r in rows).items()))

    summary = {
        "opportunities": len(rows),
        "current_distinct_scores": len({r["current_score"] for r in rows}),
        "proposed_distinct_scores": len({r["proposed_score"] for r in rows}),
        "current_labels": dist("current_label"),
        "proposed_labels": dist("proposed_label"),
        "raised": sum(1 for r in rows if r["proposed_score"] > r["current_score"] + 1e-9),
        "unchanged": sum(1 for r in rows if abs(r["proposed_score"] - r["current_score"]) < 1e-9),
        "lowered": sum(1 for r in rows if r["proposed_score"] < r["current_score"] - 1e-9),
        "max_current": max(r["current_score"] for r in rows),
        "max_proposed": max(r["proposed_score"] for r in rows),
    }

    # Is the spread explained by evidence, or cosmetic?
    earnings = [r for r in rows if r["signal"] == "earnings_signal" and "unverified" not in r["reason"]]
    earnings.sort(key=lambda r: r["magnitude_pct"])
    monotonic = all(a["proposed_score"] <= b["proposed_score"] + 1e-9 for a, b in zip(earnings, earnings[1:]))
    by_magnitude = collections.defaultdict(set)
    for r in earnings:
        by_magnitude[r["magnitude_pct"]].add(r["proposed_score"])
    equal_evidence_equal_score = all(len(scores) == 1 for scores in by_magnitude.values())
    ties = [m for m, _ in collections.Counter(r["magnitude_pct"] for r in earnings).items()
            if sum(1 for r in earnings if r["magnitude_pct"] == m) > 1]
    saturated = [r for r in earnings if r["magnitude_pct"] >= 20]
    checks = {
        "nothing_raised_above_current": summary["raised"] == 0,
        "score_monotonic_in_magnitude": monotonic,
        "equal_magnitude_gives_equal_score": equal_evidence_equal_score,
        "magnitudes_that_tie": ties,
        "saturated_evidence_shares_one_score": len({r["proposed_score"] for r in saturated}) <= 1,
        "score_is_a_function_of_magnitude_only": True,  # no per-entity or rank term exists in the function
    }
    print("\nSUMMARY", json.dumps(summary, indent=1))
    print("CHECKS", json.dumps(checks, indent=1))
    if len(sys.argv) > 3:
        json.dump({"rows": rows, "summary": summary, "checks": checks,
                   "parameters": {"F": F, "by_family": PARAMS, "base": BASE}},
                  open(sys.argv[3], "w", encoding="utf-8", newline="\n"), indent=1)


if __name__ == "__main__":
    main()
