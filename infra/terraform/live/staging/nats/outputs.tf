output "nats_cluster_id" {
  description = "Canonical NATS cluster id."
  value       = var.nats_cluster_id
}

output "nats_firewall_id" {
  description = "Hetzner firewall protecting the NATS nodes."
  value       = module.nats_firewall.id
}

output "nats_nodes" {
  description = "Provisioned NATS nodes keyed by hostname."
  value = {
    for name, node in module.nats_nodes : name => {
      id            = node.id
      ipv4_address  = node.ipv4_address
      client_addr   = "${node.ipv4_address}:${node.client_port}"
      cluster_addr  = "${node.ipv4_address}:${node.cluster_port}"
      monitor_addr  = "http://127.0.0.1:${var.nats_monitor_port}"
      exporter_addr = "http://${node.ipv4_address}:${node.exporter_port}/metrics"
      client_port   = node.client_port
      cluster_port  = node.cluster_port
      monitor_port  = var.nats_monitor_port
      exporter_port = node.exporter_port
      ssh_port      = node.ssh_port
      labels        = node.labels
    }
  }
}
