# Beta 1 release candidate — local package

2026-10-06. Branch `beta1/candidate` (local, unpushed). Production was not touched in building this.

Companion documents in this folder: `CRITICAL_PATH.md`, `DEPLOYMENT_SEQUENCE.md`,
`RUNBOOK_PAUSE_ROLLBACK.md`, `SAFETY_SUPPORT_CARD.md`, `SUCCESS_FAILURE_SCORECARD.md`,
`PARTICIPANT_PACKET.md`, `DEVICE_ACCEPTANCE_SCRIPT.md`. Decisions: ADR-071, 075 to 082.

## 1. What the candidate contains

| Part | Source | State |
|---|---|---|
| Production base | `f105a0a` (Fly v33) | Deployed |
| Decision Ledger | `b10c100` applied cleanly; ADR order resolved | Local |
| Self-corroboration fix, no-percentage copy, shadow qualification | `feat/evidence-strength-presentation` merged | Local |
| Freshness clock | `fix/freshness-fetch-age` merged | Local |
| EPS comparability gate, fail-closed notifications, pause, dispatch states, retention | `091b757` | Local |
| Feedback event, Ask context, telemetry account deletion | `aef231b` | Local |
| Mobile feedback control, trajectory, evidence, Ask revision | `2988550` | Local |
| ADRs 079 to 082, clock-pinned test | `dc70e28` | Local |
| Demo routes closed in live mode, tolerant telemetry loader | `3c5aa57` | Local |

## 2. Evidence-truth transition

**Qualification.** The five governed states and stable reason codes are in
`logan_core/trigger_detection/qualification_shadow.py`. One path is wired: the EPS comparability gate.
Blocked observations emit no trigger, carry no confidence contribution, no magnitude and no materiality,
and unknown never resolves to valid (a test removes each proof field in turn). Price and revenue
qualification remain shadow; a test asserts nothing else imports the module.

**Self-corroboration.** Included unchanged (ADR-076): a same-source update is a revision; only an
independent origin corroborates; signal diversity does not.

**No percentages.** Re-swept on mobile. No user-facing percentage or numeric evidence score remains on
cards, detail, the notification dropdown, accessibility labels, revision text or push text. Two
non-user-facing remnants: `ConfidenceRing.tsx` renders a percentage but is imported nowhere, and
`attentionLayout.ts` builds a percentage string only to estimate label width. Neither is displayed.

**Evidence labels.** Not changed. Every surface now takes its wording from one helper
(`mobile/lib/opportunityPresentation.ts`): "High / Moderate / Low / Speculative evidence". The
quality-condition model is specified, not built:

| Label | Conditions |
|---|---|
| Strongest tier | Qualified; at least one independent-origin corroboration; freshness established; required fields complete; no conflicting evidence |
| Supported (middle) | Qualified; single origin; freshness established; no critical conflict |
| Limited | Qualified, with a defined non-critical limitation: freshness within grace, an optional field missing, or an unresolved minor conflict |
| No label | Blocked observation. It is not an opportunity and receives no evidence-strength label |

No threshold from the current score is carried over and no population percentile is used. Building it
changes the confidence layer's output contract and needs approval; the label names are also undecided.

**Materiality.** Separate from evidence strength and not shown. Price bands exist in shadow and are
unwired; the live price rule (a 5% move) is unchanged. Revenue: none. EPS: none. Analyst:
magnitude-neutral. No logarithmic or floor-based scaling exists anywhere.

**Trajectory.** Verified evidence-based. States are STRENGTHENING, STEADY, WEAKENING, REVERSING, derived
from observed relative performance and volume against the thesis; every reason string describes observed
evidence. The mobile wording is "Evidence strengthening / steady / weakening / reversing", and a test
rejects predictive vocabulary. "New" and "revised" are carried by the lifecycle change type and the
since-you-last-looked panel, not by trajectory.

## 3. EPS beta-safe fallback

With `STRATUS_EPS_COMPARABILITY_GATE` on, no earnings beat, miss or in-line trigger fires unless the
signal proves comparability. The current provider proves none of it, so no EPS-surprise opportunity
fires.

What an earnings release still supports without the comparison:

| Field | Usable | Reason |
|---|---|---|
| That results were released, and when | Yes, as a fact | Provider-supplied date |
| Fiscal quarter | Yes | Provider-supplied |
| Reported EPS as a bare number | **No** | Its basis is not stated; the same field is GAAP for some issuers and adjusted for others |
| Consensus EPS | **No** | Basis not stated |
| Revenue actual | Not available | The provider's field is not mapped, and its definition is unverified |
| Guidance change | Not available | The provider's earnings endpoint carries no guidance |

User-facing behaviour for Beta 1: nothing is shown in place of the comparison. An earnings release with a
blocked comparison does not create an opportunity; the same company still surfaces on a qualifying price
move or analyst action. A neutral "results reported" opportunity would use the first two rows above; it
is a new trigger code and a product decision, and is not built.

## 4. Decision Ledger: what is attributable

| Item | State in the candidate |
|---|---|
| Opportunity ID, revision ID, signal family | Recorded per candidate |
| Model version | Recorded on candidates, feedback and Ask events |
| Qualification outcome | "qualified" plus trigger codes on candidates; blocked observations are logged only |
| Evidence snapshot | Confidence, classification, freshness state, degraded flag, market evidence |
| Provenance | Partial: source time is recorded; provider and endpoint per evidence item are not |
| External event time, detected time, created time | Source-captured time and candidate time recorded; first-detected time is in lifecycle state |
| Freshness / degraded state | Recorded per candidate |
| Candidacy, SEND / SUPPRESS, reason | Recorded; twelve suppression reasons, one send reason |
| Dispatch attempt and outcome | Recorded: attempted, accepted, rejected, failed |
| Delivery | Recorded as unknown; never claimed |
| Exposure, open, detail view, return | Existing telemetry |
| Watch / unwatch | Existing telemetry and store |
| Ask with selected opportunity | Opportunity ID was already sent; company and revision added |
| Feedback | New event with displayed context |

Correction to the 2026-10-05 audit: Ask events were already carrying the opportunity ID. The gap was the
durable key (company and revision), which is now added.

## 5. Audits

**Watch.** Writes persist and survive a restart; duplicate create and remove are idempotent; one user's
Watch never appears for another; the feed reflects it; a degraded provider does not remove it; account
deletion purges it (18 existing tests). Watch state does not reach trigger detection, evidence trust,
conclusion confidence, the world model, normalization, receptors or lifecycle classification (new
structural test). Telemetry records create and remove. No beta blocker found.

**Notifications.** Places where uncertainty could become SEND, and their disposition:

| Finding | Disposition |
|---|---|
| An alert-level item with no lifecycle revision was sent on prioritisation alone | Suppressed in live mode |
| Freshness was never consulted | Unestablished or stale freshness suppresses |
| A push was recorded as sent whenever the HTTP call returned, whatever the response | Response is read; failed and rejected are never recorded as notified |
| Nothing could stop pushes short of a deploy | Pause switch |
| A model change can produce notification-worthy revisions | **Not prevented in code.** Procedure: deploy with the pause on. A code guard needs a schema change |

Confirmed unchanged: revision de-duplication and cooldown are deterministic and durable; a degraded
provider suppresses; push text contains no confidence percentage and, with the EPS gate on, no beat / miss claim.

**Beta-surface sweep.**

| Finding | Disposition |
|---|---|
| `/v1/briefing` and `/v1/demo/tesla` served static or simulated data from production | Fixed: 404 in live mode |
| Account deletion did not remove telemetry | Fixed |
| A telemetry row from another build could stop the store loading | Fixed: skipped, not fatal |
| A user-model test depended on the wall clock and had started failing | Fixed in the test |
| `/v1/dev/*` routes are unauthenticated aggregate reports | Recorded. Existing posture; a decision before any wider release |
| Opportunity `event_id` changes on restart | Recorded. Company plus revision is the durable key and is now on feedback and Ask events |
| Telemetry in-memory index and store have no bound | Post-beta |
| Unused percentage ring component; legacy diagnostic screens | Post-beta; not reachable in a production build |

## 6. News and catalysts

Not built. No investigation was started beyond what is already recorded. The SEC 8-K path remains the one
candidate that is structured, attributable and timestamped. It is not on the critical path; it becomes
relevant only if the feed is judged too thin with the EPS gate on.

## 7. Verification

| Suite | Result |
|---|---|
| `logan_core` + `backend` (pytest) | 1,779 passed, 1 expected failure, 0 failed (production base: 1,458 passed, 1 failed) |
| Mobile (jest) | 36 suites, 260 tests, all pass |
| Mobile type-check and lint | Clean |
| Ruff | Clean |
| Black | One file would be reformatted: `notification_ledger_report.py`, as it arrived in `b10c100` |
| mypy, application code | Clean |
| mypy, test files | 53 errors in 7 test files; present before this work |

Expected failure: one (`xfail`, strict), from the self-corroboration change, documented in ADR-076.

## 8. What was not done

- Nothing was run on a device.
- The pause and rollback were not rehearsed.
- The quality-condition labels, a supporting-signals list on the detail view, a neutral earnings fact,
  and a code guard against recalibration pushes were specified or described, not built.
- WHAT CHANGED and WHY IT MATTERS NOW text is generated server-side by the Presentation layer and was
  not rewritten; only what the detail shows and omits was changed.
