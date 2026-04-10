variable "project" {
  type        = string
  description = "Project label."
}

variable "environment" {
  type        = string
  description = "Environment label."
}

variable "managed_by" {
  type        = string
  description = "Managed-by label."
  default     = "terraform"
}

variable "extra" {
  type        = map(string)
  description = "Additional labels."
  default     = {}
}
