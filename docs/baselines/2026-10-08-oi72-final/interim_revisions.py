import json, sqlite3, glob, os
SINCE = "2026-10-05T20:57:06"
out = {}
c = sqlite3.connect("file:/data/opportunity_revisions.db?mode=ro", uri=True)
c.row_factory = sqlite3.Row
rows = [dict(r) for r in c.execute("select entity_id, revision, lifecycle_state, round(confidence_score,4) c, trigger_codes, change_type, created_at from opportunity_revisions where created_at >= ? order by created_at", (SINCE,))]
out["revisions_since_T0"] = rows
c = sqlite3.connect("file:/data/universe_scheduler_state.db?mode=ro", uri=True)
out["scheduler"] = [list(r) for r in c.execute("select * from universe_scheduler_state")]
c = sqlite3.connect("file:/data/universe_membership.db?mode=ro", uri=True)
out["membership_rows"] = c.execute("select count(*) from universe_membership").fetchone()[0]
out["sizes"] = {os.path.basename(p): os.path.getsize(p) for p in sorted(glob.glob("/data/*.db"))}
c = sqlite3.connect("file:/data/universe_operational_observations.db?mode=ro", uri=True)
out["faults_since_T0"] = [list(r) for r in c.execute("select code, count(*) from fault_mirror_observations where occurred_at >= ? group by 1", (SINCE,))]
print(json.dumps(out))
