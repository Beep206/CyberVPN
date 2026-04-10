variable "hcloud_token" {
  type        = string
  description = "Hetzner Cloud API token."
  sensitive   = true
}

provider "hcloud" {
  token = var.hcloud_token
}
