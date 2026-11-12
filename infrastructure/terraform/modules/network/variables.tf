variable "name_prefix" {
  description = "Prefix for every OpenStack object name."
  type        = string
}

variable "external_network_name" {
  description = "Provider network that the router uses as its gateway."
  type        = string
}

variable "mgmt_cidr" {
  description = "Management subnet (edge-01)."
  type        = string
}

variable "mgmt_gateway_ip" {
  description = "Router address on the management subnet."
  type        = string
}

variable "mgmt_pool_start" {
  description = "First DHCP address on the management subnet."
  type        = string
}

variable "mgmt_pool_end" {
  description = "Last DHCP address on the management subnet."
  type        = string
}

variable "k8s_cidr" {
  description = "Kubernetes subnet (api-lb, control plane, workers)."
  type        = string
}

variable "k8s_gateway_ip" {
  description = "Router address on the Kubernetes subnet."
  type        = string
}

variable "k8s_pool_start" {
  description = "First DHCP address on the Kubernetes subnet."
  type        = string
}

variable "k8s_pool_end" {
  description = "Last DHCP address on the Kubernetes subnet."
  type        = string
}

variable "dns_nameservers" {
  description = "Resolvers advertised by Neutron DHCP. See docs/network-design.md open item 3."
  type        = list(string)
}

variable "vpn_cidr" {
  description = "WireGuard client subnet routed back through edge-01."
  type        = string
}

variable "vpn_next_hop" {
  description = "edge-01 fixed address on the management subnet."
  type        = string
}
