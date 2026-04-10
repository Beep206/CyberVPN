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
  value       = hcloud_primary_ip.ipv4.ip_address
}

output "location" {
  description = "Hetzner location."
  value       = hcloud_server.this.location
}

output "role" {
  description = "Node role."
  value       = var.role
}

output "server_type" {
  description = "Server type."
  value       = hcloud_server.this.server_type
}

output "ssh_port" {
  description = "Configured bootstrap SSH port."
  value       = var.ssh_port
}

output "labels" {
  description = "Applied labels."
  value       = hcloud_server.this.labels
}
