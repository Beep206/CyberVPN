variable "project_name" {
  type        = string
  description = "Project name."
  default     = "cybervpn"
}

variable "environment" {
  type        = string
  description = "Canonical environment name."
  default     = "nonprod"
}

variable "openbao_cluster_id" {
  type        = string
  description = "Canonical OpenBao cluster id."
  default     = "openbao-nonprod"
}

variable "aws_region" {
  type        = string
  description = "AWS region hosting the KMS seal key."
  default     = "eu-central-1"
}

variable "common_labels" {
  type        = map(string)
  description = "Additional shared labels."
  default     = {}
}

variable "foundation_state" {
  type = object({
    bucket       = string
    key          = string
    region       = string
    use_lockfile = optional(bool, true)
  })
  description = "Remote state location for the legacy staging foundation stack that owns the shared SSH key registry."
}

variable "kms_deletion_window_in_days" {
  type        = number
  description = "Deletion window for the non-prod OpenBao seal key."
  default     = 30
}

variable "firewall_name" {
  type        = string
  description = "Optional firewall name override."
  default     = null
  nullable    = true
}

variable "ssh_port" {
  type        = number
  description = "Administrative SSH port."
  default     = 22
}

variable "admin_ipv4_cidrs" {
  type        = list(string)
  description = "Administrative IPv4 CIDRs for SSH and API access."
}

variable "admin_ipv6_cidrs" {
  type        = list(string)
  description = "Administrative IPv6 CIDRs for SSH and API access."
  default     = []
}

variable "api_ipv4_cidrs" {
  type        = list(string)
  description = "Additional IPv4 CIDRs allowed to access OpenBao API/UI."
  default     = []
}

variable "api_ipv6_cidrs" {
  type        = list(string)
  description = "Additional IPv6 CIDRs allowed to access OpenBao API/UI."
  default     = []
}

variable "metrics_port" {
  type        = number
  description = "Dedicated OpenBao metrics listener port."
  default     = 9101
}

variable "metrics_ipv4_cidrs" {
  type        = list(string)
  description = "IPv4 CIDRs allowed to scrape OpenBao metrics."
  default     = []
}

variable "metrics_ipv6_cidrs" {
  type        = list(string)
  description = "IPv6 CIDRs allowed to scrape OpenBao metrics."
  default     = []
}

variable "openbao_api_port" {
  type        = number
  description = "OpenBao API/UI listener port."
  default     = 8200
}

variable "openbao_cluster_port" {
  type        = number
  description = "OpenBao cluster listener port."
  default     = 8201
}

variable "openbao_version" {
  type        = string
  description = "Pinned OpenBao version for non-prod foundation."
  default     = "2.5.2"
}

variable "openbao_nodes" {
  type = map(object({
    location                   = string
    server_type                = string
    image                      = optional(string, "ubuntu-24.04")
    admin_username             = optional(string, "cyberops")
    ssh_port                   = optional(number, 22)
    enable_backups             = optional(bool, false)
    enable_delete_protection   = optional(bool, true)
    enable_ipv6                = optional(bool, false)
    tls_common_name            = optional(string, "")
    cloud_init_authorized_keys = optional(list(string), [])
    labels                     = optional(map(string), {})
  }))
  description = "OpenBao nodes for the non-prod cluster. Baseline is a single node."
}
