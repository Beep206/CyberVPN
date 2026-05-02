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

variable "nats_cluster_id" {
  type        = string
  description = "Canonical NATS cluster id."
  default     = "nats-nonprod"
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
  description = "Administrative IPv4 CIDRs for SSH access and bootstrap recovery."
}

variable "admin_ipv6_cidrs" {
  type        = list(string)
  description = "Administrative IPv6 CIDRs for SSH access and bootstrap recovery."
  default     = []
}

variable "client_ipv4_cidrs" {
  type        = list(string)
  description = "IPv4 CIDRs allowed to connect to the NATS client port."
  default     = []
}

variable "client_ipv6_cidrs" {
  type        = list(string)
  description = "IPv6 CIDRs allowed to connect to the NATS client port."
  default     = []
}

variable "metrics_ipv4_cidrs" {
  type        = list(string)
  description = "IPv4 CIDRs allowed to scrape the Prometheus NATS exporter."
  default     = []
}

variable "metrics_ipv6_cidrs" {
  type        = list(string)
  description = "IPv6 CIDRs allowed to scrape the Prometheus NATS exporter."
  default     = []
}

variable "nats_client_port" {
  type        = number
  description = "NATS client port."
  default     = 4222
}

variable "nats_cluster_port" {
  type        = number
  description = "NATS route cluster port."
  default     = 6222
}

variable "nats_monitor_port" {
  type        = number
  description = "Local NATS monitoring port."
  default     = 8222
}

variable "nats_exporter_port" {
  type        = number
  description = "Prometheus NATS exporter port."
  default     = 7777
}

variable "nats_version" {
  type        = string
  description = "Pinned NATS server version."
  default     = "2.12.7"
}

variable "nats_exporter_version" {
  type        = string
  description = "Pinned prometheus-nats-exporter version."
  default     = "0.18.0"
}

variable "jetstream_max_file_store" {
  type        = number
  description = "JetStream max file store in bytes per node."
  default     = 21474836480
}

variable "jetstream_max_memory_store" {
  type        = number
  description = "JetStream max memory store in bytes per node."
  default     = 268435456
}

variable "nats_nodes" {
  type = map(object({
    location                   = string
    server_type                = string
    image                      = optional(string, "ubuntu-24.04")
    admin_username             = optional(string, "cyberops")
    ssh_port                   = optional(number, 22)
    enable_backups             = optional(bool, false)
    enable_delete_protection   = optional(bool, true)
    enable_ipv6                = optional(bool, false)
    cloud_init_authorized_keys = optional(list(string), [])
    labels                     = optional(map(string), {})
  }))
  description = "NATS nodes for the shared non-prod cluster. Baseline is a 3-node JetStream cluster."
}
