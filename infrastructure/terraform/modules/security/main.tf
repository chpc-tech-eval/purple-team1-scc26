# Cloud-side firewall. Rule numbers match the matrix in
# docs/network-design.md §4. Week-3 (Wazuh/metrics) rules are added in a
# later PR, never by hand in Horizon.

locals {
  groups = toset(["edge", "api-lb", "k8s-control-plane", "k8s-worker"])

  private_groups  = setsubtract(local.groups, ["edge"])
  k8s_node_groups = toset(["k8s-control-plane", "k8s-worker"])

  # Each spec has either `port` (single port), `port_min`/`port_max` (range),
  # or neither (ICMP). Normalised into `rules` below.
  rule_specs = merge(
    # --- Week 1 -----------------------------------------------------------
    # 1. Bootstrap / break-glass SSH to edge from known /32s (#13).
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

    # --- Week 2: Kubernetes + Cilium, node to node only (k8s_cidr) -----------
    # 9. etcd (stacked, control plane only).
    { "k8s-control-plane-etcd" = {
      group = "k8s-control-plane", protocol = "tcp", port_min = 2379, port_max = 2380, cidr = var.k8s_cidr
    } },
    merge([for group in local.k8s_node_groups : {
      # 10. kubelet API.
      "${group}-kubelet" = { group = group, protocol = "tcp", port = 10250, cidr = var.k8s_cidr }
      # 11. Cilium VXLAN overlay.
      "${group}-cilium-vxlan" = { group = group, protocol = "udp", port = 8472, cidr = var.k8s_cidr }
      # 12. Cilium health checks.
      "${group}-cilium-health" = { group = group, protocol = "tcp", port = 4240, cidr = var.k8s_cidr }
      # 13. ICMP for node/Cilium health.
      "${group}-icmp-k8s" = { group = group, protocol = "icmp", cidr = var.k8s_cidr }
      # 14. NodePort range, TCP and UDP.
      "${group}-nodeport-tcp" = { group = group, protocol = "tcp", port_min = 30000, port_max = 32767, cidr = var.k8s_cidr }
      "${group}-nodeport-udp" = { group = group, protocol = "udp", port_min = 30000, port_max = 32767, cidr = var.k8s_cidr }
    }]...),
    # 14a. ICMP from edge (mgmt) to the private hosts, for path debugging (#18 review).
    { for group in local.private_groups : "${group}-icmp-mgmt" => {
      group = group, protocol = "icmp", cidr = var.mgmt_cidr
    } },
    # 14b. Traefik web/websecure NodePorts on the workers from the VPN only
    # (Week-2 Part F ingress path; edge routes VPN traffic without NAT).
    {
      "k8s-worker-traefik-web-vpn"       = { group = "k8s-worker", protocol = "tcp", port = 30080, cidr = var.vpn_cidr }
      "k8s-worker-traefik-websecure-vpn" = { group = "k8s-worker", protocol = "tcp", port = 30443, cidr = var.vpn_cidr }
    },
  )

  rules = { for key, spec in local.rule_specs : key => {
    group    = spec.group
    protocol = spec.protocol
    cidr     = spec.cidr
    port_min = try(spec.port_min, spec.port, null)
    port_max = try(spec.port_max, spec.port, null)
  } }

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
  port_range_min    = each.value.port_min
  port_range_max    = each.value.port_max
  remote_ip_prefix  = each.value.cidr
  security_group_id = openstack_networking_secgroup_v2.this[each.value.group].id
}
