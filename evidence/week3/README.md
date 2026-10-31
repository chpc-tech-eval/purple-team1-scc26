# Week-3 evidence pack

Owners: Phathutshedzo (`saxs-14`), Olerato (`Ole06`) · Ref: [`week3/README.md`](../../week3/README.md) "Week-3 acceptance gate" · Issues: [#63](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/63) [#64](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/64) [#65](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/65) [#66](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/66) [#67](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/67)

This is an **index**: each row points to sanitised evidence on GitHub. It is **address-free** (instructor rule on #23). Cluster checks ran on `k8s-cp-01`, host checks on the hosts, and traffic checks from a member workstation over WireGuard (command-location rule). Times are UTC; for the security chain the **server (NTP) clocks are authoritative**.

Also in this folder: [architecture diagram](diagrams/README.md) · [troubleshooting notes](troubleshooting.md) · demo: [`docs/demo/week3-demo-runbook.md`](../../docs/demo/week3-demo-runbook.md) · run manifests: [`evidence/runs/`](../runs/README.md)

Status key: ✅ done (evidence linked) · 🟡 partly done · ⏳ pending

## Versions in use

| Component | Version | Installed by |
| --- | --- | --- |
| kube-prometheus-stack | chart 91.9.0 (operator v0.94.1) | Argo `monitoring` (#68) |
| Grafana / Prometheus storage | 5Gi / 20Gi on `cinder-ssd` | Argo `monitoring` (#68) |
| Suricata | 7.0.17 (EPEL), ET Open via suricata-update | Ansible `suricata` (#75) |
| Wazuh manager + agents | 4.14.8 | Ansible `wazuh_manager`, `wazuh_agent` (#76) |
| PostgreSQL | 17.11 (by digest), 10Gi `cinder-ssd` | Argo `student-platform` (#73) |
| Student Project Platform | Node 24.21.0 (by digest), Astro 7.4.2, Express 5.3.0 | GitHub Actions → GHCR (#77) |

## Acceptance gate (week3 "Week-3 acceptance gate")

| Gate | Proof required | Status | Evidence |
| --- | --- | --- | --- |
| Prometheus | real targets/queries return current data | ✅ | `up` by job via the API: apiserver, coredns, alertmanager, grafana, operator, prometheus, kube-state-metrics, kubelet, node-exporter **all 1.00**, no targets down; node memory per node returned. node-exporter was 0.33 until SG row 17 opened 9100 between nodes: [#63](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/63), [#64](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/64) |
| Grafana | Git-managed dashboard renders live metrics | ✅ | Dashboard "SCC26 3NCRYP+3D overview" loaded by the sidecar from a ConfigMap in Git (10 panels, UTC); Grafana's Prometheus datasource returns live data; served at `grafana.pt1.internal` with a team-CA certificate, 401 without login: [#63](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/63), [#68](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/68) |
| Wazuh | manager active; expected agents enrolled/active | ✅ | `wazuh-manager` active, v4.14.8; `agent_control -l`: edge-01 (server) + api-lb-01, k8s-cp-01, k8s-worker-01, k8s-worker-02 **all Active**; playbook run 2 `changed=0`: [#76](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/76) |
| Suricata | config valid; fresh EVE event from authorised test | ✅ | IDS mode (af-packet on the edge NIC + `wg0`, no inline IPS); `suricata -T` loads; 53,256 rules; team drill rule `sid 9000001` fired in EVE at 17:18:05 and 17:47:41 on 2026-10-25: [#75](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/75) |
| Security chain | fresh event reconstructable from timestamps/evidence | ✅ | **Host:** 17:44:32 failed SSH login as a non-existent user → Wazuh rule **5710** from agent api-lb-01 at 17:44:35. **Network:** 17:47:41 marker request over the VPN → Suricata EVE sid 9000001 at 17:47:41.97 → Wazuh rule **86601** at 17:47:42.02: [#76](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/76) |
| Student Platform | CI-built immutable image deployed through Argo | 🟡 | App + image workflow ([#77](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/77)): unit tests 6/6, image build and smoke test (`/healthz` + sign-in page from the real image) green in CI. The GHCR push happens on merge into `dev`; the Argo deployment by digest follows |
| Auth | real browser login/logout works | ⏳ | bcrypt + server-side sessions in PostgreSQL, implemented and unit-tested in #77; browser proof after deployment |
| PostgreSQL | state survives DB pod replacement | ✅ | Row `persist-20261018T190314Z` written, `postgres-0` deleted (PVC kept), row read back: **PASS**; NetworkPolicy blocks other namespaces (DNS resolves, 5432 times out): [#66](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/66), [#73](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/73) |
| TLS/Ingress | intended hostname/path works | 🟡 | Pattern proven for Grafana (`grafana.pt1.internal`, team CA) in #68; the platform Ingress `platform.pt1.internal` is part of the deployment |
| Provenance | at least one run manifest recorded without secrets | ✅ | Allowlist writer (refuses secret-looking values and private addresses, immutable images only): [#72](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/72); 3 manifests in [`evidence/runs/`](../runs/README.md) |
| PR | Week-3 state reviewed and merged into `dev` | 🟡 | #68, #69, #72, #73, #74 merged; #75, #76, #77 in review |
