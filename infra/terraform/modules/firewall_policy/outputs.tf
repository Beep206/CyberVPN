output "id" {
  description = "Firewall ID."
  value       = hcloud_firewall.this.id
}

output "name" {
  description = "Firewall name."
  value       = hcloud_firewall.this.name
}
