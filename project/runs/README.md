# Week-5 exercise runs

One directory per run: `project/runs/<run-id>/`, where `<run-id>` is `<UTC start>-w5-<phase>` (for example `20261110T090000Z-w5-phase1-defend`). Procedure: [`docs/week5-runbook.md`](../../docs/week5-runbook.md).

| File | Written by | Notes |
| --- | --- | --- |
| `manifest.yaml` | analyst, from [`_template/manifest.yaml`](_template/manifest.yaml) | validated with `w5run.py validate --stage plan` before the run, `--stage final` after |
| `timeline.csv`, `summary.json`, `SHA256SUMS` | `edge_export.sh` | sanitised: addresses replaced; the raw copy stays on edge-01 |
| `analyst.csv` | analyst | operator and analyst timestamps, same header as `timeline.csv` |
| `incident-timeline.csv` / `.md` | `w5run.py timeline` | the single incident timeline |
| `metrics.json` | `w5run.py metrics` | T_detect, T_identify, T_contain, T_recover; `null` = not reached, never imputed |

Rules: logical names only, no addresses (the RFC 5737 ranges are the only exception) and no secret scenario text until the instructor authorises disclosure. Runs are never deleted; a failed or missed detection is a result.

## Evidence pack (one run)

```
project/runs/
├── README.md
├── _template/manifest.yaml           # copy this, never edit it for a run
├── <run-id>/                         # e.g. 20261110T090000Z-w5-phase1-defend
│   ├── manifest.yaml                 # 1. before the run (validate --stage plan)
│   ├── timeline.csv                  # 2. edge_export.sh (sanitised)
│   ├── summary.json                  #    edge_export.sh
│   ├── SHA256SUMS                    #    edge_export.sh; every file above is listed in manifest evidence[]
│   ├── analyst.csv                   # 3. operator/analyst rows: utc,source,layer,evidence_id,summary
│   ├── incident-timeline.csv / .md   # 4. w5run.py timeline
│   └── metrics.json                  # 5. w5run.py metrics (after validate --stage final)
└── recertification/                  # access recertification records (docs/access-control-policy.md)
    └── <YYYY-MM-DD>-pass<N>.md
```

Checklist per run (commands in [`docs/week5-runbook.md`](../../docs/week5-runbook.md)):

1. `mkdir project/runs/<run-id>` and copy `_template/manifest.yaml`; fill scope, frozen SHA/images, time sync and baseline; `w5run.py validate --stage plan`.
2. After the window, export with `edge_export.sh`; copy only `timeline.csv`, `summary.json`, `SHA256SUMS`; add each to `evidence[]` with its SHA-256.
3. Write `analyst.csv`, then `w5run.py timeline` → `incident-timeline.csv/.md`.
4. Fill `milestones`, `detections`, `findings`; `w5run.py validate --stage final`; `w5run.py metrics` → `metrics.json`.
5. `project/tools/w5paper.sh` regenerates `paper/figures/week5/` (metrics table + phase and timeline figures) from every committed run; `paper/main.tex` includes them. Commit the run directory and the regenerated figures together.

Preview without a real run (synthetic data, do not commit the output):
`python3 project/tools/w5figures.py project/tools/testdata/example-run -o /tmp/w5preview`

## Access recertification records

[`docs/access-control-policy.md`](../../docs/access-control-policy.md) asks for each recertification pass to be recorded (date, who, result) here. Same rules as runs: no addresses, no key material (short public fingerprints at most), findings fixed through Git/Ansible.
