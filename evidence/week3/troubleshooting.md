# Week-3 troubleshooting notes (real problems)

Each note is a problem the team actually hit in Week 3, with its source on GitHub. Address-free. Times are UTC.

## 1. node-exporter at 0.33: two of three targets down

**When:** 2026-10-17 · **Source:** [#63](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/63), [#69](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/69)

**Symptom:** right after the monitoring stack came up, every job reported `up=1` except `node-exporter`, at 0.33. Only the exporter on the node running Prometheus answered.

**Cause:** node-exporter listens on the **host** network (9100). Prometheus on one node scraping the other two crosses the OpenStack security group, which had no 9100 rule.

**Fix:** SG row 17 (Olerato, #69): 9100/tcp and the Cilium metrics ports from `k8s_cidr` only. After the apply: `node-exporter 1.00`, no targets down.

**Lesson:** "pod Running" is not "target up"; query `up` (week3 §2).

## 2. The README's Prometheus query used a tool the image doesn't have

**When:** 2026-10-17 · **Source:** [#63](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/63)

**Symptom:** `kubectl exec ... -- wget ...` failed: `exec: "wget": executable file not found`. The README example assumes a different chart's `prometheus-server` image.

**Fix:** query through the API server's service proxy from `k8s-cp-01`, with nothing extra in the pod:
`kubectl get --raw '/api/v1/namespaces/monitoring/services/kps-prometheus:9090/proxy/api/v1/query?query=up'`.

## 3. Four control-plane jobs could only ever be red

**When:** 2026-10-16 · **Source:** [#68](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/68)

**Cause:** kubeadm binds the etcd, scheduler, controller-manager and kube-proxy metrics to `127.0.0.1`, so a scrape from a pod always fails.

**Decision:** those four scrapes are switched off and documented in the values, rather than left as permanent red targets that hide real failures.

## 4. Suricata ran but wrote no events

**When:** 2026-10-25 17:12 · **Source:** [#75](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/75)

**Symptom:** the service was active and the config valid, but `eve.json` stayed empty and the first drill found nothing.

**Cause:** `suricata.log` showed `Error opening file: "/var/log/suricata/eve.json": Permission denied`. Our role ran `suricata -T` **as root**, which created `eve.json`, `fast.log` and `stats.log` owned by root. The service drops to the `suricata` user and could not open them.

**Fix:** the role makes those files belong to `suricata` and runs the validation as `suricata`. The next drill produced the EVE alert; run 3 `changed=0`.

**Lesson:** a validation step can change state too. Run it as the user the service runs as.

## 5. Workstation clock vs server clock in the drill timeline

**When:** 2026-10-25 · **Source:** [#75](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/75)

**Symptom:** the Suricata alert time (from edge-01) came out 3 s *before* the drill "start" printed on the workstation.

**Cause:** edge-01 is NTP-synced (`chronyc`: 0.00004 s slow); the WSL workstation clock was about 3 s fast.

**Fix:** drill start/end are now read from the edge-01 clock. For the security chain, **server timestamps are authoritative** (week3 §8 "can another team member reconstruct the timeline?").

## 6. The Wazuh agent rule existed but was switched off

**When:** 2026-10-25 · **Source:** [#69](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/69), [#76](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/76)

**Note:** Olerato's #69 rendered the edge nftables rules for Wazuh (1514-1515, 55000) only when `firewall_wazuh_*_cidrs` is set, so edge was unchanged until Wazuh existed. Before running `wazuh.yml`, the private inventory set them from the existing `firewall_private_cidrs` (no new addresses), and `edge.yml --tags firewall` applied them (`changed=2`). All four agents enrolled on the first run.

## 7. gitleaks flagged SealedSecret ciphertext

**When:** 2026-10-17 · **Source:** [#73](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/73)

**Cause:** the `generic-api-key` rule fires on the key name `POSTGRES_PASSWORD`, even under `spec.encryptedData` (Sealed Secrets ciphertext, `Ag…`). Olerato verified it without printing any value.

**Fix:** one pinned fingerprint in `.gitleaksignore` with the reason, as in Week 2; nothing else relaxed.

## 8. Astro refused the pinned Node version

**When:** 2026-10-26 · **Source:** [#77](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/77)

**Symptom:** the image build failed at `npx astro build`: `Node.js v22.21.1 is not supported by Astro! ... ">=22.23.4"`.

**Fix:** Node 24.21.0 LTS (more than two weeks old), pinned by digest in both Dockerfile stages. Build and smoke test green.

## 9. Local build killed for low memory

**When:** 2026-10-25 · **Who:** captain

**Symptom:** the local `npm install` + `astro build` was stopped by the OS for low memory (the workstation runs WSL with about 2 GB).

**Fix:** the lockfile was resolved with `npm install --package-lock-only` (no download), and the real build runs where it belongs: in GitHub Actions (week3 §11, "build images in GitHub, not on the workstation").

## 10. Finding the drill in Wazuh: three traps

**When:** 2026-10-26 (testing the demo runbook) · **Source:** [`docs/demo/week3-demo-runbook.md`](../../docs/demo/week3-demo-runbook.md)

- **Self-match:** `grep 'scc26-drill-nouser' alerts.json` returned rule **5402** "Successful sudo to ROOT executed", which is Wazuh logging our own `sudo grep ...` command line. Select alerts by rule ID with `jq`, not by grepping the drill text.
- **Rule 86601 is generic:** it covers every Suricata alert, so also filter on `.data.alert.signature_id == "9000001"`.
- **Daily rotation:** `alerts.json` rotates at midnight; the 2026-10-25 drill alerts are in `/var/ossec/logs/alerts/2026/Oct/`. Run a fresh drill on the day of a demo.

**Observation:** Suricata/Wazuh also raised *ET INFO "Server Responded with Vulnerable OpenSSH Version (CVE-2024-6409)"* on our SSH banners. Rocky Linux backports security fixes without changing the upstream version string, so this banner-based rule is likely a false positive. It is recorded here for Week 5 rather than suppressed.

## 11. GHCR refused the image push (org setting)

**When:** 2026-10-26 · **Source:** [#79](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/79), [#80](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/80)

**Symptom:** on `dev`, tests, build and smoke test passed, then `docker push ghcr.io/chpc-tech-eval/...` failed with `error from registry: denied`, although the job's `GITHUB_TOKEN` had `Packages: write`.

**Cause:** the `chpc-tech-eval` organisation doesn't let this repo create container packages. Only an org owner can change that, and the instructor was unavailable.

**Fix:** the image is published under the captain's GHCR namespace (`ghcr.io/saxs-14/scc26-student-platform`) with a 30-day, `write:packages`-only token stored as the repo secret `GHCR_TOKEN`, and the package made public so the cluster pulls without credentials. Still GHCR, still built by Actions, still an immutable `sha-` tag. The question stays open on #79.

## 12. Merging with no available reviewer

**When:** 2026-11-01 · **Source:** [#75](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/75), [#80](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/80), [#81](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/81)

**Situation:** every other member and the instructor were unavailable, and `dev` requires one approval. Branch protection also applied to admins, so there was no bypass at first.

**What we did:** the captain (repo admin) briefly allowed admin bypass, merged #75, #80 and #81 with CI green, and then switched enforcement back on (`enforce_admins=true` verified). Each PR carries a note explaining the exception and asking for review after the fact. It is recorded as an exception, not a new practice.

## 13. A PostgreSQL restart crashed the platform pods

**When:** 2026-11-01 · **Source:** [#66](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/66), [#82](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/82)

**Symptom:** during the §13 test (deleting `postgres-0`), both platform pods restarted 3 times and a login attempt got no response. The data survived and the pods self-healed.

**Cause:** node-postgres emits an `error` event when an idle pooled connection drops; with no listener, Node exits.

**Fix (#82):** a pool `error` handler (log, reconnect on next use), a start-up `waitForDatabase()` retry instead of crash-looping, and a regression test.

## 14. Pi-hole seemed to answer on one edge address only (it was the link)

**When:** 2026-11-01

**Symptom:** a VPN query to Pi-hole on edge-01's management address timed out while the wg0 address answered. In a burst of 20 queries each, the results flipped: management 14/20, wg0 0/20.

**Investigation:** the edge nftables ruleset is correct (input policy drop; DNS allowed from the three private ranges via `@dns_src`), Pi-hole listens on all addresses, and `terraform plan` shows **No changes** (no security-group drift). Ping showed 0% loss but round-trip times of **86-980 ms** (average 550 ms). At one query per second with a 6 s timeout, **both** addresses answered (9/10 and 8/10).

**Conclusion:** not a firewall problem. The misses come from a slow, jittery workstation link. For demos, use a longer DNS timeout or `curl --resolve`, and test the path before presenting.
