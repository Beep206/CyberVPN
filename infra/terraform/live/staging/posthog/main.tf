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

module "posthog_firewall" {
  source             = "../../../modules/firewall_policy"
  name               = coalesce(var.firewall_name, "${var.project_name}-${var.environment}-posthog")
  labels             = module.common_labels.labels
  ssh_port           = var.ssh_port
  admin_ipv4_cidrs   = var.admin_ipv4_cidrs
  admin_ipv6_cidrs   = var.admin_ipv6_cidrs
  allow_https_tcp    = false
  allow_https_udp    = false
  metrics_port       = 9100
  metrics_ipv4_cidrs = []
  metrics_ipv6_cidrs = []
  extra_inbound_rules = concat(
    length(var.http_ipv4_cidrs) > 0 ? [
      {
        description = "PostHog HTTP ingress"
        protocol    = "tcp"
        port        = "80"
        source_ips  = var.http_ipv4_cidrs
      },
      {
        description = "PostHog HTTPS ingress"
        protocol    = "tcp"
        port        = "443"
        source_ips  = var.http_ipv4_cidrs
      }
    ] : [],
    length(var.http_ipv6_cidrs) > 0 ? [
      {
        description = "PostHog HTTP ingress IPv6"
        protocol    = "tcp"
        port        = "80"
        source_ips  = var.http_ipv6_cidrs
      },
      {
        description = "PostHog HTTPS ingress IPv6"
        protocol    = "tcp"
        port        = "443"
        source_ips  = var.http_ipv6_cidrs
      }
    ] : [],
  )
}

module "posthog_nodes" {
  for_each = var.posthog_nodes
  source   = "../../../modules/posthog_node"

  name                       = each.key
  project                    = var.project_name
  environment                = var.environment
  posthog_instance_id        = var.posthog_instance_id
  domain_name                = var.posthog_domain
  location                   = each.value.location
  server_type                = each.value.server_type
  image                      = each.value.image
  ssh_keys                   = values(data.terraform_remote_state.foundation.outputs.ssh_key_names)
  firewall_ids               = [module.posthog_firewall.id]
  admin_username             = each.value.admin_username
  ssh_port                   = each.value.ssh_port
  enable_backups             = each.value.enable_backups
  enable_delete_protection   = each.value.enable_delete_protection
  enable_ipv6                = each.value.enable_ipv6
  cloud_init_authorized_keys = each.value.cloud_init_authorized_keys
  backup_retention_days      = var.backup_retention_days
  labels = merge(
    module.common_labels.labels,
    each.value.labels,
    {
      component        = "posthog"
      posthog_instance = var.posthog_instance_id
      location         = each.value.location
    },
  )
}
