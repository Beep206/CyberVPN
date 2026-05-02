provider "hcloud" {
  token = var.hcloud_token
}

variable "hcloud_token" {
  type        = string
  description = "Hetzner Cloud API token."
  sensitive   = true
}
