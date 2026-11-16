# Self-range dry-run authorisation (HTTP application-layer SIDs)

**Run:** `20261116T112654Z-w5-phase1-httpsids`
**Type:** Self-range validation of the HTTP application-layer Suricata SIDs (9000012-15).
**This is NOT the graded Week-5 exercise.** It follows up issue #133 / PR #131.
**Authorised by:** team captain / range owner, 2026-11-16.
**Authorised scope:** our own infrastructure only — the traefik web entrypoint
(`k8s-worker-01:30080`) fronting our own `student-platform`. No other team, no external target.

## Why this exists

PR #131's dry-run exercised the host rules and the network scan/burst SIDs but not the HTTP
SIDs. This run sends benign, clearly-marked HTTP requests that match each signature, over
plaintext `http://` so Suricata on edge-01 can parse the URI / User-Agent. It proves live
coverage (or surfaces a gap) before the graded exercise, which stays gated on the instructor
RoE.

## Authorised actions (benign, non-destructive)

Four single HTTP GETs to our own traefik `:30080` with `Host: platform.pt1.internal`, each
carrying a marked attack pattern in the URI or User-Agent:

1. path traversal (`../` and `%2e%2e%2f`) -> SID 9000012 (T1190)
2. SQLi UNION SELECT in the query string -> SID 9000013 (T1190)
3. SQLi tautology (`' OR '1'='1`) -> SID 9000014 (T1190)
4. scanner User-Agent (`sqlmap/...`) -> SID 9000015 (T1595)

No exploitation: the server redirects/handles the request normally; only the request line and
headers (which Suricata inspects on the wire) carry the patterns. No data read/modify/delete,
no DoS, no persistence.

## Reset and replay

Per `docs/week5-runbook.md#reset-and-replay`. Raw captures retained off-repo under
`/var/lib/scc26-evidence/<run-id>/`; only sanitised summaries enter the repository.
