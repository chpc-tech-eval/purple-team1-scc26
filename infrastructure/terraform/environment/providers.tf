terraform {
  required_version = ">= 1.9.0"

  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.4.0"
    }
  }

  # State location is still an open question (#16 Q5). Until it is
  # answered, state stays local and private (gitignored), never in Git.
}

provider "openstack" {
  # Credentials come from ~/.config/openstack/clouds.yaml, never from this repo.
  cloud  = var.openstack_cloud
  region = var.openstack_region
}
