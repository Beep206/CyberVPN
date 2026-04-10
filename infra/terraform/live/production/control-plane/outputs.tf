output "control_plane_firewall_id" {
  description = "Default production control-plane firewall ID."
  value       = module.control_plane_firewall.id
}

output "control_plane_firewall_name" {
  description = "Default production control-plane firewall name."
  value       = module.control_plane_firewall.name
}

output "control_plane_nodes" {
  description = "Control-plane node inventory data."
  value = {
    for hostname, node in module.control_plane_nodes : hostname => {
      id            = node.id
      name          = node.name
      ipv4_address  = node.ipv4_address
      location      = node.location
      server_type   = node.server_type
      ssh_port      = node.ssh_port
      labels        = node.labels
      service_roles = node.service_roles
    }
  }
}
