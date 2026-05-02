output "id" {
  description = "Server ID."
  value       = hcloud_server.this.id
}

output "name" {
  description = "Server name."
  value       = hcloud_server.this.name
}

output "ipv4_address" {
  description = "Public IPv4 address."
  value       = local.primary_ip_address
}

output "primary_ip_id" {
  description = "Attached primary IPv4 ID."
  value       = local.primary_ip_id
}

output "location" {
  description = "Hetzner location."
  value       = hcloud_server.this.location
}

output "server_type" {
  description = "Server type."
  value       = hcloud_server.this.server_type
}

output "node_role" {
  description = "Talos node role."
  value       = var.node_role
}

output "labels" {
  description = "Applied labels."
  value       = local.effective_labels
}
