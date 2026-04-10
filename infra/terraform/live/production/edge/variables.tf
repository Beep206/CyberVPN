variable "project_name" {
  type        = string
  description = "Project name."
  default     = "cybervpn"
}

variable "environment" {
  type        = string
  description = "Environment name."
  default     = "production"
}

variable "common_labels" {
  type        = map(string)
  description = "Additional labels applied to all edge nodes."
  default     = {}
}

variable "foundation_state" {
  type = object({
    bucket       = string
    key          = string
    region       = string
    use_lockfile = optional(bool, true)
  })
  description = "Remote state location for the production foundation stack."
}

variable "edge_nodes" {
  type = map(object({
    role                       = string
    location                   = string
    server_type                = string
    image                      = optional(string, "ubuntu-24.04")
    admin_username             = optional(string, "cyberops")
    ssh_port                   = optional(number, 22)
    enable_backups             = optional(bool, false)
    enable_delete_protection   = optional(bool, true)
    enable_ipv6                = optional(bool, false)
    cloud_init_authorized_keys = optional(list(string), [])
  }))
  description = "Production edge nodes keyed by hostname."
}
