variable "project_name" {
  type        = string
  description = "Project name."
  default     = "cybervpn"
}

variable "environment" {
  type        = string
  description = "Environment name."
  default     = "staging"
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
  description = "Remote state location for the staging foundation stack."
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
  description = "Administrative IPv4 CIDRs for SSH access."
}

variable "admin_ipv6_cidrs" {
  type        = list(string)
  description = "Administrative IPv6 CIDRs for SSH access."
  default     = []
}

variable "control_plane_nodes" {
  type = map(object({
    location                   = string
    server_type                = string
    image                      = optional(string, "ubuntu-24.04")
    service_roles              = optional(list(string), ["backend", "worker", "helix-adapter"])
    admin_username             = optional(string, "cyberops")
    ssh_port                   = optional(number, 22)
    enable_backups             = optional(bool, false)
    enable_delete_protection   = optional(bool, true)
    enable_ipv6                = optional(bool, false)
    cloud_init_authorized_keys = optional(list(string), [])
  }))
  description = "Control-plane nodes for staging."
}
