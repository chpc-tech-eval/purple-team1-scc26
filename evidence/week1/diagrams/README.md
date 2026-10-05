# Week-1 architecture / trust-boundary diagram

Editable source: [`trust-boundary.mmd`](trust-boundary.mmd) (Mermaid). The block below is a copy of it so GitHub renders it inline; edit the `.mmd` file first, then copy it here.

Design source: [`docs/network-design.md`](../../../docs/network-design.md) (#18, follow-up #26). SG rule numbers refer to the matrix in §4 of that doc.

**Address-free (instructor rule on #23):** only Terraform variable names (`mgmt_cidr`, `k8s_cidr`, `vpn_cidr`, `bootstrap_ssh_cidrs`, `wireguard_port`) appear. Real values live in the private `terraform.tfvars` and Discord #purple-1 only.

```mermaid
flowchart TB
    subgraph Z0["Zone: Internet (untrusted)"]
        ws["Team workstation<br/>WireGuard client in vpn_cidr"]
        boot["Bootstrap workstation<br/>(single source in bootstrap_ssh_cidrs)"]
    end

    ext(("Sebowa external network<br/>&quot;Public Internet&quot;"))

    ws -- "WireGuard UDP wireguard_port<br/>(SG rule 2, steady-state admin path)" --> ext
    boot -. "temporary bootstrap SSH 22/tcp<br/>(SG rule 1, removed after WireGuard proof)" .-> ext
    ext -- "1 floating IP<br/>(quota = 1)" --> edge

    subgraph CLOUD["Team OpenStack project (Terraform-owned)"]
        router["Router: SNAT to Public Internet<br/>static route vpn_cidr -> edge-01 mgmt IP"]

        subgraph Z1["Zone: mgmt network (mgmt_cidr)"]
            edge["edge-01 (large)<br/>WireGuard | Pi-hole DNS | nftables<br/>SG: prefix-edge"]
        end

        subgraph Z2["Zone: k8s network (k8s_cidr), no floating IPs"]
            lb["api-lb-01 (small)<br/>HAProxy :6443<br/>SG: prefix-api-lb"]
            cp["k8s-cp-01 (medium)<br/>SG: prefix-k8s-control-plane"]
            w1["k8s-worker-01 (scc.large)<br/>SG: prefix-k8s-worker"]
            w2["k8s-worker-02 (scc.large)<br/>SG: prefix-k8s-worker"]
        end
    end

    edge --- router
    router --- lb & cp & w1 & w2
    edge -- "routed VPN traffic, no NAT<br/>SSH 22/tcp from vpn_cidr (rule 6)<br/>ProxyJump from mgmt_cidr (rule 5)" --> cp
    lb -- "6443/tcp from k8s_cidr (rule 8)" --> cp
```

## What the diagram claims (and where it is proven)

| Claim | Evidence |
| --- | --- |
| Only `edge-01` has a floating IP; exactly 1 exists | #11 apply/verification (Ole06, 2026-10-05 13:25 UTC); captain re-check 13:41 UTC |
| Only WireGuard UDP is open to anywhere; bootstrap SSH is a single source | captain verification on #11, 2026-10-05 13:41 UTC |
| VPN return path: router static route + `allowed_address_pairs` on edge port | #11 verification: 1 static route, 1 address pair |
| 4 security groups, 17 ingress rules | #11 verification; matches the #18 Week-1 matrix |
| No 6443 from `vpn_cidr`; `kubectl` runs on `k8s-cp-01` only | `docs/network-design.md` §4, `docs/COMMAND-LOCATIONS.md` |
| WireGuard admin path works | **pending**: #13 (roles merged in #27/#35, not yet applied) |

## Re-rendering an image export

GitHub renders the Mermaid block above directly, so no image is committed yet. To export an SVG/PNG (e.g. for the Friday demo slides, #25):

```bash
# RUN ON: WORKSTATION (needs Node.js)
npx -y @mermaid-js/mermaid-cli -i trust-boundary.mmd -o trust-boundary.svg
```

Commit any export next to the `.mmd` source so it stays editable.
