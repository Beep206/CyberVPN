variable "name" {
  type        = string
  description = "OpenBao node hostname."
}

variable "project" {
  type        = string
  description = "Project name."
}

variable "environment" {
  type        = string
  description = "Canonical environment id."
}

variable "openbao_cluster_id" {
  type        = string
  description = "Canonical OpenBao cluster id, for example openbao-nonprod."
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

variable "openbao_version" {
  type        = string
  description = "OpenBao version installed by cloud-init."
}

variable "kms_key_alias" {
  type        = string
  description = "AWS KMS alias consumed by auto-unseal."
}

variable "aws_region" {
  type        = string
  description = "AWS region for the KMS key."
}

variable "api_port" {
  type        = number
  description = "OpenBao API/UI listener port."
  default     = 8200
}

variable "cluster_port" {
  type        = number
  description = "OpenBao cluster listener port."
  default     = 8201
}

variable "metrics_port" {
  type        = number
  description = "Dedicated Prometheus metrics listener port."
  default     = 9101
}

variable "tls_common_name" {
  type        = string
  description = "Preferred TLS common name for the self-signed bootstrap certificate."
  default     = ""
}

variable "retry_join_api_addrs" {
  type        = list(string)
  description = "Additional OpenBao API addresses used in retry_join stanzas."
  default     = []
}
