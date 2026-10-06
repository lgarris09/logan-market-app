"""Read-only replay: what the feed would contain with the EPS gate on.
Sources: production snapshots taken 2026-10-05 and the feed captured at T0."""
import collections
import json
import sqlite3

SNAP = "prod_snapshot/"
FEED = "C:/Projects/stratus-worktrees/oi72/opps_at_T0.json"
EPS = {"STOCK_EARNINGS_BEAT", "STOCK_EARNINGS_MISS", "STOCK_EARNINGS_IN_LINE"}


def ro(name):
    c = sqlite3.connect("file:%s%s?mode=ro" % (SNAP, name), uri=True)
    c.row_factory = sqlite3.Row
    return c


def codes(text):
    try:
        v = json.loads(text)
        return list(v) if isinstance(v, list) else []
    except Exception:
        return [x for x in (text or "").split(",") if x]


out = {}
feed = json.load(open(FEED, encoding="utf-8"))["items"]
feed_entities = [i["entity_id"] for i in feed]
out["feed_at_T0"] = {
    "items": len(feed),
    "by_signal_type": dict(collections.Counter(i["signal_type"] for i in feed)),
    "by_lifecycle_state": dict(collections.Counter(i["lifecycle_state"] for i in feed)),
    "by_trajectory": dict(collections.Counter(i["trajectory"] for i in feed)),
    "by_freshness": dict(collections.Counter(i["freshness_state"] for i in feed)),
    "unique_entities": len(set(feed_entities)),
}

c = ro("lifecycle_state.db")
snaps = {r["entity_id"]: dict(r) for r in c.execute("select * from lifecycle_snapshots")}
out["lifecycle_snapshots"] = len(snaps)
per = {}
for e, r in snaps.items():
    cs = codes(r["trigger_codes"])
    per[e] = {"codes": cs, "state": r["lifecycle_state"], "non_eps": [x for x in cs if x not in EPS]}
out["snapshot_code_combinations"] = dict(
    collections.Counter(",".join(sorted(v["codes"])) for v in per.values())
)
surviving = {e: v for e, v in per.items() if v["non_eps"]}
out["entities_with_a_non_eps_trigger"] = {e: v["non_eps"] for e, v in surviving.items()}
in_feed = [e for e in feed_entities if e in per]
out["feed_entities_matched_to_snapshot"] = len(in_feed)
out["feed_items_surviving_gate"] = sorted(e for e in feed_entities if e in surviving)
out["feed_items_removed_by_gate"] = len([e for e in feed_entities if e in per and e not in surviving])
out["feed_entities_not_in_snapshot"] = sorted(e for e in feed_entities if e not in per)

c = ro("opportunity_revisions.db")
rows = [dict(r) for r in c.execute("select * from opportunity_revisions order by created_at")]
out["revisions_total"] = len(rows)
out["revisions_span"] = [rows[0]["created_at"][:10], rows[-1]["created_at"][:10]] if rows else None
fam = collections.Counter()
non_eps_days = collections.defaultdict(set)
non_eps_entities = set()
change = collections.Counter()
for r in rows:
    cs = codes(r["trigger_codes"])
    key = ",".join(sorted(cs))
    fam[key] += 1
    ne = [x for x in cs if x not in EPS]
    if ne:
        non_eps_days[r["created_at"][:10]].add(r["entity_id"])
        non_eps_entities.add(r["entity_id"])
        change[r["change_type"]] += 1
out["revisions_by_code_combination"] = dict(fam)
out["revisions_with_non_eps_trigger"] = sum(v for k, v in fam.items() if any(x not in EPS for x in k.split(",") if x))
out["entities_ever_with_non_eps_trigger"] = sorted(non_eps_entities)
out["days_with_any_non_eps_revision"] = len(non_eps_days)
out["non_eps_revision_change_types"] = dict(change)
out["non_eps_entities_per_day"] = {d: sorted(v) for d, v in sorted(non_eps_days.items())}

c = ro("universe_daily_telemetry.db")
days = []
for r in c.execute("select date, observation_count, raw_qualified_observation_count, signal_family_impression_counts from universe_daily_telemetry order by date"):
    try:
        f = json.loads(r["signal_family_impression_counts"] or "{}")
    except Exception:
        f = {}
    days.append((r["date"], r["observation_count"], f))
tot = collections.Counter()
for _, _, f in days:
    for k, v in f.items():
        tot[k] += v
out["telemetry_days"] = len(days)
out["impressions_by_family_all_days"] = dict(tot)
out["impressions_by_family_last_7_days"] = {d: f for d, _, f in days[-7:]}

c = ro("universe_operational_observations.db")
out["signal_family_attempts"] = [
    dict(r)
    for r in c.execute(
        "select signal_family, count(*) n, sum(qualified) qualified, min(occurred_at) first, max(occurred_at) last "
        "from signal_family_attempt_observations group by 1"
    )
]
print(json.dumps(out, indent=1, default=str))
