# Week-5 self-range dry-run — detection pipeline and evidence tooling

**Run:** `20261116T100522Z-w5-phase1-dryrun` · **Role:** defender · **Date:** 2026-11-16
**Type:** self-range rehearsal on our own infrastructure. **Not the graded exercise.**
Authorisation and scope: [`SELF-RANGE-AUTH.md`](SELF-RANGE-AUTH.md).

## Purpose

Prove, end to end and on equipment we own, that (a) the Week-5 detection rules fire on the
traffic they are meant to catch, (b) a clean baseline is separable from the scenario, and
(c) the evidence / timeline / metrics tooling produces repository-safe artefacts — before the
instructor's graded exercise (still gated on the Rules of Engagement).

## What ran

Frozen state: `dev` @ `bdb61cc`, 14/14 Argo apps Synced + Healthy, workload image digests
pinned in the manifest. Clocks NTP-synced across all 5 hosts (max skew < 0.001 s).

- **Baseline** 10:08:41–10:19:18Z (10m37s): normal telemetry, no injected activity.
- **Scenario** 10:21:07–10:23:04Z, three benign actions from `self-range-host` at our own
  `api-lb-01`:
  1. break-glass `rocky` login,
  2. TCP SYN sweep across 60 ports,
  3. 12 rejected SSH logins (unauthorised key) in ~20 s.

## Result — every targeted detection fired

| UTC (Z) | Layer | Rule / SID | What it caught |
| --- | --- | --- | --- |
| 10:21:07 | network | Suricata **9000010** | TCP SYN sweep (T1046) |
| 10:21:07 | host | Wazuh **100110** (L12) | break-glass `rocky` login (T1078) |
| 10:21:07 | host | Wazuh **100100** | SYN-scan alert escalated into Wazuh |
| 10:21:15 | network | Suricata **9000011** | SSH connection burst (T1110) |
| 10:21:24 | host | Wazuh **100112** (L10) | 8+ rejected logins correlated as brute force |
| (×11)   | host | Wazuh **100111** | each rejected login (11 of 12 attempts) |

**Metrics** (`metrics.json`): time-to-detect ≈ **0 s**, time-to-identify = **17 s**
(brute-force correlation); containment / recovery not exercised. 5 headline detections,
2 false positives, 1 false negative, 2 evidence gaps.

## Honest findings

**False positives / noise**
- 54× `ET INFO Server Responded with Vulnerable OpenSSH Version (CVE-2024-6409)`
  (Suricata 2054407 / Wazuh 86601): informational, raised by our own SSH handshakes exposing
  the sshd version banner. Benign, but a real exposure to track and suppress or patch.
- Baseline carried 9 ambient `ET TA_ABUSED_SERVICES` DNS alerts (lovable.app/.dev) from
  in-cluster name resolution. No team SID or host rule fired in the baseline, so the scenario
  signal is cleanly separable.

**False negative**
- `100111` fired on 11 of 12 rejected attempts (one not individually decoded to sshd event
  5722). The `100112` correlation still fired — the brute force was not missed.

**Gaps**
- `prom_export.sh` failed (exec's `wget` inside a pod that has none); Prometheus operational
  context not captured. Fix: use `curl`, or reach in-cluster Prometheus without a pod exec.
- HTTP application-layer SIDs (9000012 traversal, 9000013/9000014 SQLi, 9000015 scanner UA)
  were not exercised; validate them against `student-platform` in a follow-up.

## Evidence integrity

Raw captures stay on the hosts (`/var/lib/scc26-evidence/<run-id>/`, never committed). The
repository holds only sanitised `summary.json` / `timeline.csv` with addresses replaced by
logical names, plus SHA-256 of each raw file:

- baseline: suricata `13df51dd…`, wazuh `7de1f29a…`
- scenario: suricata `c143d7ca…`, wazuh `c2facf7b…`

Reset/replay per `docs/week5-runbook.md#reset-and-replay`.
