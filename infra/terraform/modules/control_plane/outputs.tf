output "id" {
  description = "Server ID."
  value       = module.node.id
}

output "name" {
  description = "Server name."
  value       = module.node.name
}

output "ipv4_address" {
  description = "Public IPv4 address."
  value       = module.node.ipv4_address
}

output "location" {
  description = "Hetzner location."
  value       = module.node.location
}

output "server_type" {
  description = "Server type."
  value       = module.node.server_type
}

output "ssh_port" {
  description = "Configured bootstrap SSH port."
  value       = module.node.ssh_port
}

output "labels" {
  description = "Applied labels."
  value       = module.node.labels
}

output "service_roles" {
  description = "Declared workload roles assigned to the host."
  value       = var.service_roles
}
