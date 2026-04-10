terraform {
  required_version = "~> 1.14.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = ">= 1.60.1, < 2.0"
    }
  }

  backend "s3" {}
}
