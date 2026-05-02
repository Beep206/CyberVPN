variable "hcloud_token" {
  type        = string
  description = "Hetzner Cloud API token."
  sensitive   = true
  ephemeral   = true
}

provider "aws" {
  region = var.aws_region
}

provider "hcloud" {
  token = var.hcloud_token
}
