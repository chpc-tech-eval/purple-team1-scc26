# Sebowa discovery summary (sanitised)

Source: captain's read-only discovery on [#8](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/8#issuecomment-5986712954), run **2026-10-05 01:39 UTC** from the captain's workstation (WSL2, OpenStack CLI 10.3.0, application-credential auth). Nothing was created or modified. The raw output stays private and is not in Git.

This is **historical** discovery output from before the apply. It is not proof of the current state; see the #11 verification for that.

## Authentication

`openstack token issue`: **OK** (Keystone v3, region `RegionOne`, application-credential auth). Token not recorded.

## Quota vs five-node POC

| Resource | Quota | POC needs | Fits? |
| --- | ---: | ---: | --- |
| vCPU | 48 | 26 (30 with edge `large`) | yes |
| RAM | 96 GiB | 54 GiB (60 GiB with edge `large`) | yes |
| Cinder volume storage | 900 GB | 0 (boot from image, #24) | yes |
| Floating IPs | **1** | 1 (edge only) | yes, exactly |
| Instances / networks / routers / SGs / ports | unlimited | 5 / 2 / 1 / 4 / 5 | yes |

## Provider resources

- **Images:** Rocky 9, Ubuntu 22.04, Ubuntu 24.04, Fedora CoreOS 42. Rocky 9 is the course baseline.
- **External network:** `Public Internet` (external, not shared).
- **Volume types:** NVMe, HDD, `__DEFAULT__` (for Cinder CSI StorageClasses in Week 2).
- **Availability zone:** `nova`.
- **Before apply:** 0 servers, 0 routers, 0 floating IPs, 0 volumes, 0 keypairs, 1 security group (OpenStack `default`).

## Flavors and the host mapping we chose

| Flavor | vCPU | RAM | Disk | Used by |
| --- | ---: | ---: | ---: | --- |
| scc.tiny | 1 | 2 GiB | 50 GB | none |
| small | 2 | 4 GiB | 50 GB | `api-lb-01` |
| medium | 4 | 8 GiB | 100 GB | `k8s-cp-01` |
| large | 8 | 16 GiB | 150 GB | `edge-01` (team decision, #22) |
| scc.large | 8 | 16 GiB | 100 GB | `k8s-worker-01`, `k8s-worker-02` |
| scc.xlarge | 12 | 24 GiB | 100 GB | none |

No flavor matched the brief for `edge-01` (4 vCPU / 10 GiB). The team chose `large` to leave headroom for Wazuh Manager and Suricata in Week 3 (recorded in `docs/DECISIONS.md`, #22).

## How the open questions from #8 were resolved

| Question | Resolution |
| --- | --- |
| edge-01 flavor | `large` (#22) |
| Boot from image vs boot-from-volume | boot from image (#24) |
| Keypair | created by Terraform (#19) |
| CIDRs | team proposal approved by the instructor (#21); values kept off GitHub (#23) |
