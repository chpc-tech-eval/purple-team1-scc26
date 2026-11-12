output "port_ids" {
  description = "Port ID by hostname."
  value       = { for name, port in openstack_networking_port_v2.this : name => port.id }
}

output "fixed_ips" {
  description = "Fixed private IP by hostname."
  value       = { for name, port in openstack_networking_port_v2.this : name => one(port.all_fixed_ips) }
}

output "instance_ids" {
  description = "Instance ID by hostname."
  value       = { for name, instance in openstack_compute_instance_v2.this : name => instance.id }
}
