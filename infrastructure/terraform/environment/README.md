# Terraform environment: five-node student POC

Declares the Sebowa infrastructure designed in [`docs/network-design.md`](../../../docs/network-design.md): two private networks, one router (with the VPN return route), four security groups with the Week-1 rules, five hosts with fixed IPs, and one floating IP on `edge-01`.

Terraform owns cloud infrastructure only. Host configuration (WireGuard, Pi-hole, nftables, HAProxy) belongs to `infrastructure/ansible`.

| Path | Contents |
| --- | --- |
| `modules/network` | mgmt + k8s networks/subnets, router, interfaces, VPN static route |
| `modules/security` | security groups and rules (Week-1 matrix) |
| `modules/compute` | ports with fixed IPs (and edge's `allowed_address_pairs`), instances |
| `environment` | this root module: providers, the five hosts, keypair, floating IP |

## Status

Decided: image `Rocky 9` with bootstrap user `rocky`, edge flavor `large`, state kept local on the applier's private workstation (#16, #22). Still being agreed: CIDRs (#21), WireGuard port and WireGuard/bootstrap SSH sources (#18), boot from image vs volume. Those are variables with **no default**, so `terraform plan` refuses to run until the real values are in the private `terraform.tfvars`.

## Usage

```bash
# RUN ON: WORKSTATION (WSL), from the repo root
cd infrastructure/terraform/environment
cp terraform.tfvars.example terraform.tfvars   # gitignored; fill in real values
chmod 600 terraform.tfvars
export OS_CLOUD=sebowa                          # ~/.config/openstack/clouds.yaml

terraform init
terraform fmt -recursive ..
terraform validate
terraform plan -out=tfplan                      # share a sanitised summary for review
```

`terraform apply tfplan` only after the team has reviewed the plan **and** the captain has approved it. Never `-auto-approve`; never `destroy` without the captain's approval.

## Never commit

`terraform.tfvars`, `*.tfstate*`, `tfplan`, `.terraform/`, `clouds.yaml`. Commit `.terraform.lock.hcl` and `terraform.tfvars.example`. The repo `.gitignore` enforces this.

## State backup (so the team is not tied to one laptop)

The state contains secrets, so it never goes to GitHub. After every apply, the state holder runs:

```bash
# RUN ON: WORKSTATION (the state holder's)
../scripts/backup-state.sh ~/.config/scc26-secrets/backup-recipients.txt edge-01
```

This encrypts `terraform.tfstate` + `terraform.tfvars` with [age](https://github.com/FiloSottile/age) to every member's SSH **public** key (the recipients file holds one per line, kept private). It keeps a copy locally and stores one root-only in `/var/backups/scc26/` on edge-01.

To take over as state holder, a member copies the newest file from edge-01 (they have sudo there) and decrypts it with their own SSH key:

```bash
age -d -i ~/.ssh/<your-key> scc26-tfstate-<stamp>.tar.age | tar x   # gives terraform.tfstate + terraform.tfvars
terraform init && terraform plan   # expect "No changes" before doing anything else
```

Only one person applies at a time. The captain announces any change of state holder in #purple-1.
