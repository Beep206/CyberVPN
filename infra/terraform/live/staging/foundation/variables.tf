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

variable "edge_metrics_port" {
  type        = number
  description = "Metrics port allowed on edge nodes."
  default     = 9100
}

variable "edge_metrics_ipv4_cidrs" {
  type        = list(string)
  description = "IPv4 CIDRs allowed to scrape edge metrics."
  default     = []
}

variable "edge_metrics_ipv6_cidrs" {
  type        = list(string)
  description = "IPv6 CIDRs allowed to scrape edge metrics."
  default     = []
}

variable "ssh_keys" {
  type = map(object({
    public_key = string
    labels     = optional(map(string), {})
  }))
  description = "SSH public keys registered in Hetzner for staging."
}
