# Values marked UNKNOWN in docs/network-design.md §5 have no default on
# purpose: Terraform must refuse to plan until the real value is supplied
# in the private terraform.tfvars.

# --- Cloud ---

variable "openstack_cloud" {
  description = "Cloud name in ~/.config/openstack/clouds.yaml."
  type        = string
}

variable "openstack_region" {
  description = "OpenStack region."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for every OpenStack object name."
  type        = string
}

variable "external_network_name" {
  description = "Provider network for the router gateway and the floating IP."
  type        = string
}

# --- Networks (docs/network-design.md §1, §5) ---

variable "mgmt_cidr" {
  type = string
}

variable "mgmt_gateway_ip" {
  type = string
}

variable "mgmt_pool_start" {
  type = string
}

variable "mgmt_pool_end" {
  type = string
}

variable "k8s_cidr" {
  type = string
}

variable "k8s_gateway_ip" {
  type = string
}

variable "k8s_pool_start" {
  type = string
}

variable "k8s_pool_end" {
  type = string
}

variable "vpn_cidr" {
  description = "WireGuard client subnet."
  type        = string
}

variable "dns_nameservers" {
  description = "Resolvers advertised by Neutron DHCP."
  type        = list(string)
}

variable "node_fixed_ips" {
  description = "Fixed private IP per host, inside its subnet but outside the DHCP pool."
  type        = map(string)

  validation {
    condition = alltrue([
      for host in ["edge-01", "api-lb-01", "k8s-cp-01", "k8s-worker-01", "k8s-worker-02"] :
      contains(keys(var.node_fixed_ips), host)
    ])
    error_message = "node_fixed_ips needs an entry for each of the five hosts."
  }
}

# --- Edge exposure (docs/network-design.md §4 rules 1-2) ---

variable "wireguard_port" {
  type = number
}

variable "wireguard_allowed_cidrs" {
  type = list(string)
}

variable "bootstrap_ssh_cidrs" {
  description = "Temporary public SSH sources for edge-01. Set to [] only after WireGuard access is proven (#13)."
  type        = list(string)
}

# --- Compute ---

variable "image_name" {
  description = "Exact Glance image name (Rocky 9 course baseline)."
  type        = string
}

variable "flavors" {
  description = "Flavor name per role: edge, api_lb, control_plane, worker."
  type        = map(string)

  validation {
    condition = alltrue([
      for role in ["edge", "api_lb", "control_plane", "worker"] : contains(keys(var.flavors), role)
    ])
    error_message = "flavors needs edge, api_lb, control_plane and worker."
  }
}

variable "boot_volume_size" {
  description = "Boot-from-volume size in GB for every host, or null to boot from the image (decision pending)."
  type        = number
}

variable "boot_volume_type" {
  description = "Cinder volume type for boot volumes, or null for the default. Ignored when booting from the image."
  type        = string
}

variable "admin_ssh_public_key" {
  description = "Team admin SSH PUBLIC key. Never put a private key here."
  type        = string
}
