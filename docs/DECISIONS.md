# Team decision log — 3NCRYP+3D

Record of **decisions and instructor answers** only. Newest first. No credentials, IPs or private topology here.

Questions for the instructor are raised as **GitHub issues** (label `question`, mention `@nyameko`), not written into this file. Once answered, the outcome is recorded below with a link to the issue.

## Decided

| Date | Decision | Why / source |
| --- | --- | --- |
| 2026-10-05 | `main` and `dev` are **protected**: PR only, 1 approval, conversations resolved, the 4 CI checks required, no force-push/deletion, enforced for admins too | Instructor recommendation; applied by the captain |
| 2026-10-05 | **edge-01 flavor = `large`** (8 vCPU / 16 GiB / 150 GB): no 4 vCPU / 10 GiB flavor exists, `medium` is 2 GiB short, and Wazuh Manager + Suricata land on edge in Week 3; still within quota (30 vCPU / 60 GiB total) | Captain decision; #8, #19 |
| 2026-10-05 | Questions for the instructor go in **separate GitHub issues** (label `question`), never inside commits or docs | Instructor review on #6 |
| 2026-10-05 | We **write our own** student Terraform and Ansible; the instructor provides examples, and `nyameko/infra-hpc-qc-k8s` is reference only | Instructor answer on #16 |
| 2026-10-05 | **Edge exposure:** WireGuard on **UDP 51820**, reachable from anywhere (it drops unauthenticated packets; members' home IPs change); temporary bootstrap SSH from a single applier /32, removed via Terraform once WireGuard works for two members | Captain decision; #11, #18 |
| 2026-10-05 | **Pi-hole internal domain `pt1.internal`** (`.internal` is reserved for private use); upstream resolver: **edge-01's own Neutron resolver** (a resolver seen from the k8s subnet only serves that subnet). `1.1.1.1` was configured as a fallback, but Sebowa appears to refuse outbound queries to it, so treat it as non-functional | Captain decision; corrected per Olerato's finding C on #13 |
| 2026-10-05 | **Run-side work stays with whoever has host access** (Olerato until WireGuard is up), approved run by run by the captain; code and reviews continue from everyone | Captain decision; #12 |
| 2026-10-05 | **Boot from image** (`boot_volume_size = null`): flavor root disks (50-150 GB) already exceed the brief's sizes, no Cinder quota is used, and teardown/rebuild in Week 6 is simpler | Captain decision; #19 |
| 2026-10-05 | **No real network architecture on GitHub** (public repo): no real CIDRs, IPs, floating IP or address-bearing plan output in files, issues, PRs or comments; examples use placeholders/RFC 5737 addresses; real values stay in gitignored files and the private Discord channel | Instructor review on #23 |
| 2026-10-05 | The **captain makes the final merge** after instructor/peer approval; captain-authored PRs are merged by another member | Instructor comment on #21 |
| 2026-10-05 | Private network CIDRs **approved as proposed in #21** (RFC 1918, non-overlapping, clear of the Kubernetes service range); the pod network is set explicitly in kubeadm **and** Cilium in Week 2 | Instructor answer on #21 |
| 2026-10-05 | Merged: network design (#18), Terraform modules + environment (#19), CI collections fix (#20), decision log (#22) | Approved by the instructor |
| 2026-10-05 | External network is **"Public Internet"**; the project has exactly **one floating IP** (on edge-01) | #8 discovery, instructor answer on #16 |
| 2026-10-05 | Image **Rocky 9**; bootstrap/cloud user **`rocky`** | #8 discovery, instructor answer on #16 |
| 2026-10-05 | Terraform state **stays local, on the private workstation** of whoever applies; never in Git or a shared backend | Instructor answer on #16 |
| 2026-10-05 | Captain's repo role raised to `admin`; other members are `maintainer` | Instructor answer on #16 |
| 2026-10-05 | Week-6 paper uses the repo's IEEE scaffold (`paper/`); depending on quality it may be submitted to internal journals | Instructor answer on #16 |
| 2026-10-05 | Every PR into `dev`/`main` runs credential-free CI: gitleaks, yamllint, Terraform fmt/validate, Ansible syntax-check/lint | #17 |
| 2026-10-04 | Team workstations run inside **WSL2 Ubuntu** on Windows laptops | Ansible's control node does not run natively on Windows; keeps every member on the same toolchain |
| 2026-10-04 | Workstation toolset: Git, SSH, OpenStack CLI, Terraform, Ansible, kubeseal. **No** kubectl/Helm/Argo CLI on workstations | `docs/COMMAND-LOCATIONS.md`, `week1/README.md` §0.2 |
| 2026-10-04 | Credentials live only in `~/.config/openstack` and `~/.config/scc26-secrets` (mode 700); the repo `.gitignore` blocks state, tfvars, `clouds.yaml`, keys, kubeconfigs and private inventories | `week1/README.md` §0.3, `docs/SECRETS-AND-LOCAL-FILES.md` |
| 2026-10-04 | `main` and `dev` are never committed to directly; small feature branches → PR into `dev`, instructor added as reviewer | Instructor guidance, `CONTRIBUTING.md` |
| 2026-10-04 | Sebowa team account is the **PurpleTeamB** account; this GitHub repo (`purple-team1-scc26`) is ours | Confirmed by team captain |
| 2026-10-04 | Week 1 follows `main`/`dev` (merged `feature/student-weeks-1-7`), not the superseded `feature/student-weeks-1-4` | Branch history (PR #4, #5) |
| 2026-10-04 | Week 1 edge scope is WireGuard, Pi-hole/DNS and nftables; Wazuh Manager and Suricata are added in Week 3 | `week1/README.md` §20, `week3/README.md` |

## Pending team decisions

Design choices the team owns (not instructor questions). Tracked in the linked issues/PRs:

- None open right now.

## Roles

| Member | GitHub | Starting ownership |
| --- | --- | --- |
| Olerato | `Ole06` | Infrastructure deployment: OpenStack, Terraform, networking, security groups, DNS/firewall design |
| Rendani | `Rendani-Anele` | Cloud automation: Ansible, Kubernetes, Cilium, Cinder |
| Phathutshedzo (captain) | `saxs-14` | CI/CD, telemetry & security: Argo CD, Prometheus/Grafana, Wazuh, Suricata; Git workflow |
| Siyabonga | `Swaetc` | Front-end & agents: Astro, ACP/Hermes, Week-5 specialisation |

Roles rotate after major milestones; everyone should be able to explain the whole stack.
