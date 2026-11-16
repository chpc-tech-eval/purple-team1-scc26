# Week-5 self-range dry-run — HTTP application-layer SIDs (9000012-15)

**Run:** `20261116T112654Z-w5-phase1-httpsids` · **Role:** defender · **Date:** 2026-11-16
**Type:** self-range rehearsal on our own infrastructure. **Not the graded exercise.**
Follows up issue #133. Authorisation and scope: [`SELF-RANGE-AUTH.md`](SELF-RANGE-AUTH.md).

## Purpose

PR #131's dry-run validated the host rules and the network scan/burst SIDs but not the HTTP
application-layer SIDs. This run sends benign, marked HTTP requests matching each signature to
our own `student-platform` (via the traefik web entrypoint `k8s-worker-01:30080`, plaintext
`http://` so Suricata can parse the URI / User-Agent) and confirms live coverage.

## Result — all four HTTP SIDs fire live

| UTC (Z) | Layer | Rule / SID | Caught |
| --- | --- | --- | --- |
| 11:44:50 | network | Suricata **9000012** | HTTP path traversal (T1190) |
| 11:44:51 | network | Suricata **9000013** | SQLi UNION SELECT (T1190) |
| 11:44:52 | network | Suricata **9000014** | SQLi tautology (T1190) |
| 11:44:54 | network | Suricata **9000015** | web scanner User-Agent (T1595) |
| 11:44:50 | host | Wazuh **100101** (L12) | repeated network detections from one source, correlated |
| (each)  | host | Wazuh **100100** | every Suricata SID escalated into Wazuh |

Baseline (10.2 min) carried only ambient ET DNS alerts — no team SID — so the scenario signal
is cleanly separable. Manifest validates at **plan and final**. Metrics: time-to-detect 7 s,
time-to-identify 0 s (the correlation fired with the first detection), **0 false negatives**.

Suricata inspects HTTP on the NodePort (`:30080`), not only port 80 — confirmed live.

## Measurement lesson (recorded as a gap)

Suricata stamps each alert with the **flow-start** time, ~2-3 s before the HTTP transaction.
A first, un-padded attempt put the traversal alert in the baseline window and the UNION alert
in the 2 s dead-zone between `baseline.end` and `window.start`, so two SIDs looked like misses.
Re-running with a >=10 s pad after `window.start` (and no gap at the boundary) captured all
four. **The Week-5 runbook's window guidance should require this padding** so the graded
exercise does not lose early detections at a window edge.

## Evidence integrity

Raw captures stay on the hosts (`/var/lib/scc26-evidence/<run-id>/`, never committed). The repo
holds only sanitised `summary.json` / `timeline.csv` (logical names / `<addr>`), SHA-256 of each
raw file, the incident timeline, metrics, and figures (`paper/figures/week5-httpsids/`). The
Prometheus export (`prom_export.sh`, fixed under PR #134 / issue #132) ran cleanly here — all
five queries returned series.

Reset/replay per `docs/week5-runbook.md#reset-and-replay`.
