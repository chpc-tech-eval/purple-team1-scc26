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

Waiting on the instructor (#16) for CIDRs, WireGuard/bootstrap sources, edge flavor, boot method and state location. Every one of those is a variable with **no default**, so `terraform plan` refuses to run until the real values are in the private `terraform.tfvars`.

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
