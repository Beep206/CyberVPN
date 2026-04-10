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

module "control_plane_firewall" {
  source           = "../../../modules/firewall_policy"
  name             = coalesce(var.firewall_name, "${var.project_name}-${var.environment}-control-plane")
  labels           = module.common_labels.labels
  ssh_port         = var.ssh_port
  admin_ipv4_cidrs = var.admin_ipv4_cidrs
  admin_ipv6_cidrs = var.admin_ipv6_cidrs
}

module "control_plane_nodes" {
  for_each = var.control_plane_nodes
  source   = "../../../modules/control_plane"

  name                       = each.key
  project                    = var.project_name
  environment                = var.environment
  location                   = each.value.location
  server_type                = each.value.server_type
  image                      = each.value.image
  ssh_keys                   = values(data.terraform_remote_state.foundation.outputs.ssh_key_names)
  firewall_ids               = [module.control_plane_firewall.id]
  service_roles              = each.value.service_roles
  admin_username             = each.value.admin_username
  ssh_port                   = each.value.ssh_port
  enable_backups             = each.value.enable_backups
  enable_delete_protection   = each.value.enable_delete_protection
  enable_ipv6                = each.value.enable_ipv6
  cloud_init_authorized_keys = each.value.cloud_init_authorized_keys
  labels = merge(
    module.common_labels.labels,
    {
      component = "control-plane"
      location  = each.value.location
    },
  )
}
