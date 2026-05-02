output "openbao_cluster_id" {
  description = "Canonical OpenBao cluster id."
  value       = var.openbao_cluster_id
}

output "openbao_kms_key_arn" {
  description = "AWS KMS key ARN used for auto-unseal."
  value       = aws_kms_key.seal.arn
}

output "openbao_kms_key_alias" {
  description = "AWS KMS alias used for auto-unseal."
  value       = aws_kms_alias.seal.name
}

output "openbao_firewall_id" {
  description = "Hetzner firewall protecting the OpenBao host."
  value       = module.openbao_firewall.id
}

output "openbao_nodes" {
  description = "Provisioned OpenBao nodes keyed by hostname."
  value = {
    for name, node in module.openbao_nodes : name => {
      id           = node.id
      ipv4_address = node.ipv4_address
      api_addr     = node.api_addr
      metrics_addr = node.metrics_addr
      ssh_port     = node.ssh_port
      labels       = node.labels
    }
  }
}
