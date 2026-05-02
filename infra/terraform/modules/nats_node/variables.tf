variable "name" {
  type        = string
  description = "NATS node hostname."
}

variable "project" {
  type        = string
  description = "Project name."
}

variable "environment" {
  type        = string
  description = "Canonical environment id."
}

variable "nats_cluster_id" {
  type        = string
  description = "Canonical NATS cluster id."
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

variable "nats_version" {
  type        = string
  description = "Pinned NATS server version."
}

variable "nats_exporter_version" {
  type        = string
  description = "Pinned prometheus-nats-exporter version."
}

variable "client_port" {
  type        = number
  description = "NATS client port."
  default     = 4222
}

variable "cluster_port" {
  type        = number
  description = "NATS route cluster port."
  default     = 6222
}

variable "monitor_port" {
  type        = number
  description = "NATS local monitoring port."
  default     = 8222
}

variable "exporter_port" {
  type        = number
  description = "Prometheus NATS exporter port."
  default     = 7777
}

variable "jetstream_store_dir" {
  type        = string
  description = "Local JetStream store directory."
  default     = "/var/lib/nats/jetstream"
}

variable "jetstream_max_file_store" {
  type        = number
  description = "JetStream max file store in bytes."
  default     = 21474836480
}

variable "jetstream_max_memory_store" {
  type        = number
  description = "JetStream max memory store in bytes."
  default     = 268435456
}
