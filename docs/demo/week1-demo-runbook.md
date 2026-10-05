# Friday demo: Week-1 runbook (#25)

Agenda and owners are on #25. This file is the **exact sequence of safe, read-only commands** each presenter runs live, so the demo is repeatable and nothing sensitive reaches the screen.

## Before you share your screen

- [ ] VPN up (`sudo wg show` shows a recent handshake), terminal font enlarged.
- [ ] `export OS_CLOUD=sebowa`; `clouds.yaml`, tfvars, inventories and Vault files **closed**. Never `cat` them on screen.
- [ ] **After step 3 (public SSH removed), use the post-VPN private inventory:** `edge-01` at its mgmt address, and the `private_nodes` ProxyJump file deleted (see `infrastructure/ansible/README.md`). Check with `ansible all -i inventories/private/hosts.yml -m ping -o` before the demo.
- [ ] Use host **names**, not addresses, in every command. Commands that print addresses are marked ⚠️: run them **off-screen** or pipe them as shown.
- [ ] Fallback: screenshots or recordings from `evidence/week1/` ready in a browser tab in case Sebowa or the network misbehaves.
- [ ] `dev` SHA noted for the reproducibility slide: `git rev-parse --short origin/dev`.

## 1. Architecture (Olerato, ~10 min)

Show `evidence/week1/diagrams/trust-boundary.png` and `docs/network-design.md` §2–4: one floating IP on edge-01, routed VPN with no NAT, the security-group matrix, why `large` for edge.

## 2. OpenStack → Terraform (Olerato, ~10 min)

```bash
# RUN ON: WORKSTATION, in infrastructure/terraform/environment
terraform version
terraform validate
terraform plan -input=false | tail -n 3        # expect: No changes.
openstack server list -c Name -c Status -c Flavor
openstack security group list -c Name | grep 3ncryp3d
openstack floating ip list -f value -c ID | wc -l   # count only ⚠️ never print the address
```

Talking points: plan reviewed before apply (42/0/0), the real partial-apply failure and the fix (#33 + untaint), second plan shows no drift.

## 3. Ansible (Rendani or Olerato, ~12 min)

```bash
# RUN ON: WORKSTATION, in infrastructure/ansible
ansible-inventory -i inventories/private/hosts.yml --graph   # names only
ansible all -i inventories/private/hosts.yml -m ping -o | sed -E 's/[0-9]+(\.[0-9]+){3}/<addr>/g'
ansible-playbook -i inventories/private/hosts.yml playbooks/bootstrap.yml | tail -n 8   # expect changed=0
ansible all -i inventories/private/hosts.yml -b -m shell \
  -a 'timedatectl show -p Timezone --value; getenforce' -o | sed -E 's/[0-9]+(\.[0-9]+){3}/<addr>/g'
```

Then the edge and HAProxy checks over the VPN:

```bash
# RUN ON: edge-01
sudo wg show | grep -E 'interface|listening port|latest handshake'   # no keys or endpoints on screen
sudo nft list table inet scc26_edge | sed -E 's/[0-9]+(\.[0-9]+){3}(\/[0-9]+)?/<addr>/g' | head -n 25   # the named sets hold real ranges: always redact
systemctl --failed --no-pager
# RUN ON: api-lb-01
sudo haproxy -c -f /etc/haproxy/haproxy.cfg && systemctl is-active haproxy && getenforce
sudo ss -lntp | grep ':6443'
```

## 4. Security and DevOps (Phathutshedzo, ~8 min)

- A PR with the 4 green checks (gitleaks, yamllint, Terraform, Ansible) and branch protection on `dev`/`main`.
- The PR, review and merge flow; questions raised as issues; no real network details on GitHub.
- Live: private SSH over WireGuard, then show that public SSH is gone from the security group:
```bash
# RUN ON: WORKSTATION
openstack security group rule list 3ncryp3d-edge --ingress -c "IP Protocol" -c "Port Range" -c "IP Range" \
  | sed -E 's#0\.0\.0\.0/0#ANYWHERE#; s/[0-9]+(\.[0-9]+){3}\/[0-9]+/<range>/g'
```

## 5. Evidence and next steps (Siyabonga, ~7 min)

`evidence/week1/README.md` (acceptance ladder, all rows linked) and `troubleshooting.md` (three real problems), then a one-slide outlook for Weeks 2–4.

## 6. Lessons and Q&A (all, ~8 min)

Real problems: floating-IP race + Nova 408, CI collections, `unzip`, `netaddr`. What we'd automate next.
