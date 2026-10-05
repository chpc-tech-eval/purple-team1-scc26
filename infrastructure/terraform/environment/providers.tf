terraform {
  required_version = ">= 1.9.0"

  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.4.0"
    }
  }

  # No backend block on purpose: state stays local, on the private
  # workstation of whoever applies (instructor answer, #16). It is
  # gitignored and never goes in Git or a shared backend.
}

provider "openstack" {
  # Credentials come from ~/.config/openstack/clouds.yaml, never from this repo.
  cloud  = var.openstack_cloud
  region = var.openstack_region
}
