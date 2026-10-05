# Team decision log — 3NCRYP+3D

Short record of decisions and open questions. Newest first. No credentials, IPs or private topology here.

## Decided

| Date | Decision | Why / source |
| --- | --- | --- |
| 2026-10-04 | Team workstations run inside **WSL2 Ubuntu** on Windows laptops | Ansible's control node does not run natively on Windows; keeps every member on the same toolchain |
| 2026-10-04 | Workstation toolset: Git, SSH, OpenStack CLI, Terraform, Ansible, kubeseal. **No** kubectl/Helm/Argo CLI on workstations | `docs/COMMAND-LOCATIONS.md`, `week1/README.md` §0.2 |
| 2026-10-04 | Credentials live only in `~/.config/openstack` and `~/.config/scc26-secrets` (mode 700); the repo `.gitignore` blocks state, tfvars, `clouds.yaml`, keys, kubeconfigs and private inventories | `week1/README.md` §0.3, `docs/SECRETS-AND-LOCAL-FILES.md` |
| 2026-10-04 | `main` and `dev` are never committed to directly; small feature branches → PR into `dev`, instructor added as reviewer | Instructor guidance, `CONTRIBUTING.md` |
| 2026-10-04 | Sebowa team account is the **PurpleTeamB** account; this GitHub repo (`purple-team1-scc26`) is ours | Confirmed by team captain |
| 2026-10-04 | Week 1 follows `main`/`dev` (merged `feature/student-weeks-1-7`), not the superseded `feature/student-weeks-1-4` | Branch history (PR #4, #5) |
| 2026-10-04 | Week 1 edge scope is WireGuard, Pi-hole/DNS and nftables; Wazuh Manager and Suricata are added in Week 3 | `week1/README.md` §20, `week3/README.md` |

## Roles

| Member | GitHub | Starting ownership |
| --- | --- | --- |
| Olerato | `Ole06` | Infrastructure deployment: OpenStack, Terraform, networking, security groups, DNS/firewall design |
| Rendani | `Rendani-Anele` | Cloud automation: Ansible, Kubernetes, Cilium, Cinder |
| Phathutshedzo (captain) | `saxs-14` | CI/CD, telemetry & security: Argo CD, Prometheus/Grafana, Wazuh, Suricata; Git workflow |
| Siyabonga | `Swaetc` | Front-end & agents: Astro, ACP/Hermes, Week-5 specialisation |

Roles rotate after major milestones; everyone should be able to explain the whole stack.

## Open questions for the instructor

1. Will a student Terraform/Ansible starter be added to this repo, or do we write our own from the `infra-hpc-qc-k8s` reference?
2. Assigned CIDRs for the management network, Kubernetes network, WireGuard client subnet and pod network?
3. External/provider network name, and is exactly one floating IP allocated?
4. Which Rocky Linux image and bootstrap user? Which flavors match the POC sizes, and which volume types exist?
5. Where should Terraform state live (local/private vs remote backend), and what is the backup policy for the Week-6 rebuild?
6. Which source IPs may reach edge SSH/WireGuard during bootstrap? Preferred WireGuard port?
7. Internal DNS domain for Pi-hole: our choice or assigned?
8. Are Terraform ≥1.9 / OpenStack provider 3.4.0 / Kubernetes v1.36.4 / containerd 2.3.4 / Cilium 1.20.1 the frozen student baseline?
9. Week-6 paper: the email says a 2-page article, the repo says a 3–5 page IEEE paper. Which is assessed?
10. Please enable branch protection/rulesets on `main` and `dev` (captain role is `maintain` and cannot set them).
