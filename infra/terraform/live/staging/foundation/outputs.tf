output "edge_firewall_id" {
  description = "Default staging edge firewall ID."
  value       = module.edge_firewall.id
}

output "edge_firewall_name" {
  description = "Default staging edge firewall name."
  value       = module.edge_firewall.name
}

output "ssh_key_ids" {
  description = "Hetzner SSH key IDs keyed by logical name."
  value       = { for name, key in hcloud_ssh_key.admin : name => key.id }
}

output "ssh_key_names" {
  description = "Hetzner SSH key names keyed by logical name."
  value       = { for name, key in hcloud_ssh_key.admin : name => key.name }
}
