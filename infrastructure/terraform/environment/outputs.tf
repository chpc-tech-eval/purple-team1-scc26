output "edge_floating_ip" {
  description = "The one public address (edge-01)."
  value       = openstack_networking_floatingip_v2.edge.address
}

output "fixed_ips" {
  description = "Private address per host, for the private Ansible inventory."
  value       = module.compute.fixed_ips
}

output "router_id" {
  value = module.network.router_id
}

output "security_group_ids" {
  value = module.security.group_ids
}
