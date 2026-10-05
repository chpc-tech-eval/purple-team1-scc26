output "group_ids" {
  description = "Security group ID by role: edge, api-lb, k8s-control-plane, k8s-worker."
  value       = { for name, group in openstack_networking_secgroup_v2.this : name => group.id }
}
