variable "image_id" {
  description = "Glance image ID for every host (Rocky 9 course baseline)."
  type        = string
}

variable "key_pair" {
  description = "Nova keypair injected for the bootstrap user."
  type        = string
}

variable "nodes" {
  description = "Hosts keyed by hostname."
  type = map(object({
    flavor_name           = string
    network_id            = string
    subnet_id             = string
    fixed_ip              = string
    security_group_ids    = list(string)
    allowed_address_pairs = optional(list(string), [])
    boot_volume_size      = optional(number)
    boot_volume_type      = optional(string)
  }))
}
