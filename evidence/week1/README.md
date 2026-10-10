# Week-1 evidence pack

Owners: Siyabonga (`Swaetc`), Phathutshedzo (`saxs-14`) · Issue [#15](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/15) · Ref: [`week1/README.md`](../../week1/README.md) "Week-1 evidence and PR" and Part H (acceptance ladder).

This is an **index**: each row points to sanitised evidence on GitHub or in this folder. It is **address-free** (instructor rule on #23): no real CIDRs, fixed IPs, floating IP or SSH source IPs. Real-address outputs stay in Discord #purple-1. Times are UTC.

- **Index last updated:** 2026-10-05 23:10 UTC
- **`dev` at time of writing:** `a90a93d2365db61398088e6bf946ff41d5c3b5e1`

Status key: ✅ done (evidence linked) · 🟡 partly done · ⏳ pending

## Acceptance ladder (week1 Part H)

| Layer | Expected | Status | Evidence |
| --- | --- | --- | --- |
| Git | work on feature branches from `dev` | ✅ | `main`/`dev` protected (PR only, 1 approval, conversations resolved, 4 CI checks green). All Week-1 changes merged via PRs #17–#35. [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |
| OpenStack auth | `openstack token issue` succeeds | ✅ | Captain, [#8](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/8#issuecomment-5986712954) (2026-10-05 01:39). Olerato with her own credential, [#11](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/11#issuecomment-5994463656) (12:29) |
| Quota | enough headroom | ✅ | [`sebowa-discovery.md`](sebowa-discovery.md): 48 vCPU / 96 GiB vs 30 / 60 needed; 1 floating IP |
| Terraform | `fmt`, `validate`, reviewed plan clean | ✅ | `validate` Success; plan **42 to add, 0 to change, 0 to destroy** from `dev` @ `ef17d37`, matched by the captain's independent read-only plan: [#11](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/11#issuecomment-5994463656) (12:29). CI `terraform fmt + validate` green on every PR |
| Terraform drift | second plan: no unexpected changes | ✅ | `No changes. Your infrastructure matches the configuration.`: [#11](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/11#issuecomment-5995385135) (13:25) |
| Nova/Neutron | lists match the diagram | ✅ | 5 servers ACTIVE (edge-01 `large`, api-lb-01 `small`, k8s-cp-01 `medium`, 2 × workers `scc.large`); router with 2 interfaces + 1 static route; 4 SGs / 17 ingress rules: [#11](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/11#issuecomment-5995385135) (13:25), captain re-check [#11](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/11#issuecomment-5995674841) (13:41) |
| Public exposure | only the intended edge path | ✅ | Exactly 1 floating IP, on edge-01. Temporary bootstrap SSH **removed** after the VPN proofs (plan `0/0/1`, apply, second plan `No changes`); now the **only** rule open to anywhere is WireGuard UDP 51820 and no rule has a public source; TCP 22 to the floating IP times out: [#13 step 3](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/13#issuecomment-6004684236) (22:43), captain verification [#13](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/13#issuecomment-6004741241) (22:46) |
| SSH | works through the intended path | ✅ | Bootstrap: direct SSH to edge-01 + ProxyJump [#12](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/12#issuecomment-5995851693) (13:51). **Steady state: direct SSH over WireGuard to all 5 hosts, no ProxyJump**, by Olerato [#13](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/13#issuecomment-6004182430) (22:13) and the captain [#13](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/13#issuecomment-6004492619) (22:30), each with their own key |
| Ansible inventory | `--graph` / `--host` show correct groups and vars | ✅ | Graph: 5 hosts in `edge_nodes` / `private_nodes` (`api_lb`, `control_plane`, `workers`), ProxyJump resolved for private hosts; `ping` 5 × SUCCESS: [#12](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/12#issuecomment-5999725962) (Ole06, 17:34, `dev` @ `d5dd9ca`) |
| Ansible convergence | second bootstrap: no unexplained changes | ✅ | Run 1: `changed=4` per host (packages, timezone, member keys, sshd drop-in), 22 s. Run 2: **`changed=0`** on all 5, 11 s. All hosts: `Africa/Johannesburg`, chrony synced (stratum 2), SELinux Enforcing: [#12](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/12#issuecomment-5999725962) (17:34) |
| WireGuard | private SSH works before public SSH is removed | ✅ | Edge services applied, 4 peers [#13](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/13#issuecomment-6003275019) (21:26); **two members** proved private SSH over the VPN (22:13, 22:30), **then** public SSH was removed (22:43). Hosts see each member's **own** VPN address (routed, no NAT): per-member attribution for Week 5 |
| HAProxy | syntax/service/listener healthy; backend may be DOWN | ✅ | `api-lb.yml` run 1 `changed=5`, run 2 **`changed=0`**; `haproxy -c` valid; active + enabled; listening on 6443; SELinux Enforcing with `haproxy_connect_any` on; backend `k8s-cp-01` DOWN (*connection refused*), as expected before kubeadm: [#14](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/14#issuecomment-6004936750) (22:59) |
| GitHub | Week-1 PR reviewed and merged into `dev` | ✅ | All Week-1 work reached `dev` through reviewed PRs (#6–#41) with the 4 CI checks required; this final evidence update is the last Week-1 PR |

## Evidence items (#15 checklist)

| Item | Status | Where |
| --- | --- | --- |
| Architecture / trust-boundary diagram | ✅ | [`diagrams/`](diagrams/README.md) (Mermaid source + rendered on GitHub). Design: [`docs/network-design.md`](../../docs/network-design.md) (#18, #26) |
| Terraform provider lock + Git SHA | ✅ | [`.terraform.lock.hcl`](../../infrastructure/terraform/environment/.terraform.lock.hcl): `terraform-provider-openstack/openstack` **3.4.0** (pinned exactly in `providers.tf`; Terraform `>= 1.9.0`, team baseline 1.16.5). Lock last changed in `a073617ccaaee0fa2f3ba63ac19875395e913f82`; applied plan built from `ef17d37` + #33 (`a1735de`) |
| Sanitised plan summary + OpenStack resource summary | ✅ | Plan: 42 add (5 instances, 1 FIP + 1 association, 2 networks, 2 subnets, 1 router, 2 router interfaces, 1 route, 5 ports, 4 SGs, 17 rules, 1 keypair). Resources: see the Nova/Neutron row. Full outputs only in Discord #purple-1 |
| Ansible inventory graph | ✅ | [#12 bootstrap ACK](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/12#issuecomment-5999725962), steps 1–3 |
| First and second bootstrap recaps | ✅ | [#12 bootstrap ACK](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/12#issuecomment-5999725962): run 1 `ok=8 changed=4`, run 2 `ok=7 changed=0`, 5 hosts, 0 unreachable / 0 failed |
| WireGuard / private-access proof (no keys) | ✅ | [#13 Olerato](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/13#issuecomment-6004182430), [#13 captain](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/13#issuecomment-6004492619): all 5 hosts, own keys, own VPN address seen |
| HAProxy validation | ✅ | [#14](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/14#issuecomment-6004936750) |
| Edge services (nftables, WireGuard, Pi-hole) | ✅ | Run 1 `changed=19`; on fixed code (#39) run 2 **`changed=0` in 36 s** (was 6 min); policy-drop input/forward, VPN-only SSH and Pi-hole UI, Pi-hole answers `pt1.internal` from private hosts: [#13](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/13#issuecomment-6003275019), [re-run](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/13#issuecomment-6003975405) |
| At least one real troubleshooting note | ✅ | [`troubleshooting.md`](troubleshooting.md): partial apply (FIP race + Nova 408), CI collections, slow edge facts (ICMPv6), setup-guide `unzip` |
| Sebowa discovery summary | ✅ | [`sebowa-discovery.md`](sebowa-discovery.md) (from #8) |
| CI evidence | ✅ | 4 checks: secret scan (gitleaks), yamllint, terraform fmt + validate, ansible-lint + syntax-check. Added in #17, collections fix #20; green on #17 and #20 and required on `dev` |
| Workstation toolsets | ✅ | [#7](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/7): all four members posted (Siyabonga: [comment](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/7#issuecomment-5999779829)) |

## Rules for adding evidence here

- Address-free: use variable names (`mgmt_cidr`, `k8s_cidr`, `vpn_cidr`) or RFC 5737 dummy addresses, plus counts and pass/fail results.
- Never commit tokens, application-credential IDs/secrets, passwords, private keys, kubeconfigs, Terraform state or project/user IDs.
- Every item gets a UTC timestamp and the Git SHA it was produced from. Historical output is never presented as a fresh test.
- Unknown values are written as `UNKNOWN — NEEDS VERIFICATION`, never guessed.
