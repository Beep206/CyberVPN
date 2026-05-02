terraform {
  required_version = "~> 1.11.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.60.1"
    }

    talos = {
      source  = "siderolabs/talos"
      version = "~> 0.10.1"
    }
  }

  backend "s3" {}
}
