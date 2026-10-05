# Cloud-side firewall. Rule numbers match the Week-1 matrix in
# docs/network-design.md §4. Week-2 (Kubernetes/Cilium) and Week-3
# (Wazuh/metrics) rules are added in later PRs, never by hand in Horizon.

locals {
  groups = toset(["edge", "api-lb", "k8s-control-plane", "k8s-worker"])

  private_groups = setsubtract(local.groups, ["edge"])

  rules = merge(
    # 1. Temporary bootstrap SSH to edge. Emptying bootstrap_ssh_cidrs removes it.
    { for cidr in var.bootstrap_ssh_cidrs : "edge-ssh-bootstrap-${cidr}" => {
      group = "edge", protocol = "tcp", port = 22, cidr = cidr
    } },
    # 2. WireGuard.
    { for cidr in var.wireguard_allowed_cidrs : "edge-wireguard-${cidr}" => {
      group = "edge", protocol = "udp", port = var.wireguard_port, cidr = cidr
    } },
    # 3. Admin SSH to edge over the VPN.
    { "edge-ssh-vpn" = { group = "edge", protocol = "tcp", port = 22, cidr = var.vpn_cidr } },
    # 4. Pi-hole DNS from every private source.
    merge([for src, cidr in local.dns_sources : {
      "edge-dns-udp-${src}" = { group = "edge", protocol = "udp", port = 53, cidr = cidr }
      "edge-dns-tcp-${src}" = { group = "edge", protocol = "tcp", port = 53, cidr = cidr }
    }]...),
    # 5. SSH ProxyJump from edge, and 6. direct private SSH over the VPN.
    merge([for group in local.private_groups : {
      "${group}-ssh-mgmt" = { group = group, protocol = "tcp", port = 22, cidr = var.mgmt_cidr }
      "${group}-ssh-vpn"  = { group = group, protocol = "tcp", port = 22, cidr = var.vpn_cidr }
    }]...),
    # 7. Stable API endpoint, and 8. HAProxy -> kube-apiserver. No 6443 from the VPN.
    {
      "api-lb-k8s-api"            = { group = "api-lb", protocol = "tcp", port = 6443, cidr = var.k8s_cidr }
      "k8s-control-plane-k8s-api" = { group = "k8s-control-plane", protocol = "tcp", port = 6443, cidr = var.k8s_cidr }
    },
  )

  dns_sources = {
    mgmt = var.mgmt_cidr
    k8s  = var.k8s_cidr
    vpn  = var.vpn_cidr
  }
}

resource "openstack_networking_secgroup_v2" "this" {
  for_each = local.groups

  name        = "${var.name_prefix}-${each.key}"
  description = "${var.name_prefix} ${each.key} (managed by Terraform)"
}

resource "openstack_networking_secgroup_rule_v2" "this" {
  for_each = local.rules

  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = each.value.protocol
  port_range_min    = each.value.port
  port_range_max    = each.value.port
  remote_ip_prefix  = each.value.cidr
  security_group_id = openstack_networking_secgroup_v2.this[each.value.group].id
}
