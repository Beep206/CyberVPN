output "posthog_instance_id" {
  description = "Canonical PostHog instance id."
  value       = var.posthog_instance_id
}

output "posthog_domain" {
  description = "Canonical PostHog DNS name."
  value       = var.posthog_domain
}

output "posthog_firewall_id" {
  description = "Hetzner firewall protecting the PostHog node."
  value       = module.posthog_firewall.id
}

output "posthog_nodes" {
  description = "Provisioned PostHog nodes keyed by hostname."
  value = {
    for name, node in module.posthog_nodes : name => {
      id           = node.id
      ipv4_address = node.ipv4_address
      ssh_port     = node.ssh_port
      domain_name  = node.domain_name
      https_url    = "https://${var.posthog_domain}"
      labels       = node.labels
    }
  }
}
