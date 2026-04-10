output "edge_nodes" {
  description = "Structured metadata for production edge nodes."
  value = {
    for name, node in module.edge_nodes : name => {
      id          = node.id
      ip          = node.ipv4_address
      location    = node.location
      role        = node.role
      server_type = node.server_type
      ssh_port    = node.ssh_port
      labels      = node.labels
    }
  }
}

output "ansible_inventory" {
  description = "Inventory-friendly map for later Ansible generation."
  value = {
    all = {
      hosts = {
        for name, node in module.edge_nodes : name => {
          ansible_host  = node.ipv4_address
          ansible_port  = node.ssh_port
          node_role     = node.role
          node_location = node.location
        }
      }
    }
  }
}
