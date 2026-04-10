variable "zone_id" {
  type        = string
  description = "Cloudflare zone ID."
}

variable "edge_state" {
  type = object({
    bucket       = string
    key          = string
    region       = string
    use_lockfile = optional(bool, true)
  })
  description = "Remote state location for the staging edge stack."
}

variable "records" {
  type = map(object({
    name    = string
    node    = string
    type    = string
    ttl     = optional(number, 300)
    proxied = optional(bool, false)
    comment = optional(string, null)
    tags    = optional(set(string), [])
  }))
  description = "Cloudflare DNS records keyed by logical name. Use FQDNs or @ for the zone apex."

  validation {
    condition     = alltrue([for record in values(var.records) : record.type == "A"])
    error_message = "Phase 1 DNS records must be A records backed by edge node IPv4 addresses."
  }
}
