# Week-4 evidence pack

Owners: Phathutshedzo (`saxs-14`), Olerato (`Ole06`) · Ref: [`week4/README.md`](../../week4/README.md) "Week-4 acceptance gate" · Network flows: [#93](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/93) · Instructor questions: [#94](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/94)

An **index**, address-free like Week 3: each row points to sanitised evidence on GitHub. The agent is shown in the Student Platform as **Crypty** (display name only; records always name the real approved model).

Status key: ✅ done (evidence linked) · 🟡 partly done · ⏳ pending (reason given)

## What we deploy, and from where

| Component | Reference | Managed by |
| --- | --- | --- |
| ACP API | `ghcr.io/nyameko/agent-control-plane@sha256:b1289eab…` (instructor's reference, no fork), **live** | Argo `agent-control-plane` ([#96](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/96)) |
| Hermes worker | `ghcr.io/nyameko/agent-control-plane-hermes@sha256:609dd6a8…` | Argo `agent-control-plane` (#96), `replicas: 0` until #94 |
| ACP PostgreSQL | `postgres:18.4@sha256:a02db8ca…`, 10Gi `cinder-agent-retain` (Retain) | Argo `agent-control-plane` (#96) |
| Student Platform (Crypty) | CI image from [#98](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/98), digest pinned in the deploy PR | GitHub Actions → GHCR → Argo |
| Approved model | **not yet known**: logical ID, endpoint class and credential asked in #94 | n/a |

## Acceptance gate (week4 "Week-4 acceptance gate")

| Gate | Proof required | Status | Evidence / blocker |
| --- | --- | --- | --- |
| GitOps | ACP desired state and encrypted secrets reproducible from repo/private inputs | ✅ | Argo `agent-control-plane` **Synced/Healthy** at `7597bcd` in wave order; 3 SealedSecrets decrypted; credentials generated offline from private inputs: [#96 evidence](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/96#issuecomment-6571044436) |
| DB | ACP PostgreSQL PVC/schema ready | ✅ | 10Gi PVC **Bound** on `cinder-agent-retain` (Retain); migration Job **Complete**; `acp1.schema_version` 1–4; `acp_app` not superuser/createrole/createdb/bypassrls: [#96 evidence](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/96#issuecomment-6571044436) |
| API | health + readiness; authenticated task accepted | 🟡 | `/health` **200**, `/ready` **200** (ACP's check proves an RLS-enforcing role and a current schema); no assertion → **401**, foreign-key token → **401**: [#96 evidence](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/96#issuecomment-6571044436). **Pending:** a platform-signed task accepted (after #98 + deploy PR) |
| Worker | singleton Hermes worker healthy with persistent profile | ⏳ | **blocked on #94** (the worker refuses to start without the approved model route) |
| Inference | approved A100/H200 endpoint used remotely | ⏳ | **blocked on #94**; egress to that one host is W4-4 (#93, Olerato) |
| Evidence | fixed diagnostic persists deterministic evidence before explanation | ⏳ | **blocked on #94**: the pinned image queries `namespace="quantum-platform"`; the same query on `student-platform` returns data (3 ready pods), the approved fix is asked in #94 |
| UI | Student Platform displays task/run/evidence/result | 🟡 | `/crypty/` page + server-side signing in #98 (18/18 tests; token accepted by ACP's own PyJWT verification settings). **Pending:** merge + deploy |
| Failure | one safe failure is explicit, not hallucinated as success | ⏳ | planned: model endpoint unavailable via Git config → run `failed` with its code, evidence kept, then revert (week4 §12) |
| Restart | Hermes pod replacement does not erase canonical history | ⏳ | planned: delete only the Hermes pod; history in ACP PostgreSQL; profile PVC retained (week4 §13) |
| Security | no broad cluster/cloud credentials or plaintext secrets exposed | 🟡 | live: **no service-account token** in any ACP pod; other namespaces **can't reach** the API or DB; from the API pod the **Kubernetes API, Internet and platform DB are blocked**; ACP holds only the public key: [#96 evidence](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/96#issuecomment-6571044436). **Pending:** the Hermes worker's checks (#94) |
| PR | accepted Week-4 state merged into `dev` | 🟡 | merged: [#93](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/93), [#95](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/95), [#96](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/96). Open: #97, #98, #99 |

## Done so far (Week-4 carry-forward from Week 3)

| Item | Evidence |
| --- | --- |
| Wazuh manager/agents + Filebeat **version-locked** on all 5 hosts | [#95](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/95): run 2 `changed=0`; per-host `dnf versionlock list`; `dnf update --assumeno` 0 candidates; downgrade refused, and possible only with the lock disabled (control) |
| Suricata pinned + locked, Filebeat release step | [#97](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/97) (open) |

Problems hit so far: [`troubleshooting.md`](troubleshooting.md).
