# One port with a fixed IP per host, then the instance on that port.
# boot_volume_size = null boots from the image (local root disk);
# a number boots from a new Cinder volume. Decision pending (#8, #16).

resource "openstack_networking_port_v2" "this" {
  for_each = var.nodes

  name               = "${each.key}-port"
  network_id         = each.value.network_id
  security_group_ids = each.value.security_group_ids
  admin_state_up     = true

  fixed_ip {
    subnet_id  = each.value.subnet_id
    ip_address = each.value.fixed_ip
  }

  # Lets edge-01 forward WireGuard client traffic without NAT
  # (docs/network-design.md §3, option A).
  dynamic "allowed_address_pairs" {
    for_each = each.value.allowed_address_pairs
    content {
      ip_address = allowed_address_pairs.value
    }
  }
}

resource "openstack_compute_instance_v2" "this" {
  for_each = var.nodes

  name         = each.key
  flavor_name  = each.value.flavor_name
  image_id     = each.value.boot_volume_size == null ? var.image_id : null
  key_pair     = var.key_pair
  config_drive = true

  dynamic "block_device" {
    for_each = each.value.boot_volume_size == null ? [] : [each.value.boot_volume_size]
    content {
      uuid                  = var.image_id
      source_type           = "image"
      destination_type      = "volume"
      boot_index            = 0
      volume_size           = block_device.value
      volume_type           = each.value.boot_volume_type
      delete_on_termination = true
    }
  }

  network {
    port = openstack_networking_port_v2.this[each.key].id
  }
}
