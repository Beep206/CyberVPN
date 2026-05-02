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

variable "management_cluster_id" {
  type        = string
  description = "Canonical management cluster id."
  default     = "nonprod-mgmt"
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

variable "admin_ipv4_cidrs" {
  type        = list(string)
  description = "Administrative IPv4 CIDRs allowed to reach the Talos API and Kubernetes API."
}

variable "admin_ipv6_cidrs" {
  type        = list(string)
  description = "Administrative IPv6 CIDRs allowed to reach the Talos API and Kubernetes API."
  default     = []
}

variable "kubernetes_api_port" {
  type        = number
  description = "Kubernetes API listener port."
  default     = 6443
}

variable "talos_api_port" {
  type        = number
  description = "Talos API listener port."
  default     = 50000
}

variable "talos_version" {
  type        = string
  description = "Pinned Talos version used for generated machine configuration."
  default     = "v1.12.6"
}

variable "kubernetes_version" {
  type        = string
  description = "Pinned Kubernetes version for the management cluster."
  default     = "v1.35.4"
}

variable "capi_version" {
  type        = string
  description = "Pinned Cluster API core version for non-prod management bootstrap."
  default     = "v1.13.0"
}

variable "cabpt_version" {
  type        = string
  description = "Pinned Cluster API Bootstrap Provider Talos version."
  default     = "v0.6.11"
}

variable "cacppt_version" {
  type        = string
  description = "Pinned Cluster API Control Plane Provider Talos version."
  default     = "v0.5.12"
}

variable "caph_branch" {
  type        = string
  description = "Validated CAPH source branch used until a compatible v1.1.x or newer release artifact is promoted."
  default     = "v1.1.x"
}

variable "control_plane_config_patches" {
  type        = list(string)
  description = "Optional Talos config patches applied to control-plane nodes."
  default     = []
}

variable "worker_config_patches" {
  type        = list(string)
  description = "Optional Talos config patches applied to worker nodes."
  default     = []
}

variable "control_plane_nodes" {
  type = map(object({
    location                 = string
    server_type              = string
    image                    = string
    enable_backups           = optional(bool, false)
    enable_delete_protection = optional(bool, true)
    enable_ipv6              = optional(bool, false)
    labels                   = optional(map(string), {})
  }))
  description = "Control-plane nodes for the non-prod management cluster. P1.5 baseline requires exactly one node."
}

variable "worker_nodes" {
  type = map(object({
    location                 = string
    server_type              = string
    image                    = string
    enable_backups           = optional(bool, false)
    enable_delete_protection = optional(bool, true)
    enable_ipv6              = optional(bool, false)
    labels                   = optional(map(string), {})
  }))
  description = "Worker nodes for the non-prod management cluster. P1.5 baseline requires at least two nodes."
}
