# Week-2 evidence pack

Owner: Phathutshedzo (`saxs-14`) · Ref: [`week2/README.md`](../../week2/README.md) "Week-2 acceptance gate".

This is an **index**: each row points to sanitised evidence in a PR on GitHub. It is **address-free** (instructor rule on #23); real-address output stays in Discord #purple-1. All checks were run from `k8s-cp-01` (cluster) or from a member workstation over WireGuard (traffic path), following the command-location rule. Times are UTC.

- **Index last updated:** 2026-10-17
- **`dev` at time of writing:** `b3d6b5305afd999512bc3e126b9ca9e54618fc23`

Also in this folder: [architecture diagram](diagrams/README.md) · [troubleshooting notes](troubleshooting.md) · demo: [`docs/demo/week2-demo-runbook.md`](../../docs/demo/week2-demo-runbook.md)

Status key: ✅ done (evidence linked) · 🟡 partly done · ⏳ pending

## Versions in use (read from the live cluster)

| Component | Version | Installed by |
| --- | --- | --- |
| Rocky Linux | 9.5 on all nodes | Terraform image |
| containerd | 2.3.4 (versionlocked) | Ansible `containerd` (#45) |
| Kubernetes | 1.36.4: kubelet, kubeadm, API (versionlocked) | Ansible `kube_prereqs`, `kube_control_plane`, `kube_worker_join` (#45, #48) |
| Cilium | 1.20.1 (image by digest), CLI 0.20.1 (checksum-verified) | Ansible `cilium_bootstrap`, values in `gitops/resources/cilium/` (#49) |
| CoreDNS | 1.14.2 | kubeadm |
| Argo CD | v3.5.0 (manifest checksum-verified) | Ansible `argocd_bootstrap` (#50) |
| Sealed Secrets | controller 0.39.1, kubeseal 0.40.0 | Ansible `sealed_secrets` (#50) |
| Cinder CSI | chart 2.36.5 | Argo `cinder-csi` (#51) |
| cert-manager | v1.21.2 | Argo `cert-manager` (#54) |
| Traefik | v3.7.14 (chart 41.7.1) | Argo `traefik` (#54, #56, #60) |

## Acceptance gate (week2 "Week-2 acceptance gate")

| Gate | Required proof | Status | Evidence |
| --- | --- | --- | --- |
| Runtime | containerd active + `crictl info` works on all K8s nodes | ✅ | Run 1 `changed=16` per node, run 2 `changed=0`; `CRI_OK` on all 3: [#45](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/45) |
| kubeadm | API `/readyz` healthy through the stable HAProxy endpoint | ✅ | `kubeadm init` against the HAProxy endpoint; `readyz` ok and the HAProxy backend UP; run 3 `changed=0`: [#48](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/48) |
| Nodes | CP + two workers registered | ✅ | 3 × `Ready`, kubelet v1.36.4, containerd 2.3.4: [#48](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/48), re-read 2026-10-17 (table above) |
| Cilium | all nodes Ready + connectivity test passes | ✅ | `cilium connectivity test`: **82/82 tests passed** (701 actions): [#49](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/49). Re-run 2026-10-17 to restore the test workloads (kept since; `cilium-test-1`, `-ccnp1`, `-ccnp2`): every connectivity test passed; 1/82 failed only in `no-errors-in-logs`, flagging one cilium-agent *warning* at 21:21 UTC on 10-16 ("CEP was deleted externally" for `storage-test/persistence-test`), which is the pod pruned when #52 merged at 21:17 (see troubleshooting §11) |
| Argo | root app follows this repo/`dev`, controller healthy | ✅ | `root` → `gitops/applications` on `dev`; every child app Synced/Healthy: [#50](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/50), [#51](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/51), [#60](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/60) |
| Sealed Secrets | controller healthy; workstation has the public cert only | ✅ | Public cert on the workstation (0 private-key blocks); offline `kubeseal` works; only the sealed Cinder credential is committed: [#50](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/50), [#51](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/51) |
| Cinder | real PVC write/recreate/read persistence test | ✅ | Marker written, pod deleted (PVC kept), Argo self-heal recreated it **on the other worker**, marker read back: `PASS`; the volume is `in-use` on the new node in OpenStack: [#51](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/51). The test app was removed in #52 and **restored** afterwards (team rule: everything that ran stays on the servers); the persistence test was re-run on the restored volume |
| Ingress | Traefik/cert-manager baseline reachable through the approved path | ✅ | Team CA `pt1-internal-ca` (internal domain `pt1.internal`, #13); the whoami certificate was issued by the Ingress annotation; VPN → worker NodePort 30443 (rule 14b, [#53](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/53)) → Traefik: **HTTP 200, TLS verified against the team CA** on both workers; Pi-hole resolves the names over the VPN: [#54](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/54). Ingress address + `http → https :30443` redirect: [#60](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/60). Domain strategy question to the instructor: [#55](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/55) |
| GitOps | a Git change produces the intended cluster reconciliation | ✅ | whoami `replicas 1 → 2` + pod annotation changed **only in Git** ([#61](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/61), merged 23:20 UTC). Argo reconciled at 23:25: app at the merge commit `b3d6b53`, Synced/Healthy; new ReplicaSet 2/2 across both workers carrying the annotation, old one scaled to 0; the Deployment's only field managers are `argocd-controller` and `kube-controller-manager` (no hand edits): [#61](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/61) |
| PR | Week-2 changes reviewed and merged into `dev` | ✅ | #45, #47–#54, #56, #58–#61 reviewed and merged with the 4 CI checks green; this evidence PR is the last Week-2 PR |

## Beyond the gate

| Item | Evidence |
| --- | --- |
| Per-member access: own Linux account on all 5 hosts (key only, sudo via group) and a personal 30-day kubeconfig on `k8s-cp-01`; rights only via per-member bindings in Git, so access is revocable | [#58](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/58): all four members authenticate as themselves and `get nodes` works |
| Terraform state no longer tied to one laptop: encrypted with age to every member's SSH key, root-only copy on edge-01 | [#59](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/59): decrypted with a member key; checksum equals the live state |
| Volume quota raised by the instructor to 900 GB | `openstack limits show --absolute`: 900 GB volumes, 1 GB used |

## Problems we hit (friction notes)

| Problem | Cause | Fix |
| --- | --- | --- |
| A new join token on every Ansible run | Workers registered as `*.novalocal`, so the "already joined" check missed them | Compare without the domain + `--node-name` (#48) |
| gitleaks failed on #50 | A public sha256 in a variable named `*secrets*` looked like a key | Fingerprinted `.gitleaksignore` entry + inline allow (#50) |
| GitHub showed the stacked Week-2 PRs as conflicting | The chained merges left two merge bases | Merge `dev` into each branch, no force-push |
| Argo showed `ingress-test` Progressing forever | NodePort Traefik had no load-balancer status to publish | `ingressEndpoint.hostname` (#56, #60) |
| `traefik` app stuck at Sync **Unknown** after #56 | The Helm chart only accepts an entrypoint name as the redirect target | `to: websecure` + `exposedPort: 30443`, rendered with `helm template` before pushing (#60) |
| VPN dropped when WSL went idle | WSL shuts down and takes `wg0` with it | Keep a WSL process running while working |
