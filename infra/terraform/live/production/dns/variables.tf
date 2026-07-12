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
  description = "Remote state location for the production edge stack."
}

variable "records" {
  type = map(object({
    name         = string
    node         = optional(string)
    content      = optional(string)
    record_class = optional(string, "edge")
    type         = string
    ttl          = optional(number, 300)
    proxied      = optional(bool, false)
    comment      = optional(string, null)
    tags         = optional(set(string), [])
  }))
  description = "Cloudflare DNS records keyed by logical name. Use FQDNs or @ for the zone apex."

  validation {
    condition     = alltrue([for record in values(var.records) : contains(["A", "AAAA"], record.type)])
    error_message = "Production DNS records must use canonical A or AAAA types."
  }

  validation {
    condition     = alltrue([for record in values(var.records) : contains(["edge", "vpn-node"], record.record_class)])
    error_message = "Production DNS records must use the edge or vpn-node record class."
  }

  validation {
    condition = alltrue([
      for record in values(var.records) :
      record.record_class == "edge" ? (
        try(length(trimspace(record.node)) > 0, false)
        && record.content == null
        ) : (
        try(length(trimspace(record.content)) > 0, false)
        && record.node == null
        && !record.proxied
      )
    ])
    error_message = "Edge records require only an edge-state node; vpn-node records require only explicit DNS-only content."
  }

  validation {
    condition = alltrue([
      for record in values(var.records) :
      record.type != "AAAA" || record.record_class == "vpn-node"
    ])
    error_message = "AAAA records must use the vpn-node class until edge state exposes a dedicated IPv6 output."
  }
}
