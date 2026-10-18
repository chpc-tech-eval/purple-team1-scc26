# Week-2 troubleshooting notes (real problems)

Each note is a problem the team actually hit in Week 2, with its source on GitHub. Address-free. Times are UTC.

## 1. A new kubeadm join token on every Ansible run

**When:** 2026-10-15 · **Source:** [#48](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/48)

**Symptom:** the second run of `kubernetes.yml` still created a fresh join token and tried to join workers that were already in the cluster, so it was never `changed=0`.

**Cause:** the workers registered as `k8s-worker-0N.novalocal` (the OpenStack DHCP domain), but the "already joined?" check compared against the short inventory name, so it never matched.

**Fix:** compare node names with the domain stripped, and join with an explicit `--node-name`. Run 3 was `changed=0`. The existing workers keep their `.novalocal` names (cosmetic; renaming means a reset and rejoin, which we did not do).

**Lesson:** an idempotence check is only as good as its comparison. Check what the cluster actually reports, not what you expect it to report.

## 2. Cilium's default IPAM pool overlapped our private ranges

**When:** 2026-10-15 · **Source:** [#49](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/49)

**Symptom (caught in review, before install):** Cilium's default cluster-pool IPAM uses `10.0.0.0/8`, which contains our management, Kubernetes and VPN ranges.

**Fix:** `ipam.mode: kubernetes`, so pods get addresses from the kubeadm pod CIDR that is set in the private inventory and passed to `kubeadm init`. VXLAN tunnelling, kube-proxy kept. `cilium connectivity test`: 82/82 passed.

**Lesson:** read the defaults of anything that allocates addresses before installing it.

## 3. gitleaks flagged a public checksum as a secret

**When:** 2026-10-15 · **Source:** [#50](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/50)

**Symptom:** the `secret scan (gitleaks)` check failed with `generic-api-key` on `sealed_secrets_manifest_sha256`.

**Cause:** a 64-hex-character value in a variable whose name contains "secrets" looks like a key to the generic rule. It is the public SHA-256 of the released `controller.yaml`, which anyone can recompute.

**Fix:** one fingerprinted entry in `.gitleaksignore` (commit:file:rule:line) plus an inline `# gitleaks:allow`, with a comment explaining why. The rule itself was not weakened.

**Follow-up:** gitleaks scans the **full history of every fetched branch**, so other open PRs saw that same commit and failed too. The identical `.gitleaksignore` was carried into those branches ([#48](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/48)).

## 4. GitHub said the stacked Week-2 PRs were "conflicting"

**When:** 2026-10-15 15:00 · **Source:** [#48](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/48), [#49](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/49)

**Symptom:** after #45 merged, #48 showed `CONFLICTING`, but `git merge` and `git merge-tree` locally were clean.

**Cause:** the PRs were chained with normal merges (#45 → #48 → #49 → #50 → #51), which left **two merge bases** against `dev`. GitHub does not resolve that case; git does.

**Fix:** merge `dev` into each branch in turn (a normal merge, no force-push), wait for CI, then merge. All five went in.

**Lesson:** stacking PRs saves waiting, but merge `dev` into the next branch after each merge.

## 5. Argo showed `ingress-test` as Progressing forever

**When:** 2026-10-16 · **Source:** [#54](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/54), [#56](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/56), [#60](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/60)

**Symptom:** HTTPS through Traefik worked (HTTP 200, certificate verified), but Argo CD never marked the Ingress Healthy.

**Cause:** there is no Octavia load balancer, so Traefik is a NodePort Service. Its `publishedService` setting copies the Service's load-balancer status onto each Ingress, and that status is empty. Argo's Ingress health check waits for an address.

**Fix:** turn `publishedService` off and set `ingressEndpoint.hostname: ingress.pt1.internal`. Ingresses now show that name and go Healthy. No address is in the repo.

## 6. The http → https redirect pointed at a closed port

**When:** 2026-10-16 · **Source:** [#56](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/56), [#60](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/60)

**Symptom:** `http://whoami.pt1.internal:30080/` answered `301 → https://whoami.pt1.internal/`, which is port 443. Only the NodePorts 30080/30443 are reachable.

**First fix, which broke the app:** #56 set the redirect target to `":30443"`, which the Traefik binary accepts. The **Helm chart** does not: `ERROR: Cannot redirect web to :30443: entryPoint not found`. Argo could not render the app and showed **Sync: Unknown**. It kept the last good config running, so there was no outage, but neither fix was live.

**Real fix (#60):** `to: websecure` plus `ports.websecure.exposedPort: 30443`. The chart renders `to=:<exposedPort>`, so the redirect lands on 30443. Verified: `301 → https://…:30443/` → `200`, TLS verified.

**Lesson:** render chart values with `helm template` before pushing. We now do, with the app's exact `valuesObject` and the pinned chart version.

## 7. The cluster nodes do not use Pi-hole

**When:** 2026-10-16 · **Source:** [#54](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/54)

**Symptom:** `getent hosts whoami.pt1.internal` on `k8s-cp-01` returned nothing, even though the record was in Pi-hole.

**Cause:** the nodes resolve through the OpenStack subnet DNS. Pi-hole (on edge-01) serves VPN clients; it is not the nodes' resolver. The WireGuard client config also has no `DNS=` line, so a workstation has to ask Pi-hole explicitly.

**Effect:** none for Week 2, since users reach apps over the VPN. Week-3 workloads that call `*.pt1.internal` from inside the cluster will need CoreDNS forwarding for `pt1.internal` or a node resolver change (open item).

## 8. Ansible 2.21: `object of type 'dict' has no attribute 'state'`

**When:** 2026-10-17 · **Source:** [#58](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/58)

**Symptom:** the new `team_users` role created the group, sudoers rule and accounts, then failed on the key task on all 5 hosts.

**Cause:** `rejectattr('state', 'equalto', 'absent')` touches an attribute most members don't have, and Ansible 2.21 treats an undefined attribute as an error.

**Fix:** loop over everyone with `when: item.state | default('present') == 'present'`, and use `selectattr('state', 'defined')` where a filtered list is needed. Re-run: `changed=0`.

## 9. A group-wide cluster-admin binding could not be revoked

**When:** 2026-10-17 · **Source:** [#58](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/58)

**Symptom (caught by a security review before anything went live):** the first design gave every member certificate `O=scc26-admins` and bound that group to cluster-admin.

**Cause:** Kubernetes client certificates cannot be revoked. A member leaving the team would have kept cluster-admin until their certificate expired.

**Fix:** one ClusterRoleBinding per member (`User` = certificate CN) in Git, a certificate group with no binding, and 30-day certificates renewed by the playbook. Off-boarding = delete that member's binding; access ends on the next Argo sync.

## 10. Operations: the VPN dropped when WSL went idle

**When:** throughout · **Who:** captain

**Symptom:** SSH and Ansible suddenly timed out to every host.

**Cause:** the captain's WireGuard client runs in WSL. Windows shuts an idle WSL down, and `wg0` goes with it.

**Fix:** keep a WSL process running while working (a hidden `sleep`), and re-run `vpn-up.sh` after a restart. A separate case (a public-IP change mid-session) caused brief SSH stalls with healthy hosts. Ansible now runs with `--timeout 30`, so a stall fails fast instead of hanging.

## 11. A test app was removed, then restored

**When:** 2026-10-16/17 · **Source:** [#52](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/52), [#70](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/70)

**What happened:** after the Part E persistence evidence was recorded, #52 removed the `storage-test` app. Argo pruned the pod and PVC, and the Cinder volume was deleted with it.

**Decision (captain, 2026-10-17):** everything that ran on the servers stays there until the end of the project. #70 restores the app from Git history, and the persistence test is re-run on the new volume. Test apps (`storage-test`, `ingress-test`) and test workloads (the Cilium connectivity test, re-run without cleanup) are now kept permanently.

**Trace it left:** the Cilium connectivity re-run on 2026-10-17 passed every connectivity test, but its `no-errors-in-logs` check (1/82) flagged one cilium-agent warning, *"CEP was deleted externally"* for `storage-test/persistence-test`, logged at 21:21 UTC on 10-16, four minutes after #52 merged and Argo pruned that pod. It is expected for a pod deleted while its endpoint was syncing, and not a network fault. The full log is kept on k8s-cp-01 in `~/scc26-evidence/`.
