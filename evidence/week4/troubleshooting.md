# Week-4 troubleshooting notes

## 1. The fixed diagnostic is hardcoded to the instructor's namespace

**When:** 2026-11-01 · **Source:** [#94](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/94)

The pinned ACP image's only tool queries `sum by (condition) (kube_pod_status_ready{namespace="quantum-platform"})`; the namespace is a constant, not a setting, and ACP's schema fixes the diagnostic's name. In our cluster that would truthfully return `diagnostic_no_data`. The identical query against `student-platform` returns real data (true=3, false=0, unknown=0). We asked the instructor which fix is approved instead of forking or faking it.

## 2. No approved model endpoint yet

**When:** 2026-11-01 · **Source:** #94

The Hermes worker validates its model ID and base URL at start-up and refuses to run without them. The brief requires the *approved* A100/H200 endpoint and egress to that one host only. We keep the worker at `replicas: 0` rather than point it at an unapproved model.

## 3. A versionlock `--check` run failed before the plugin existed

**When:** 2026-11-01 · **Source:** [#95](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/95)

On edge-01 and api-lb-01 the dnf versionlock plugin wasn't installed yet, so in check mode `dnf versionlock list` and the lock module failed (check mode doesn't really install the plugin). Fix: the read tolerates "No such command" (= no locks yet), and the lock tasks skip only in a first check run without the plugin. The same dry run exposed an older gap: the #87 API-password probes were skipped in check mode; they're read-only, so they now run in `--check` too.

## 4. Three manifests were saved in the wrong encoding

**When:** 2026-11-01 · **Source:** #96

Edits made with Python on Windows used the cp1252 code page, so the `§` in three new YAML comments became byte `0xA7` and yamllint crashed on invalid UTF-8. Caught locally before CI; the files were re-saved as UTF-8 and every tracked file was checked. Lesson: always pass `encoding="utf-8"` when editing repo files from Python on Windows.

## 5. One PR's sealed secrets turn every other PR's secret scan red

**When:** 2026-11-01 · **Source:** #96, #97, #98

gitleaks scans the whole history, including other open branches. #96's two sealed DB-password lines (ciphertext, flagged by key name) are ignored by fingerprint, but those ignore lines exist only on #96's branch, so #97 and #98 fail the scan until #96 merges. Copying the lines into each PR would conflict in `.gitleaksignore`. Fix: merge #96 first, then re-run CI on the others.
