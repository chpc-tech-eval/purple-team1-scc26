# Ansible: host configuration

Owner: Rendani (`Rendani-Anele`). Answers *how should the Linux machines and bootstrap services be configured?* (`week1/README.md` Part E).

```text
ansible.cfg                       defaults (private inventory, accept-new host keys)
requirements.yml                  pinned collections (CI installs these)
inventories/example/              committed placeholders; copy to inventories/private/ (gitignored)
playbooks/bootstrap.yml           all hosts: SELinux check, base packages, chrony, Africa/Johannesburg, sshd hardening
playbooks/edge.yml                edge-01: WireGuard, Pi-hole, nftables (#13)
playbooks/api-lb.yml              api-lb-01: HAProxy :6443 (#14)
roles/common/                     Week-1 host fundamentals used by bootstrap.yml
```

## First-time setup

```bash
# RUN ON: WORKSTATION (WSL), from infrastructure/ansible
ansible-galaxy collection install -r requirements.yml -p ~/.ansible/collections
mkdir -p inventories/private
cp -r inventories/example/. inventories/private/
# edit inventories/private/hosts.yml with addresses from `terraform output`
```

The real inventory never goes in Git. Private hosts are reached through `edge-01` with `ProxyJump` (`group_vars/private_nodes.yml`) until WireGuard works.

> If the repo sits under `/mnt/c/...` in WSL, Ansible ignores `./ansible.cfg` because the directory is world-writable. Run `export ANSIBLE_CONFIG=$PWD/ansible.cfg` first, or clone into your WSL home.

## Checks (same as CI, no hosts needed)

```bash
# RUN ON: WORKSTATION
ansible-inventory -i inventories/example/hosts.yml --graph
for pb in playbooks/*.yml; do ansible-playbook -i inventories/example/hosts.yml "$pb" --syntax-check; done
ansible-lint
```

## Running against real hosts

Only once the VMs exist **and** the captain has approved it in a `HANDOFF` on GitHub. Order (`week1/README.md` §14–24):

1. `ansible-inventory --graph` / `--host <name>` against the private inventory
2. `ansible all -m ping`
3. `--syntax-check`
4. `ansible-playbook playbooks/bootstrap.yml`, then run it again and expect `changed=0`
5. `ansible-playbook playbooks/edge.yml --tags wireguard,pihole,firewall`, then the WireGuard proof
6. `ansible-playbook playbooks/api-lb.yml`

Never disable SELinux or firewalls to make something work. WireGuard private keys stay on their hosts.
