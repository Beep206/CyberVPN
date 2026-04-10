output "dns_record_ids" {
  description = "Cloudflare record IDs keyed by logical name."
  value       = { for name, record in cloudflare_dns_record.this : name => record.id }
}
