# Week-1 troubleshooting notes (real problems)

Each note is a problem the team actually hit, with its source on GitHub. Address-free.

## 1. Partial `terraform apply`: floating-IP race + Nova HTTP 408

**When:** 2026-10-05, first apply ~13:12 UTC, recovery ~13:25 UTC · **Who:** Olerato (`Ole06`), approved by the captain · **Source:** [#11 report](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/11#issuecomment-5995164129), [#11 recovery](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/11#issuecomment-5995385135)

**Symptom:** `terraform apply "tfplan"` (42 to add) ran for 34 s and exited with 2 errors. 41 of 42 resources were in state.

| Error | Cause | Fix |
| --- | --- | --- |
| `floatingip_associate.edge`: Neutron `ExternalGatewayForFloatingIPNotFound` | Race in our code: the association ran before edge-01's subnet was attached to the router | #33 adds `depends_on` (ordering only) |
| `k8s-cp-01`: Nova API **HTTP 408** while Terraform waited | Sebowa API timeout; the server itself came up ACTIVE, but Terraform marked it **tainted** | `terraform untaint` (state-only) instead of destroying a healthy server |

**What we did right:** stopped at the first error as the handoff required, verified independently with `openstack` (5 servers ACTIVE, floating IP created but unattached), and backed up state before the untaint. The new plan was exactly `1 to add, 0 to change, 0 to destroy`. It applied in 2 s, and a second `terraform plan` then gave `No changes`.

**Lesson:** a plan that is fine on paper can still race on a real cloud. Read the failure, check the cloud directly, and fix both the code (ordering) and the state (untaint) rather than re-applying blindly.

## 2. CI: `couldn't resolve module/action 'community.general.timezone'`

**When:** 2026-10-05 ~11:27 UTC · **Who:** Rendani (`Rendani-Anele`) on #23 · **Source:** [#12 ACK](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/12#issuecomment-5993508091)

**Symptom:** the `ansible-lint + syntax-check` CI job failed on #23. Syntax-check and lint passed locally, and the other 3 checks were green.

**Cause:** the CI runner only had `ansible-core`. The collections pinned in `infrastructure/ansible/requirements.yml` were never installed, so the module couldn't be resolved.

**Fix:** #20 makes CI install the declared collections before the syntax-check. After merging `dev` into the branch, CI went green.

**Lesson:** "works on my machine" is not evidence. Pin collection versions and make CI install exactly those.

## 3. Setup guide failed on a fresh WSL image: no `unzip`

**When:** 2026-10-04/05 · **Who:** Olerato and Rendani hit it; fixed by the captain · **Source:** [#7](https://github.com/chpc-tech-eval/purple-team1-scc26/issues/7), fix in #28

**Symptom:** the Terraform install step in `docs/WORKSTATION-SETUP.md` failed because fresh Ubuntu 26.04 WSL images ship without `unzip`.

**Fix:** #28 extracts the Terraform zip with Python's `zipfile`, which needs no sudo. Its follow-up commit also adds `netaddr` to the Ansible install line, which the edge firewall lockout guard (#35) needs.

**Lesson:** test setup docs on a truly fresh image. The guide now installs everything into `$HOME` with checksum checks.
