# Five-node student POC on Sebowa. Design: docs/network-design.md.

data "openstack_images_image_v2" "base" {
  name        = var.image_name
  most_recent = true
}

module "network" {
  source = "../modules/network"

  name_prefix           = var.name_prefix
  external_network_name = var.external_network_name
  mgmt_cidr             = var.mgmt_cidr
  mgmt_gateway_ip       = var.mgmt_gateway_ip
  mgmt_pool_start       = var.mgmt_pool_start
  mgmt_pool_end         = var.mgmt_pool_end
  k8s_cidr              = var.k8s_cidr
  k8s_gateway_ip        = var.k8s_gateway_ip
  k8s_pool_start        = var.k8s_pool_start
  k8s_pool_end          = var.k8s_pool_end
  dns_nameservers       = var.dns_nameservers
  vpn_cidr              = var.vpn_cidr
  vpn_next_hop          = var.node_fixed_ips["edge-01"]
}

module "security" {
  source = "../modules/security"

  name_prefix             = var.name_prefix
  mgmt_cidr               = var.mgmt_cidr
  k8s_cidr                = var.k8s_cidr
  vpn_cidr                = var.vpn_cidr
  wireguard_port          = var.wireguard_port
  wireguard_allowed_cidrs = var.wireguard_allowed_cidrs
  bootstrap_ssh_cidrs     = var.bootstrap_ssh_cidrs
}

resource "openstack_compute_keypair_v2" "admin" {
  name       = "${var.name_prefix}-admin"
  public_key = var.admin_ssh_public_key
}

locals {
  mgmt = {
    network_id = module.network.mgmt_network_id
    subnet_id  = module.network.mgmt_subnet_id
  }
  k8s = {
    network_id = module.network.k8s_network_id
    subnet_id  = module.network.k8s_subnet_id
  }

  # Exactly five hosts. Adding one here is an architecture change: update
  # docs/network-design.md and get it reviewed first.
  nodes = {
    "edge-01" = merge(local.mgmt, {
      flavor_name           = var.flavors["edge"]
      security_group_ids    = [module.security.group_ids["edge"]]
      allowed_address_pairs = [var.vpn_cidr]
    })
    "api-lb-01" = merge(local.k8s, {
      flavor_name        = var.flavors["api_lb"]
      security_group_ids = [module.security.group_ids["api-lb"]]
    })
    "k8s-cp-01" = merge(local.k8s, {
      flavor_name        = var.flavors["control_plane"]
      security_group_ids = [module.security.group_ids["k8s-control-plane"]]
    })
    "k8s-worker-01" = merge(local.k8s, {
      flavor_name        = var.flavors["worker"]
      security_group_ids = [module.security.group_ids["k8s-worker"]]
    })
    "k8s-worker-02" = merge(local.k8s, {
      flavor_name        = var.flavors["worker"]
      security_group_ids = [module.security.group_ids["k8s-worker"]]
    })
  }
}

module "compute" {
  source = "../modules/compute"

  image_id = data.openstack_images_image_v2.base.id
  key_pair = openstack_compute_keypair_v2.admin.name

  nodes = {
    for name, node in local.nodes : name => merge(node, {
      fixed_ip         = var.node_fixed_ips[name]
      boot_volume_size = var.boot_volume_size
      boot_volume_type = var.boot_volume_type
    })
  }
}

# The project's only floating IP (quota = 1), on edge-01.
resource "openstack_networking_floatingip_v2" "edge" {
  pool        = var.external_network_name
  description = "${var.name_prefix} edge-01"
}

resource "openstack_networking_floatingip_associate_v2" "edge" {
  floating_ip = openstack_networking_floatingip_v2.edge.address
  port_id     = module.compute.port_ids["edge-01"]

  # Neutron refuses the association until edge-01's subnet is attached to
  # the router that has the external gateway (ExternalGatewayForFloatingIPNotFound).
  # Nothing else orders these, so wait for the whole network module.
  depends_on = [module.network]
}
