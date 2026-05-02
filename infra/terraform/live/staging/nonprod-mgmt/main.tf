locals {
  control_plane_keys = sort(keys(var.control_plane_nodes))
  worker_keys        = sort(keys(var.worker_nodes))

  primary_control_plane_key = local.control_plane_keys[0]
  talos_endpoint            = "https://${hcloud_primary_ip.kube_api.ip_address}:${var.kubernetes_api_port}"

  control_plane_node_ipv4s = [for name in local.control_plane_keys : module.control_plane_nodes[name].ipv4_address]
  worker_node_ipv4s        = [for name in local.worker_keys : module.worker_nodes[name].ipv4_address]
  all_node_ipv4s           = concat(local.control_plane_node_ipv4s, local.worker_node_ipv4s)

  control_plane_api_source_ips_v4 = distinct(concat(
    var.admin_ipv4_cidrs,
    [for address in local.all_node_ipv4s : "${address}/32"],
  ))
  control_plane_api_source_ips_v6 = distinct(var.admin_ipv6_cidrs)
  node_mesh_source_ips_v4         = [for address in local.all_node_ipv4s : "${address}/32"]
}

module "common_labels" {
  source      = "../../../modules/common_labels"
  project     = var.project_name
  environment = var.environment
  extra       = var.common_labels
}

resource "hcloud_primary_ip" "kube_api" {
  name              = "${var.management_cluster_id}-kube-api"
  type              = "ipv4"
  location          = var.control_plane_nodes[local.primary_control_plane_key].location
  assignee_type     = "server"
  auto_delete       = false
  delete_protection = true
  labels = merge(
    module.common_labels.labels,
    {
      component          = "management-cluster"
      management_cluster = var.management_cluster_id
      purpose            = "kube-api-endpoint"
    },
  )

  lifecycle {
    precondition {
      condition     = length(local.control_plane_keys) == 1
      error_message = "P1.5 baseline requires exactly one control-plane node for nonprod-mgmt."
    }

    precondition {
      condition     = length(local.worker_keys) >= 2
      error_message = "P1.5 baseline requires at least two worker nodes for nonprod-mgmt."
    }
  }
}

resource "talos_machine_secrets" "this" {}

data "talos_machine_configuration" "controlplane" {
  cluster_name       = var.management_cluster_id
  cluster_endpoint   = local.talos_endpoint
  machine_type       = "controlplane"
  machine_secrets    = talos_machine_secrets.this.machine_secrets
  talos_version      = var.talos_version
  kubernetes_version = var.kubernetes_version
  config_patches     = var.control_plane_config_patches
}

data "talos_machine_configuration" "worker" {
  cluster_name       = var.management_cluster_id
  cluster_endpoint   = local.talos_endpoint
  machine_type       = "worker"
  machine_secrets    = talos_machine_secrets.this.machine_secrets
  talos_version      = var.talos_version
  kubernetes_version = var.kubernetes_version
  config_patches     = var.worker_config_patches
}

module "control_plane_nodes" {
  for_each = var.control_plane_nodes
  source   = "../../../modules/talos_node"

  name                        = each.key
  project                     = var.project_name
  environment                 = var.environment
  management_cluster_id       = var.management_cluster_id
  node_role                   = "control-plane"
  location                    = each.value.location
  server_type                 = each.value.server_type
  image                       = each.value.image
  enable_backups              = each.value.enable_backups
  enable_delete_protection    = each.value.enable_delete_protection
  enable_ipv6                 = each.value.enable_ipv6
  existing_primary_ip_id      = each.key == local.primary_control_plane_key ? hcloud_primary_ip.kube_api.id : null
  existing_primary_ip_address = each.key == local.primary_control_plane_key ? hcloud_primary_ip.kube_api.ip_address : null
  labels = merge(
    module.common_labels.labels,
    each.value.labels,
    {
      component          = "management-cluster"
      management_cluster = var.management_cluster_id
      location           = each.value.location
    },
  )
}

module "worker_nodes" {
  for_each = var.worker_nodes
  source   = "../../../modules/talos_node"

  name                     = each.key
  project                  = var.project_name
  environment              = var.environment
  management_cluster_id    = var.management_cluster_id
  node_role                = "worker"
  location                 = each.value.location
  server_type              = each.value.server_type
  image                    = each.value.image
  enable_backups           = each.value.enable_backups
  enable_delete_protection = each.value.enable_delete_protection
  enable_ipv6              = each.value.enable_ipv6
  labels = merge(
    module.common_labels.labels,
    each.value.labels,
    {
      component          = "management-cluster"
      management_cluster = var.management_cluster_id
      location           = each.value.location
    },
  )
}

module "management_firewall" {
  source             = "../../../modules/firewall_policy"
  name               = coalesce(var.firewall_name, "${var.project_name}-${var.environment}-nonprod-mgmt")
  labels             = module.common_labels.labels
  enable_ssh         = false
  allow_https_tcp    = false
  allow_https_udp    = false
  metrics_ipv4_cidrs = []
  metrics_ipv6_cidrs = []
  extra_inbound_rules = concat(
    length(var.admin_ipv4_cidrs) > 0 ? [
      {
        description = "Talos API ingress"
        protocol    = "tcp"
        port        = tostring(var.talos_api_port)
        source_ips  = var.admin_ipv4_cidrs
      }
    ] : [],
    length(var.admin_ipv6_cidrs) > 0 ? [
      {
        description = "Talos API ingress IPv6"
        protocol    = "tcp"
        port        = tostring(var.talos_api_port)
        source_ips  = var.admin_ipv6_cidrs
      }
    ] : [],
    length(local.control_plane_api_source_ips_v4) > 0 ? [
      {
        description = "Kubernetes API ingress"
        protocol    = "tcp"
        port        = tostring(var.kubernetes_api_port)
        source_ips  = local.control_plane_api_source_ips_v4
      }
    ] : [],
    length(local.control_plane_api_source_ips_v6) > 0 ? [
      {
        description = "Kubernetes API ingress IPv6"
        protocol    = "tcp"
        port        = tostring(var.kubernetes_api_port)
        source_ips  = local.control_plane_api_source_ips_v6
      }
    ] : [],
    length(local.node_mesh_source_ips_v4) > 0 ? [
      {
        description = "Cluster internode TCP mesh"
        protocol    = "tcp"
        port        = "1-65535"
        source_ips  = local.node_mesh_source_ips_v4
      },
      {
        description = "Cluster internode UDP mesh"
        protocol    = "udp"
        port        = "1-65535"
        source_ips  = local.node_mesh_source_ips_v4
      }
    ] : [],
  )
}

resource "hcloud_firewall_attachment" "management_nodes" {
  firewall_id = module.management_firewall.id
  server_ids = concat(
    [for name in local.control_plane_keys : module.control_plane_nodes[name].id],
    [for name in local.worker_keys : module.worker_nodes[name].id],
  )
}

data "talos_client_configuration" "this" {
  cluster_name         = var.management_cluster_id
  client_configuration = talos_machine_secrets.this.client_configuration
  endpoints            = [module.control_plane_nodes[local.primary_control_plane_key].ipv4_address]
  nodes                = [module.control_plane_nodes[local.primary_control_plane_key].ipv4_address]
}

resource "talos_machine_configuration_apply" "controlplane" {
  for_each = module.control_plane_nodes

  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.controlplane.machine_configuration
  node                        = each.value.ipv4_address

  depends_on = [
    hcloud_firewall_attachment.management_nodes,
  ]
}

resource "talos_machine_bootstrap" "this" {
  depends_on = [
    talos_machine_configuration_apply.controlplane,
  ]

  node                 = module.control_plane_nodes[local.primary_control_plane_key].ipv4_address
  client_configuration = talos_machine_secrets.this.client_configuration
}

resource "talos_machine_configuration_apply" "worker" {
  for_each = module.worker_nodes

  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.worker.machine_configuration
  node                        = each.value.ipv4_address

  depends_on = [
    talos_machine_bootstrap.this,
  ]
}

resource "talos_cluster_kubeconfig" "this" {
  depends_on = [
    talos_machine_configuration_apply.worker,
  ]

  client_configuration = talos_machine_secrets.this.client_configuration
  node                 = module.control_plane_nodes[local.primary_control_plane_key].ipv4_address
}
