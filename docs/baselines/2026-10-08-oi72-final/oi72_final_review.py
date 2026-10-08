"""72-hour Operational Integrity review. Read-only; parses the local sampler
log. Applies the criteria exactly as locked:
  - post-warm-up (first 3 h excluded) RSS slope < 0.02 MB/min
  - final-24h RSS within 15 MB of the first-24h baseline
  - one process, no restart
Usage: py oi72_final_review.py [oi72_log.txt]
Run after the window end for the final verdict; before it, the output is a
status, not a verdict.
"""

import datetime
import json
import re
import statistics
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "oi72_log.txt"
T0 = datetime.datetime(2026, 10, 5, 20, 57, 6)
END = T0 + datetime.timedelta(hours=72)
PID = "652"
SLOPE_LIMIT = 0.02
LEVEL_LIMIT_MB = 15.0

full, every, bad = [], [], []
for line in open(LOG, encoding="utf-8", errors="replace"):
    m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) (full|health)", line)
    if not m:
        continue
    t = datetime.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ")
    if t > END:
        continue
    every.append(t)
    if "health=200" not in line:
        bad.append((m.group(1), line[26:95].strip()))
    r = re.search(r"pid=%s rss_kb=(\d+)" % PID, line)
    u = re.search(r"uptime_s=([\d.]+)", line)
    s = re.search(r"items=(\d+) degraded=(\w+) sem=(\w+)", line)
    if m.group(2) == "full" and r and u:
        full.append((t, int(r.group(1)) / 1024, float(u.group(1)), s.groups() if s else None))


def hours(t):
    return (t - T0).total_seconds() / 3600


def slope(rows):
    xs = [hours(r[0]) * 60 for r in rows]
    ys = [r[1] for r in rows]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def mean(rows):
    return statistics.mean(r[1] for r in rows)


last = full[-1][0]
covered = hours(last)
first24 = [r for r in full if hours(r[0]) < 24]
final24 = [r for r in full if hours(r[0]) >= covered - 24]
post = [r for r in full if hours(r[0]) >= 3]

out = {
    "window": {"start": str(T0), "end": str(END), "last_sample": str(last),
               "hours_covered": round(covered, 1), "complete": covered >= 71.9},
    "samples": {"all": len(every), "with_rss": len(full)},
    "process": {
        "pid": PID,
        "uptime_monotonic": all(b[2] > a[2] for a, b in zip(full, full[1:])),
        "restarted": not all(b[2] > a[2] for a, b in zip(full, full[1:])),
    },
    "memory_mb": {
        "at_start": round(full[0][1], 1),
        "latest": round(full[-1][1], 1),
        "max": round(max(r[1] for r in full), 1),
        "first_24h_baseline_mean": round(mean(first24), 1),
        "final_24h_mean": round(mean(final24), 1),
        "final_24h_max": round(max(r[1] for r in final24), 1),
        "delta_final_vs_first_mean": round(mean(final24) - mean(first24), 1),
        "post_warmup_slope_mb_per_min": round(slope(post), 5),
        "post_warmup_slope_mb_per_day": round(slope(post) * 1440, 1),
        "slope_by_day": {
            "0-24h (after warm-up)": round(slope([r for r in post if hours(r[0]) < 24]), 5),
            "24-48h": round(slope([r for r in full if 24 <= hours(r[0]) < 48]), 5),
            "48h-end": round(slope([r for r in full if hours(r[0]) >= 48]), 5)
            if len([r for r in full if hours(r[0]) >= 48]) > 2 else None,
        },
    },
}

# Market-open steps: mean RSS in the 3 h before 13:30 UTC vs 15:30-18:30 UTC.
steps = {}
for day in (6, 7, 8):
    open_at = datetime.datetime(2026, 10, day, 13, 30)
    before = [r[1] for r in full if open_at - datetime.timedelta(hours=3) <= r[0] < open_at]
    after = [r[1] for r in full
             if open_at + datetime.timedelta(hours=2) <= r[0] < open_at + datetime.timedelta(hours=5)]
    if before and after:
        steps["2026-10-%02d" % day] = {
            "before_open_mean": round(statistics.mean(before), 1),
            "after_open_mean": round(statistics.mean(after), 1),
            "step": round(statistics.mean(after) - statistics.mean(before), 1),
        }
    else:
        steps["2026-10-%02d" % day] = "not yet observable"
out["market_open_steps_mb"] = steps

gaps = [(str(a), str(b), round((b - a).total_seconds() / 60))
        for a, b in zip(every, every[1:]) if (b - a).total_seconds() > 420]
out["health"] = {"non_200_or_unreachable_samples": len(bad), "detail": bad,
                 "sampling_gaps_over_7_min": gaps}

changes, prev = [], None
for r in full:
    if r[3] and r[3] != prev:
        changes.append((str(r[0]), r[3][0], r[3][1], r[3][2]))
        prev = r[3]
out["feed"] = {"item_counts_seen": sorted({r[3][0] for r in full if r[3]}),
               "provider_degraded_seen": sorted({r[3][1] for r in full if r[3]}),
               "fingerprint_changes": changes}

crit = {
    "slope_under_limit": abs(slope(post)) < SLOPE_LIMIT,
    "final_24h_within_15mb_of_first_24h": abs(mean(final24) - mean(first24)) <= LEVEL_LIMIT_MB,
    "single_process_no_restart": not out["process"]["restarted"],
}
out["criteria_as_locked"] = crit
out["status"] = (
    ("PASS on the log-derived criteria" if all(crit.values()) else "FAIL on a log-derived criterion")
    if out["window"]["complete"] else "WINDOW STILL OPEN -- status only, not a verdict"
)
print(json.dumps(out, indent=1))
