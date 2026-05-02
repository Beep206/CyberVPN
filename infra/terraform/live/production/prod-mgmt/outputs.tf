output "management_cluster_id" {
  description = "Canonical management cluster id."
  value       = var.management_cluster_id
}

output "kubernetes_api_endpoint" {
  description = "Stable Kubernetes API endpoint for the management cluster."
  value       = "https://${hcloud_load_balancer.kube_api.ipv4}:${var.kubernetes_api_port}"
}

output "api_load_balancer" {
  description = "Hetzner load balancer serving the stable Kubernetes API endpoint."
  value = {
    id               = hcloud_load_balancer.kube_api.id
    name             = hcloud_load_balancer.kube_api.name
    ipv4             = hcloud_load_balancer.kube_api.ipv4
    ipv6             = hcloud_load_balancer.kube_api.ipv6
    location         = hcloud_load_balancer.kube_api.location
    load_balancer_id = hcloud_load_balancer.kube_api.id
    type             = var.api_load_balancer_type
  }
}

output "talos_api_endpoints" {
  description = "Talos API endpoints for the control-plane nodes."
  value       = local.control_plane_node_ipv4s
}

output "control_plane_nodes" {
  description = "Provisioned control-plane nodes keyed by hostname."
  value = {
    for name, node in module.control_plane_nodes : name => {
      id           = node.id
      ipv4_address = node.ipv4_address
      location     = node.location
      server_type  = node.server_type
      node_role    = node.node_role
      labels       = node.labels
    }
  }
}

output "worker_nodes" {
  description = "Provisioned worker nodes keyed by hostname."
  value = {
    for name, node in module.worker_nodes : name => {
      id           = node.id
      ipv4_address = node.ipv4_address
      location     = node.location
      server_type  = node.server_type
      node_role    = node.node_role
      labels       = node.labels
    }
  }
}

output "management_firewall_id" {
  description = "Hetzner firewall protecting the prod management cluster."
  value       = module.management_firewall.id
}

output "talosconfig" {
  description = "Administrative Talos client configuration for prod-mgmt."
  value       = data.talos_client_configuration.this.talos_config
  sensitive   = true
}

output "kubeconfig_raw" {
  description = "Administrative kubeconfig for prod-mgmt."
  value       = talos_cluster_kubeconfig.this.kubeconfig_raw
  sensitive   = true
}

output "provider_versions" {
  description = "Pinned provider versions and tracks for the management-cluster bootstrap bundle."
  value = {
    capi_version   = var.capi_version
    cabpt_version  = var.cabpt_version
    cacppt_version = var.cacppt_version
    caph_branch    = var.caph_branch
    talos_version  = var.talos_version
  }
}
