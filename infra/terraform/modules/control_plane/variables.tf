variable "name" {
  type        = string
  description = "Control-plane hostname."
}

variable "project" {
  type        = string
  description = "Project name."
}

variable "environment" {
  type        = string
  description = "Environment name."
}

variable "location" {
  type        = string
  description = "Hetzner location."
}

variable "server_type" {
  type        = string
  description = "Hetzner server type."
}

variable "image" {
  type        = string
  description = "Hetzner image slug."
  default     = "ubuntu-24.04"
}

variable "ssh_keys" {
  type        = list(string)
  description = "Hetzner SSH key IDs or names to inject."
  default     = []
}

variable "firewall_ids" {
  type        = list(number)
  description = "Hetzner firewall IDs attached on creation."
  default     = []
}

variable "labels" {
  type        = map(string)
  description = "Additional labels."
  default     = {}
}

variable "service_roles" {
  type        = list(string)
  description = "Service workloads assigned to this host."
  default     = []
}

variable "admin_username" {
  type        = string
  description = "Bootstrap admin username."
  default     = "cyberops"
}

variable "ssh_port" {
  type        = number
  description = "Bootstrap SSH port."
  default     = 22
}

variable "cloud_init_authorized_keys" {
  type        = list(string)
  description = "Extra SSH public keys written by cloud-init."
  default     = []
}

variable "enable_backups" {
  type        = bool
  description = "Enable Hetzner backups."
  default     = false
}

variable "enable_delete_protection" {
  type        = bool
  description = "Enable delete and rebuild protection."
  default     = true
}

variable "enable_ipv6" {
  type        = bool
  description = "Enable IPv6 on the public network."
  default     = false
}
