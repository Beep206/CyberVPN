data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket       = var.foundation_state.bucket
    key          = var.foundation_state.key
    region       = var.foundation_state.region
    use_lockfile = var.foundation_state.use_lockfile
  }
}

module "common_labels" {
  source      = "../../../modules/common_labels"
  project     = var.project_name
  environment = var.environment
  extra       = var.common_labels
}

module "nats_nodes" {
  for_each = var.nats_nodes
  source   = "../../../modules/nats_node"

  name                       = each.key
  project                    = var.project_name
  environment                = var.environment
  nats_cluster_id            = var.nats_cluster_id
  location                   = each.value.location
  server_type                = each.value.server_type
  image                      = each.value.image
  ssh_keys                   = values(data.terraform_remote_state.foundation.outputs.ssh_key_names)
  admin_username             = each.value.admin_username
  ssh_port                   = each.value.ssh_port
  enable_backups             = each.value.enable_backups
  enable_delete_protection   = each.value.enable_delete_protection
  enable_ipv6                = each.value.enable_ipv6
  cloud_init_authorized_keys = each.value.cloud_init_authorized_keys
  nats_version               = var.nats_version
  nats_exporter_version      = var.nats_exporter_version
  client_port                = var.nats_client_port
  cluster_port               = var.nats_cluster_port
  monitor_port               = var.nats_monitor_port
  exporter_port              = var.nats_exporter_port
  jetstream_max_file_store   = var.jetstream_max_file_store
  jetstream_max_memory_store = var.jetstream_max_memory_store
  labels = merge(
    module.common_labels.labels,
    each.value.labels,
    {
      component    = "nats"
      nats_cluster = var.nats_cluster_id
      location     = each.value.location
    },
  )
}

locals {
  nats_client_source_ips = concat(var.admin_ipv4_cidrs, var.client_ipv4_cidrs)
  nats_client_source_v6  = concat(var.admin_ipv6_cidrs, var.client_ipv6_cidrs)
  nats_route_source_ips  = [for name in sort(keys(module.nats_nodes)) : "${module.nats_nodes[name].ipv4_address}/32"]
}

module "nats_firewall" {
  source             = "../../../modules/firewall_policy"
  name               = coalesce(var.firewall_name, "${var.project_name}-${var.environment}-nats")
  labels             = module.common_labels.labels
  ssh_port           = var.ssh_port
  admin_ipv4_cidrs   = var.admin_ipv4_cidrs
  admin_ipv6_cidrs   = var.admin_ipv6_cidrs
  allow_https_tcp    = false
  allow_https_udp    = false
  metrics_port       = var.nats_exporter_port
  metrics_ipv4_cidrs = var.metrics_ipv4_cidrs
  metrics_ipv6_cidrs = var.metrics_ipv6_cidrs
  extra_inbound_rules = concat(
    length(local.nats_client_source_ips) > 0 ? [
      {
        description = "NATS client ingress"
        protocol    = "tcp"
        port        = tostring(var.nats_client_port)
        source_ips  = local.nats_client_source_ips
      }
    ] : [],
    length(local.nats_client_source_v6) > 0 ? [
      {
        description = "NATS client ingress IPv6"
        protocol    = "tcp"
        port        = tostring(var.nats_client_port)
        source_ips  = local.nats_client_source_v6
      }
    ] : [],
    length(local.nats_route_source_ips) > 0 ? [
      {
        description = "NATS cluster route ingress"
        protocol    = "tcp"
        port        = tostring(var.nats_cluster_port)
        source_ips  = local.nats_route_source_ips
      }
    ] : [],
  )
}

resource "hcloud_firewall_attachment" "nats_nodes" {
  firewall_id = module.nats_firewall.id
  server_ids  = [for name in sort(keys(module.nats_nodes)) : module.nats_nodes[name].id]
}
