variable "name" {
  type        = string
  description = "Talos node hostname."
}

variable "project" {
  type        = string
  description = "Project name."
}

variable "environment" {
  type        = string
  description = "Canonical environment id."
}

variable "management_cluster_id" {
  type        = string
  description = "Canonical management cluster id."
}

variable "node_role" {
  type        = string
  description = "Talos node role, for example control-plane or worker."
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
  description = "Hetzner image or snapshot used to boot Talos."
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

variable "user_data" {
  type        = string
  description = "Optional user-data payload. Talos nodes normally leave this empty."
  default     = ""
}

variable "existing_primary_ip_id" {
  type        = number
  description = "Optional pre-created primary IPv4 ID to attach instead of creating a new one."
  default     = null
  nullable    = true
}

variable "existing_primary_ip_address" {
  type        = string
  description = "Optional pre-created primary IPv4 address paired with existing_primary_ip_id."
  default     = null
  nullable    = true
}
