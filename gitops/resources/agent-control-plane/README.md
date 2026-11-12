# Agent Control Plane (Week 4, Phase 1)

Deployed from `nyameko/infra-hpc-qc-k8s` `argocd/resources/agent-control-plane` (the week4 brief says: no fork, pinned upstream images). Display name in the Student Platform: **Crypty**. The records always name the real approved model.

| Changed from upstream | Why |
| --- | --- |
| Images by digest in each manifest (API `sha256:b1289eab…`, Hermes `sha256:609dd6a8…`, PostgreSQL `18.4@sha256:a02db8ca…`) | immutable references; upstream used Kustomize `images:` and the floating `postgres:18` |
| `ACP_TENANT_ID: purple-team1`, Prometheus `kps-prometheus:9090` | our tenant and our kube-prometheus-stack (#68) |
| API ingress only from `student-platform` pods `app=platform` | our Student Platform replaces the Quantum Platform portal |
| Prometheus egress matches `operator.prometheus.io/name=kps-prometheus` | the labels in our cluster |
| Worker starts via `worker-patch.yaml` (diagnostic → `student-platform`) | this cluster has no `quantum-platform` namespace; instructor's answer on #94 |
| Migration hook keeps its last Job (`BeforeHookCreation` only) | team rule: nothing that ran is removed |
| PostgreSQL 10Gi (was 20Gi) | student sizing; retained class, claim never pruned |
| Hermes model route: `ACP_MODEL=qwen2.5-0.5b-instruct`, `ACP_MODEL_BASE_URL` = our LiteLLM (`model-serving`, `/v1`), key sealed as `acp-model`, egress only to LiteLLM :4000 (`acp-model-egress`), `replicas: 1` | #94 resolved 2026-11-09: LiteLLM → llama.cpp on CPU now, A100/vLLM later as a second LiteLLM backend. See `gitops/resources/model-serving/README.md` |

Credentials: owner/app DB passwords and an Ed25519 key pair were generated offline (mirroring upstream `scripts/create_secrets.py`) and sealed with our controller certificate. ACP receives only the **public** key (`acp-verification`); the **private** key is sealed into `student-platform` (`acp-signing`) and is mounted only by the platform backend. Plaintext stays in the captain's private directory, never in Git.

**Diagnostic namespace.** The pinned image's one diagnostic hard-codes `kube_pod_status_ready{namespace="quantum-platform"}`, and this cluster has no such namespace. Per the instructor (#94: "change the namespace to student platform and continue"), the worker starts through a small launcher (`worker-patch.yaml`, mounted read-only) that changes that constant to `student-platform` and the evidence's `namespace` label, then runs the unchanged upstream worker. No rebuilt image; the query stays fixed in Git. The diagnostic ID `quantum-platform-pod-readiness` is the API contract, so it is unchanged, and Hermes' built-in instructions still say "Quantum Platform" (cosmetic). If the image is bumped and its query differs, the launcher refuses to start.

**Hermes and the 64K check.** Hermes refuses models whose context window it resolves below 64K. LiteLLM reports no window, so Hermes falls back to its built-in catalogue (`qwen` → 131,072) and accepts the model, although llama.cpp serves 4,096. That is safe for this worker: one short prompt, no tools, `max_tokens` 1200. An oversize request fails at llama.cpp and the run is recorded as failed; nothing is truncated silently.

Tested before merge with the pinned images only (Hermes worker `609dd6a8…`, our llama.cpp `1c05eb08…`, LiteLLM with the `model-serving` config), on a Docker network without internet, under the cluster DNS names and the pods' UIDs, read-only:

```
Hermes resolved context ...... 131,072 (catalogue match on 'qwen'); the 64K check passes
agent_control_plane.hermes_runtime with a readiness sample (3 true, 1 false) ... exit 0 in 46 s
llama.cpp ................... largest request 760 prompt + 242 completion = 1,001 of 4,096 tokens, truncated = 0
```

The answer is on topic and states the metric's limits, but adds generic advice beyond the evidence; that's the 0.5B model.
