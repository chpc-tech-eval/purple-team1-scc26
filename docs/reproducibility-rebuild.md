# Reproducibility: clean rebuild and result replay

How to rebuild the platform from this repository plus the private inputs, and confirm
that the headline security result reproduces. This is the Week-6/7 reproducibility
deliverable; it collects pointers that already live in the repo rather than restating
them. Companion docs: [`EXPERIMENT-PROVENANCE.md`](EXPERIMENT-PROVENANCE.md) (the
provenance contract), [`COMMAND-LOCATIONS.md`](COMMAND-LOCATIONS.md) (where each command
runs), [`week5-runbook.md`](week5-runbook.md) (the security-run procedure), and
[`../project/runs/README.md`](../project/runs/README.md) (the run-directory layout).

**Address-free rule.** Nothing in this doc, or anywhere in the public repo, contains real
CIDRs, fixed IPs, the floating IP, or SSH sources. Those live only in the private inputs
below. Use logical and Terraform-variable names.

## 1. Inputs

| Input | Where it comes from | Never in Git? |
| --- | --- | --- |
| This repository | `chpc-tech-eval/purple-team1-scc26` at a pinned commit | public |
| `terraform.tfvars` | private workstation of whoever applies (the real CIDRs/IPs) | yes |
| Private Ansible inventory | private (host addresses, Wazuh agent/API CIDRs, revoked keys) | yes |
| Sealing key for secrets | lives only in the cluster; `kubeseal` uses the public cert | yes |
| WireGuard config | per-member `wg0.conf` (private) | yes |

The repository is the durable experimental record; the private inputs are the
environment-specific values the repo deliberately keeps out of version control.

## 2. Rebuild sequence

Run each command on the host named in [`COMMAND-LOCATIONS.md`](COMMAND-LOCATIONS.md).
`kubectl`/Argo commands run **only** on `k8s-cp-01`, never on a workstation.

1. **Infrastructure (Week 1).** From the workstation, `terraform plan` then `apply`
   the five-node range (networks, router + static route, security groups, floating IP
   on `edge-01` only). Verify with the checks in the Week-1 evidence (`openstack network
   list`, `router show`, `floating ip list`, security-group rule list).
2. **Host configuration (Week 1–3).** Run the Ansible roles over the private inventory:
   edge services (WireGuard, Pi-hole DNS, nftables), host hardening, then the
   observability agents (Wazuh) and the Suricata IDS with the committed rule set.
3. **Kubernetes (Week 2).** Bring up the cluster (Kubernetes 1.36.4, Cilium 1.20.1),
   HAProxy in front of the API, and Cinder storage. Confirm node/Cilium health and the
   connectivity suite.
4. **GitOps (Week 2+).** Point Argo CD at this repo's `gitops/` path; it reconciles the
   declared state. Unseal secrets with `kubeseal` against the cluster's public cert.
   Wait for every Argo application to report **Synced/Healthy**.
5. **Platform + observability (Week 3).** The student platform (UI/API/PostgreSQL),
   Prometheus/Grafana, and the Wazuh manager come up under Argo. Confirm the detection
   rules load (Suricata rules parsed; Wazuh `analysisd` validates the custom rules).
6. **Agent control plane (Week 4).** Argo brings up the ACP API, the singleton Hermes
   worker, the ACP PostgreSQL (retain), and `model-serving` (LiteLLM -> llama.cpp). The
   acceptance gates are in [`../evidence/week4/README.md`](../evidence/week4/README.md).

Each stage's commit, image digests and verification evidence are recorded in the matching
`evidence/weekN/` pack and run manifests, so a rebuild can be checked stage by stage.

## 3. Replay the headline result

The key result is: *the deployed detection rules fire end-to-end and correlate host and
network evidence on a single timeline.* To reproduce it on the rebuilt range, run a
Week-5 self-range exercise exactly as [`week5-runbook.md`](week5-runbook.md) describes
(authorised per the run's `SELF-RANGE-AUTH.md` — self-range only, never another team):

1. **Freeze + baseline.** Confirm the pinned commit, Argo Synced/Healthy, and clock skew
   within one second; capture a 10–15 min baseline of ambient traffic.
2. **Scenario.** Issue the benign, pre-declared marked actions from the range host against
   the team's own platform.
3. **Export evidence.** Run the export tooling on the sensor hosts; it keeps raw captures
   on the hosts and writes sanitised `summary.json`/`timeline.csv` + `SHA256SUMS` into the
   run directory.
4. **Validate + metrics + figures.**
   ```sh
   python3 project/tools/w5run.py validate project/runs/<run-id>/manifest.yaml --stage final
   python3 project/tools/w5run.py metrics  project/runs/<run-id>/manifest.yaml -o project/runs/<run-id>/metrics.json
   project/tools/w5paper.sh    # regenerates paper/figures/week5/ from every run directory
   ```
5. **Compare.** The new run's detections, false-positive/false-negative notes and
   `T_detect`/`T_identify` should match the committed runs' pattern: all deployed SIDs
   fire, host and network evidence correlate, sub-ten-second first detection. Exact
   timings vary run to run; the **reproduced claim is the coverage and correlation**, not
   a specific second count.

## 4. What is automated vs manual

- **Automated:** Terraform (infra), Ansible (host config + detections), Argo CD
  (continuous reconciliation of the cluster state from Git), and the Week-5 evidence
  tooling (validate / metrics / timeline / figure generation).
- **Manual (by design):** reviewed `terraform apply`, running the Ansible playbooks,
  `kubeseal` unsealing, and launching + authorising each self-range scenario. These are
  the human-in-the-loop gates the programme requires, not missing automation.

## 5. Provenance anchors

Every reported number traces to: the **pinned Git commit**; **immutable image digests**
for the ACP, Hermes, model-serving and platform images; the **`scc26-week5-run/1`**
manifest schema (validated at plan and final); and the **SHA-256** of each raw evidence
file retained on the hosts. See [`EXPERIMENT-PROVENANCE.md`](EXPERIMENT-PROVENANCE.md).
Failed runs are kept, not deleted — a failure is a valid result.
