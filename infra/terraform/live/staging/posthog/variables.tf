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

variable "posthog_instance_id" {
  type        = string
  description = "Canonical PostHog instance id."
  default     = "posthog-nonprod"
}

variable "posthog_domain" {
  type        = string
  description = "Canonical PostHog DNS name for non-prod."
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
  description = "Administrative IPv4 CIDRs for SSH and protected UI access."
}

variable "admin_ipv6_cidrs" {
  type        = list(string)
  description = "Administrative IPv6 CIDRs for SSH and protected UI access."
  default     = []
}

variable "http_ipv4_cidrs" {
  type        = list(string)
  description = "IPv4 CIDRs allowed to reach PostHog HTTP/HTTPS ingress."
  default     = ["0.0.0.0/0"]
}

variable "http_ipv6_cidrs" {
  type        = list(string)
  description = "IPv6 CIDRs allowed to reach PostHog HTTP/HTTPS ingress."
  default     = ["::/0"]
}

variable "backup_retention_days" {
  type        = number
  description = "Host-local backup retention for the baseline PostHog backup timer."
  default     = 7
}

variable "posthog_nodes" {
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
  description = "PostHog nodes for the non-prod instance. Baseline is a single dedicated VM."
}
