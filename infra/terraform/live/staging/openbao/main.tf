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

resource "aws_kms_key" "seal" {
  description             = "Auto-unseal key for ${var.openbao_cluster_id}"
  deletion_window_in_days = var.kms_deletion_window_in_days
  enable_key_rotation     = true
  tags = merge(
    module.common_labels.labels,
    {
      component       = "openbao"
      openbao_cluster = var.openbao_cluster_id
      purpose         = "seal"
    },
  )
}

resource "aws_kms_alias" "seal" {
  name          = "alias/openbao/nonprod/seal"
  target_key_id = aws_kms_key.seal.key_id
}

locals {
  openbao_api_source_ips    = concat(var.admin_ipv4_cidrs, var.api_ipv4_cidrs)
  openbao_api_source_ips_v6 = concat(var.admin_ipv6_cidrs, var.api_ipv6_cidrs)
}

module "openbao_firewall" {
  source             = "../../../modules/firewall_policy"
  name               = coalesce(var.firewall_name, "${var.project_name}-${var.environment}-openbao")
  labels             = module.common_labels.labels
  ssh_port           = var.ssh_port
  admin_ipv4_cidrs   = var.admin_ipv4_cidrs
  admin_ipv6_cidrs   = var.admin_ipv6_cidrs
  allow_https_tcp    = false
  allow_https_udp    = false
  metrics_port       = var.metrics_port
  metrics_ipv4_cidrs = var.metrics_ipv4_cidrs
  metrics_ipv6_cidrs = var.metrics_ipv6_cidrs
  extra_inbound_rules = concat(
    length(local.openbao_api_source_ips) > 0 ? [
      {
        description = "OpenBao API and UI ingress"
        protocol    = "tcp"
        port        = tostring(var.openbao_api_port)
        source_ips  = local.openbao_api_source_ips
      }
    ] : [],
    length(local.openbao_api_source_ips_v6) > 0 ? [
      {
        description = "OpenBao API and UI ingress IPv6"
        protocol    = "tcp"
        port        = tostring(var.openbao_api_port)
        source_ips  = local.openbao_api_source_ips_v6
      }
    ] : [],
  )
}

module "openbao_nodes" {
  for_each = var.openbao_nodes
  source   = "../../../modules/openbao_node"

  name                       = each.key
  project                    = var.project_name
  environment                = var.environment
  openbao_cluster_id         = var.openbao_cluster_id
  location                   = each.value.location
  server_type                = each.value.server_type
  image                      = each.value.image
  ssh_keys                   = values(data.terraform_remote_state.foundation.outputs.ssh_key_names)
  firewall_ids               = [module.openbao_firewall.id]
  admin_username             = each.value.admin_username
  ssh_port                   = each.value.ssh_port
  enable_backups             = each.value.enable_backups
  enable_delete_protection   = each.value.enable_delete_protection
  enable_ipv6                = each.value.enable_ipv6
  cloud_init_authorized_keys = each.value.cloud_init_authorized_keys
  openbao_version            = var.openbao_version
  kms_key_alias              = aws_kms_alias.seal.name
  aws_region                 = var.aws_region
  api_port                   = var.openbao_api_port
  cluster_port               = var.openbao_cluster_port
  metrics_port               = var.metrics_port
  tls_common_name            = each.value.tls_common_name
  retry_join_api_addrs       = []
  labels = merge(
    module.common_labels.labels,
    each.value.labels,
    {
      component       = "openbao"
      openbao_cluster = var.openbao_cluster_id
      location        = each.value.location
    },
  )
}
