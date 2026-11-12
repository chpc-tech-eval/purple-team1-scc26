variable "name_prefix" {
  description = "Prefix for every OpenStack object name."
  type        = string
}

variable "mgmt_cidr" {
  description = "Management subnet."
  type        = string
}

variable "k8s_cidr" {
  description = "Kubernetes subnet."
  type        = string
}

variable "vpn_cidr" {
  description = "WireGuard client subnet."
  type        = string
}

variable "wireguard_port" {
  description = "UDP port WireGuard listens on at edge-01."
  type        = number

  validation {
    condition     = var.wireguard_port >= 1 && var.wireguard_port <= 65535
    error_message = "wireguard_port must be a real UDP port (the example file's 0 is a placeholder)."
  }
}

variable "wireguard_allowed_cidrs" {
  description = "Sources allowed to reach WireGuard on edge-01."
  type        = list(string)
}

variable "bootstrap_ssh_cidrs" {
  description = "Sources allowed temporary public SSH to edge-01. Set to [] to remove the rule once WireGuard access is proven (#13)."
  type        = list(string)

  validation {
    condition     = !contains(var.bootstrap_ssh_cidrs, "0.0.0.0/0")
    error_message = "Bootstrap SSH must not be open to 0.0.0.0/0; list specific sources (docs/network-design.md §4 rule 1)."
  }
}
