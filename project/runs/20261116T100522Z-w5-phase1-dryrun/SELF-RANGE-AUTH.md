# Self-range dry-run authorisation

**Run:** `20261116T100522Z-w5-phase1-dryrun`
**Type:** Self-range tooling and detection-rule validation. **This is NOT the graded Week-5 exercise.**
**Authorised by:** team captain / range owner, 2026-11-16.
**Authorised scope:** our own infrastructure only — `edge-01`, `api-lb-01`, `k8s-cp-01`,
`k8s-worker-01`, `k8s-worker-02`, and the `student-platform` service. No other team's range,
no external target, no internet-facing scan.

## Why this exists

The Week-5 runbook step 1 ("Receive and acknowledge the RoE") and `w5run.py`'s
`authorisation.roe_reference` requirement are the hard stop for the **graded** exercise, which
remains gated on the instructor's Rules of Engagement (question raised on the project tracker,
RoE scope issue still open). This record authorises only a **benign, non-destructive rehearsal
on equipment we own**, so the team can prove the detection pipeline and the evidence tooling
work end-to-end before the real exercise. It does **not** substitute for the instructor RoE and
confers no authorisation to touch any other team.

## Authorised actions (all benign, all reversible)

1. A short burst of rejected SSH logins against our own key-only hosts — exercises Wazuh
   `100111` / `100112` (brute-force / key-spray detection, T1110).
2. A TCP port sweep from the workstation across our own VPN range — exercises the Suricata
   team SIDs (network layer).
3. A deliberate break-glass `rocky` login to our own host — exercises Wazuh `100110` (T1078).

No exploitation, no credential theft, no data read/modify/delete, no denial of service, no
persistence, no lateral movement beyond our own hosts.

## Reset and replay

Per `docs/week5-runbook.md#reset-and-replay`. Raw captures are retained off-repo under
`/var/lib/scc26-evidence/<run-id>/`; only sanitised summaries enter the repository.
