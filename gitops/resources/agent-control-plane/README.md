# Agent Control Plane (Week 4, Phase 1)

Deployed from `nyameko/infra-hpc-qc-k8s` `argocd/resources/agent-control-plane` (the week4 brief says: no fork, pinned upstream images). Display name in the Student Platform: **Crypty**. The records always name the real approved model.

| Changed from upstream | Why |
| --- | --- |
| Images by digest in each manifest (API `sha256:b1289eab…`, Hermes `sha256:609dd6a8…`, PostgreSQL `18.4@sha256:a02db8ca…`) | immutable references; upstream used Kustomize `images:` and the floating `postgres:18` |
| `ACP_TENANT_ID: purple-team1`, Prometheus `kps-prometheus:9090` | our tenant and our kube-prometheus-stack (#68) |
| API ingress only from `student-platform` pods `app=platform` | our Student Platform replaces the Quantum Platform portal |
| Prometheus egress matches `operator.prometheus.io/name=kps-prometheus` | the labels in our cluster |
| Migration hook keeps its last Job (`BeforeHookCreation` only) | team rule: nothing that ran is removed |
| PostgreSQL 10Gi (was 20Gi) | student sizing; retained class, claim never pruned |
| Hermes `replicas: 0`, no model route, no model egress | the approved A100/H200 endpoint and its credential aren't known yet (#94) |

Credentials: owner/app DB passwords and an Ed25519 key pair were generated offline (mirroring upstream `scripts/create_secrets.py`) and sealed with our controller certificate. ACP receives only the **public** key (`acp-verification`); the **private** key is sealed into `student-platform` (`acp-signing`) and is mounted only by the platform backend. Plaintext stays in the captain's private directory, never in Git.

The fixed diagnostic in the pinned image queries `namespace="quantum-platform"`; how to point it at `student-platform` is asked in #94.
