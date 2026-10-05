# Team decision log — 3NCRYP+3D

Record of **decisions and instructor answers** only. Newest first. No credentials, IPs or private topology here.

Questions for the instructor are raised as **GitHub issues** (label `question`, mention `@nyameko`), not written into this file. Once answered, the outcome is recorded below with a link to the issue.

## Decided

| Date | Decision | Why / source |
| --- | --- | --- |
| 2026-10-05 | Questions for the instructor go in **separate GitHub issues** (label `question`), never inside commits or docs | Instructor review on #6 |
| 2026-10-05 | We **write our own** student Terraform and Ansible; the instructor provides examples, and `nyameko/infra-hpc-qc-k8s` is reference only | Instructor answer on #16 |
| 2026-10-05 | Private network CIDRs are **the team's choice** (internal private networks); proposal under review in #21 | Instructor answer on #16 |
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

- Edge-01 flavor: `large` (8 vCPU / 16 GiB) vs `medium` (4 / 8 GiB); see #8 and #19.
- Boot from image vs boot-from-volume; see #19.
- WireGuard port and allowed source ranges; bootstrap SSH source ranges; see #18.
- Internal DNS domain for Pi-hole; see #13.

## Roles

| Member | GitHub | Starting ownership |
| --- | --- | --- |
| Olerato | `Ole06` | Infrastructure deployment: OpenStack, Terraform, networking, security groups, DNS/firewall design |
| Rendani | `Rendani-Anele` | Cloud automation: Ansible, Kubernetes, Cilium, Cinder |
| Phathutshedzo (captain) | `saxs-14` | CI/CD, telemetry & security: Argo CD, Prometheus/Grafana, Wazuh, Suricata; Git workflow |
| Siyabonga | `Swaetc` | Front-end & agents: Astro, ACP/Hermes, Week-5 specialisation |

Roles rotate after major milestones; everyone should be able to explain the whole stack.
