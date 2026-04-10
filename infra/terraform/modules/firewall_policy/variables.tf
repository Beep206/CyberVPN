variable "name" {
  type        = string
  description = "Firewall name."
}

variable "labels" {
  type        = map(string)
  description = "Labels applied to the firewall."
  default     = {}
}

variable "ssh_port" {
  type        = number
  description = "Administrative SSH port."
  default     = 22
}

variable "admin_ipv4_cidrs" {
  type        = list(string)
  description = "IPv4 CIDRs allowed to reach SSH."
  default     = []
}

variable "admin_ipv6_cidrs" {
  type        = list(string)
  description = "IPv6 CIDRs allowed to reach SSH."
  default     = []
}

variable "allow_https_tcp" {
  type        = bool
  description = "Allow TCP/443."
  default     = true
}

variable "allow_https_udp" {
  type        = bool
  description = "Allow UDP/443."
  default     = true
}

variable "metrics_port" {
  type        = number
  description = "Node metrics port."
  default     = 9100
}

variable "metrics_ipv4_cidrs" {
  type        = list(string)
  description = "IPv4 CIDRs allowed to reach node metrics."
  default     = []
}

variable "metrics_ipv6_cidrs" {
  type        = list(string)
  description = "IPv6 CIDRs allowed to reach node metrics."
  default     = []
}
