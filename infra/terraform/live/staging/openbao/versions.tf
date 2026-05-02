terraform {
  required_version = "~> 1.11.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.60.1"
    }
  }

  backend "s3" {}
}
