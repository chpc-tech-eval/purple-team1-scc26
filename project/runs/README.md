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
