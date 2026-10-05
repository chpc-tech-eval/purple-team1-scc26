# Ansible: host configuration

Owner: Rendani (`Rendani-Anele`). Answers *how should the Linux machines and bootstrap services be configured?* (`week1/README.md` Part E).

```text
ansible.cfg                       defaults (private inventory, accept-new host keys)
requirements.yml                  pinned collections (CI installs these)
inventories/example/              committed placeholders; copy to inventories/private/ (gitignored)
playbooks/bootstrap.yml           all hosts: SELinux check, base packages, chrony, Africa/Johannesburg, sshd hardening
playbooks/edge.yml                edge-01: nftables, WireGuard, Pi-hole (#13), tags firewall/wireguard/pihole
playbooks/api-lb.yml              api-lb-01: HAProxy :6443 (#14)
roles/common/                     Week-1 host fundamentals used by bootstrap.yml
roles/firewall/                   edge nftables: own table, routed VPN (no NAT), DNS/SSH/WireGuard only
roles/wireguard/                  edge WireGuard; private key generated on edge-01, never read back
roles/pihole/                     edge Pi-hole as a Podman Quadlet, image pinned by tag + digest
```

## First-time setup

```bash
# RUN ON: WORKSTATION (WSL), from infrastructure/ansible
ansible-galaxy collection install -r requirements.yml -p ~/.ansible/collections
uv tool install --python 3.12 --with ansible-core==2.21.4 --with netaddr --with-executables-from ansible-core ansible --force  # netaddr: edge lockout guard
mkdir -p inventories/private
cp inventories/example/hosts.yml inventories/private/hosts.yml
# edit inventories/private/hosts.yml with addresses from `terraform output`
```

The real inventory and its `group_vars/` never go in Git.

### Private inventory: reaching hosts behind the edge

Until WireGuard works (#13), private hosts are reached through `edge-01`. Create this file **only in the private inventory**:

```yaml
# inventories/private/group_vars/private_nodes.yml  (gitignored)
ansible_ssh_common_args: >-
  -o ProxyJump={{ hostvars['edge-01'].ansible_user }}@{{ hostvars['edge-01'].ansible_host }}
```

Check it resolved with `ansible-inventory -i inventories/private/hosts.yml --host k8s-cp-01`. Once WireGuard routes the private networks, delete the file.

### Private inventory: edge variables (#13)

The edge roles have **no defaults** for anything environment-specific and stop if a value is missing. Put them in `inventories/private/group_vars/edge_nodes.yml` (gitignored); the UI password goes in Ansible Vault. Shape only, every value is a placeholder:

```yaml
# inventories/private/group_vars/edge_nodes.yml  (gitignored)
firewall_ssh_cidrs: ["<bootstrap-ssh-source>", "<vpn_cidr>"]
firewall_dns_cidrs: ["<mgmt_cidr>", "<k8s_cidr>", "<vpn_cidr>"]
firewall_vpn_cidr: "<vpn_cidr>"
firewall_private_cidrs: ["<mgmt_cidr>", "<k8s_cidr>"]
firewall_wireguard_port: "<wireguard-port>"

wireguard_port: "<wireguard-port>"
wireguard_server_address: "<first-vpn-address>/<prefix>"
wireguard_peers:            # PUBLIC keys only; each member keeps their private key
  - {name: "<member>", public_key: "<member-public-key>", allowed_ips: "<member-vpn-address>/32"}

pihole_local_domain: "<internal-domain>"
pihole_dns_upstreams: ["<upstream-resolver>"]
pihole_dns_hosts: ["<private-ip> <host>.<internal-domain> <host>"]
pihole_web_password: "{{ vault_pihole_web_password }}"
```

Edge stays NAT-free for VPN traffic (`docs/network-design.md` §3, option A). If `firewalld` is running on edge, the firewall role stops rather than disabling it; agree the swap on #13 first.

> If the repo sits under `/mnt/c/...` in WSL, Ansible ignores `./ansible.cfg` because the directory is world-writable. Run `export ANSIBLE_CONFIG=$PWD/ansible.cfg` first, or clone into your WSL home.

## CI-only checks (fake example inventory, no hosts)

The example inventory exists only so CI can run `--syntax-check`; its addresses are fake. Never point a real run at it.

```bash
# RUN ON: WORKSTATION
ansible-inventory -i inventories/example/hosts.yml --graph
for pb in playbooks/*.yml; do ansible-playbook -i inventories/example/hosts.yml "$pb" --syntax-check; done
ansible-lint
```

## Running against real hosts (private inventory)

Only once the VMs exist **and** the captain has approved it in a `HANDOFF` on GitHub. Every real command uses the private inventory (`week1/README.md` §14–24):

```bash
# RUN ON: WORKSTATION, from infrastructure/ansible
INV=inventories/private/hosts.yml
ansible-inventory -i $INV --graph
ansible-inventory -i $INV --host k8s-cp-01
ansible all -i $INV -m ping
for pb in playbooks/*.yml; do ansible-playbook -i $INV "$pb" --syntax-check; done
ansible-playbook -i $INV playbooks/bootstrap.yml
ansible-playbook -i $INV playbooks/bootstrap.yml          # re-run: expect changed=0
ansible-playbook -i $INV playbooks/edge.yml --tags wireguard,pihole,firewall
# WireGuard private-access proof (#13) before any public SSH change
ansible-playbook -i $INV playbooks/api-lb.yml
```

Never disable SELinux or firewalls to make something work. WireGuard private keys stay on their hosts. Real addresses, ranges and `terraform output` never go in Git, issues or PRs.
