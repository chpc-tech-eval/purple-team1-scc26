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

## 6. The Hermes worker crash-looped: its image was older than the API's

**When:** 2026-11-12 · **Source:** #116, #118

Once #116 scaled the worker to 1, it exited at start-up with `Database migration is required`. The API image (`b1289eab…`, upstream commit `dab5e4c`) had migrated the DB to schema 4 and accepts `{3, 4}`; the worker (`609dd6a8…`) was an earlier build that accepts exactly 3. Upstream had pinned the same mismatched pair once (`infra-hpc-qc-k8s@abe429b`) and replaced both in its next commit; we never noticed because the worker sat at 0 replicas. Fix (#118): the worker GHCR tagged with the same commit as the API (`sha-dab5e4c…` → `73fbc343…`), compared file by file (`worker.py`, `diagnostic.py`, `hermes_runtime.py` identical). Lesson: pin the API and worker from the same upstream commit.

## 7. A StatefulSet won't replace a pod that was never Ready

**When:** 2026-11-12 · **Source:** #118

After #118 merged, Argo was Synced and the StatefulSet named the new image, but the crash-looping pod stayed on the old one. With `podManagementPolicy: OrderedReady`, the controller waits for the current pod to become Ready before replacing it, which a broken pod never does (documented Kubernetes behaviour). Fix: delete that one pod once (`kubectl -n agent-control-plane delete pod agent-control-plane-hermes-0`); its profile PVC is retained. A healthy pod rolls normally, so #119 also adds a pod-template revision annotation, because a ConfigMap change alone doesn't restart the worker.

## 8. Hermes ran `pip install` at runtime and hung with no internet

**When:** 2026-11-12 · **Source:** #119

The first live run collected evidence, then failed as `hermes_timeout` after exactly 180 s; LiteLLM received no request. A stack dump of the pinned Hermes inside the worker pod showed it stuck in `lazy_deps._venv_pip_install`: building its OpenAI client, Hermes imports its Bedrock adapter, which installs boto3 on demand. The NetworkPolicy drops internet traffic silently (a TCP connect from the pod hung 20 s), so pip retried until the budget ran out. The isolated Docker test before #116 missed it: on a Docker `--internal` network outside DNS fails instantly, so pip gave up at once. Fix (#119): the launcher gives the Hermes subprocess `HERMES_DISABLE_LAZY_INSTALLS=1`, Hermes' switch for immutable deployments; measured in the pod: 10.7 s, answer from the model. Lesson: test egress-blocked behaviour with **dropped** packets, not refused ones.

## 9. A GitOps PR merged before the image it points at

**When:** 2026-11-12 · **Source:** #111, #107, #114

#111 (model-serving manifests) merged eight minutes before #107 (the image build), so `dev` carried the image placeholder and the llama.cpp pod sat in `InvalidImageName`. The automatic sync started then was pinned to that revision and retried it, blocking the sync of the fix (#114) until Argo hit its retry limit about seven minutes later. Fix: #114 pinned the published digest. Lesson: say "merge after #N" at the top of a dependent PR and keep it in draft until its input exists.
