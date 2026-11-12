# Week-5 runbook: controlled security exercise, detection and forensics

The replayable procedure for [`week5/README.md`](../week5/README.md). It contains no secret scenario content: the instructor's Rules of Engagement (RoE) and scenario stay out of Git until disclosure is authorised. Wherever this runbook says *scenario step*, the RoE decides what is allowed.

**Hard stops.** No exercise without an acknowledged RoE. Only the authorised sources and targets. No production, public or other-team targets. No destructive payloads, no uncontrolled persistence. Hermes/Crypty stays read/report-only. Evidence is never deleted or overwritten (team rule).

## Tools

| Tool | Runs on | Purpose |
| --- | --- | --- |
| [`project/tools/w5_ready.sh`](../project/tools/w5_ready.sh) | laptop (VPN) | read-only readiness check before a run: NTP sync and clock offset on every evidence host, Wazuh agents, Suricata logging with all team SIDs loaded, `/root/hostmap.csv` present, Argo CD Synced/Healthy; prints `time_sync.max_skew_seconds` |
| [`project/tools/w5run.py`](../project/tools/w5run.py) | laptop/CI | `validate` a run manifest (`--stage plan` before, `--stage final` after), `metrics` (T_detect/T_identify/T_contain/T_recover), `timeline` (merge evidence CSVs into one incident timeline) |
| [`project/tools/edge_export.sh`](../project/tools/edge_export.sh) | edge-01 (sudo) | bounded Suricata + Wazuh export for one window; raw copy stays on the server, Git gets `summary.json`, `timeline.csv`, `SHA256SUMS` with addresses replaced |
| [`project/tools/prom_export.sh`](../project/tools/prom_export.sh) | k8s-cp-01 | bounded Prometheus export (fixed queries, aggregated by namespace) |
| [`project/runs/_template/manifest.yaml`](../project/runs/_template/manifest.yaml) | Git | the run manifest the brief requires |
| [`project/tools/w5figures.py`](../project/tools/w5figures.py) | laptop/CI | paper/poster figures (timeline swim-lanes, phase bars) and metrics tables (LaTeX/Markdown) |

Tests: `python3 -m unittest discover -s project/tools -v`.

## 1. Receive and acknowledge the RoE

- Read the RoE. Record **where** it was acknowledged (issue/message ID) in `authorisation.roe_reference` and the UTC time in `authorisation.acknowledged_utc`. Never paste its content.
- Write the authorised sources and targets as logical names (`scope.sources`, `scope.targets`). Addresses go only into the private host map used by `edge_export.sh` (`/root/hostmap.csv` on edge-01, `address,logical-name` per line).

## 2. Freeze the accepted Week-4 state

```bash
# RUN ON: laptop (repo)
git fetch origin && git rev-parse origin/dev            # -> frozen.git_sha
```

```bash
# RUN ON: k8s-cp-01
kubectl -n argocd get applications -o custom-columns=APP:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,REV:.status.sync.revision
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{" "}{.status.containerStatuses[*].imageID}{"\n"}{end}' \
  | grep -E '^(student-platform|agent-control-plane|wazuh) ' | sort -u                     # -> frozen.images
```

Every Argo CD application must be `Synced/Healthy` at the frozen revision. No merges to `dev` during the run window.

## 3. Verify time synchronisation

One command checks every host at once (and the sensors and Argo CD from steps 2 and 4). Paste its output into the run log:

```bash
# RUN ON: laptop (repo, VPN up)
bash project/tools/w5_ready.sh          # must end in READY; copy time_sync.max_skew_seconds into the manifest
```

By hand, per host:

```bash
# RUN ON: every evidence host (edge-01, k8s-cp-01, k8s-worker-01/02, api-lb-01)
chronyc tracking | grep -E 'Reference ID|System time|Leap status'
timedatectl show -p NTPSynchronized --value          # must be "yes"
```

Record the largest offset in `time_sync.max_skew_seconds` (the validator refuses more than 1 s). Wazuh, Suricata and Prometheus all write UTC; the exports normalise every timestamp to `...Z`.

## 4. Baseline: 10–15 minutes of normal telemetry

Do nothing unusual for 10–15 minutes, then export that window:

```bash
# RUN ON: edge-01
sudo bash edge_export.sh <run-id> baseline <baseline_start> <baseline_end> /root/hostmap.csv
# RUN ON: k8s-cp-01
bash prom_export.sh <run-id> baseline <baseline_start> <baseline_end>
```

The baseline's alert signatures and rules are the reference for false positives: anything that also fires in the baseline isn't scenario evidence by itself.

## 5. Manifest and start time

```bash
mkdir -p project/runs/<run-id> && cp project/runs/_template/manifest.yaml project/runs/<run-id>/manifest.yaml
# fill it in, then:
python3 project/tools/w5run.py validate project/runs/<run-id>/manifest.yaml --stage plan
```

Do not start until `--stage plan` prints `OK`. Note the UTC start (`window.start_utc`).

## 6–7. Execute the approved scenario; record detections

- **Attacker phase:** run only the RoE scenario steps from the authorised source. Log each step's UTC time in a private operator log (it becomes timeline rows after disclosure is authorised).
- **Defender phase:** watch the Wazuh dashboard (alerts), `eve.json` and Grafana. Record the first observable (`milestones.first_detection_utc`), each detection (`detections[]`: UTC, source, rule ID, evidence ID, analyst) and when the correct interpretation was reached (`milestones.identified_utc`). Containment/recovery only if the RoE exercises them.

## 8. Export and retain evidence

```bash
# RUN ON: edge-01
sudo bash edge_export.sh <run-id> scenario <window_start> <window_end> /root/hostmap.csv
# RUN ON: k8s-cp-01
bash prom_export.sh <run-id> scenario <window_start> <window_end>
```

Copy only `summary.json`, `timeline.csv` and `SHA256SUMS` into `project/runs/<run-id>/`. List each retained file in `evidence[]` with its SHA-256 (from `SHA256SUMS`).

## 9. One incident timeline

Add operator/analyst rows (same header: `utc,source,layer,evidence_id,summary`) in `project/runs/<run-id>/analyst.csv`, then:

```bash
python3 project/tools/w5run.py timeline project/runs/<run-id>/timeline.csv project/runs/<run-id>/analyst.csv \
  -o project/runs/<run-id>/incident-timeline.csv --md project/runs/<run-id>/incident-timeline.md
```

The merge refuses rows without an evidence ID and any real address.

## 10–11. ACP/Hermes explanation, human review

Give Crypty curated evidence only (evidence IDs from the manifest), never shell or Kubernetes access. Record each `task_id`, the evidence IDs it was given, and in `acp[].human_review` what the analyst checked and corrected.

> **Current limit:** Crypty works end to end since Week 4: Student Platform → ACP → Hermes → LiteLLM → `qwen2.5-0.5b-instruct`, with restart and worker security checks ([Week-4 evidence](../evidence/week4/README.md)). But ACP Phase 1 accepts only the fixed `quantum-platform-pod-readiness` diagnostic (pointed at `student-platform`), so **curated incident evidence cannot be submitted yet**. Until the instructor answers how it may be (#103, question 5), step 10 is recorded as an evidence gap in `findings.gaps`, never simulated.
>
> What Crypty *can* add now is operational context: a pod-readiness run during the window shows whether the Student Platform stayed healthy. If you use it, record it in `acp[]` like any other task (its `task_id`, the evidence it stored, and the analyst's `human_review`), and say in the review that it is platform health, not an explanation of the incident. The 0.5B model can misread its own evidence (Week-4 run `61898af2`), so check every sentence against the stored counts.

## 12. Findings

Record false positives (fired, not scenario), false negatives (scenario step, no alert) and evidence gaps in `findings`. A run without detections is valid only if the misses are recorded.

```bash
python3 project/tools/w5run.py validate project/runs/<run-id>/manifest.yaml --stage final
python3 project/tools/w5run.py metrics  project/runs/<run-id>/manifest.yaml -o project/runs/<run-id>/metrics.json
```

## Figures and tables for the paper and poster

```bash
pip install pyyaml==6.0.3 matplotlib==3.10.7
python3 project/tools/w5figures.py project/runs/<run-a> project/runs/<run-b> -o paper/figures/week5
```

This writes one incident-timeline swim-lane per run (`timeline-<run-id>.pdf/.png`), a detect/identify/contain/recover bar per run (`phases.pdf/.png`), and the same numbers as `metrics.tex` (booktabs, `\input` it in `paper/main.tex`) and `metrics.md`. A milestone that wasn't reached shows as "not reached", never as zero. Preview with the synthetic example: `project/tools/testdata/example-run`.

## Testing a detection rule

Each scenario needs at least one tested detection.

```bash
# RUN ON: edge-01. Wazuh rule against a sample log line (no live traffic needed)
sudo /var/ossec/bin/wazuh-logtest            # paste the line; expect the rule ID and level
# Suricata rule syntax and a replay against a captured pcap (offline)
sudo suricata -T -c /etc/suricata/suricata.yaml -S /etc/suricata/rules/local.rules
sudo suricata -r <capture.pcap> -c /etc/suricata/suricata.yaml -S /etc/suricata/rules/local.rules -l /tmp/suri-replay
```

New rules go through Ansible (roles `suricata` / `wazuh_manager`) in a PR, never edited by hand on the host.

## Reset and replay

1. **Reset:** confirm every Argo CD application is `Synced/Healthy` at `frozen.git_sha`; `agent_control -l` shows all agents active; `systemctl is-active suricata wazuh-manager filebeat` all active; the platform health endpoint returns 200. Any changes the scenario made are reverted through Git/Ansible, never by deleting evidence.
2. **Replay:** a new manifest (new `run_id`, same `scenario_id` and scope, `phase` unchanged), a fresh baseline, then steps 6–12 with export label `replay`. Compare detections and metrics with the original run.
3. **Swap roles** (brief step 14) only after the instructor approves the second phase: new manifest with the other `team_role` and `phase: 2`.

## Exit gate

Another authorised student or mentor can follow this runbook and the run directory (manifest, timeline, metrics, evidence hashes) and reconstruct what happened without a verbal explanation.
