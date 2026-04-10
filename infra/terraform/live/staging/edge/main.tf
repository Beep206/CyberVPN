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

module "edge_nodes" {
  for_each = var.edge_nodes
  source   = "../../../modules/edge_node"

  name                       = each.key
  project                    = var.project_name
  environment                = var.environment
  role                       = each.value.role
  location                   = each.value.location
  server_type                = each.value.server_type
  image                      = each.value.image
  ssh_keys                   = values(data.terraform_remote_state.foundation.outputs.ssh_key_names)
  firewall_ids               = [data.terraform_remote_state.foundation.outputs.edge_firewall_id]
  admin_username             = each.value.admin_username
  ssh_port                   = each.value.ssh_port
  enable_backups             = each.value.enable_backups
  enable_delete_protection   = each.value.enable_delete_protection
  enable_ipv6                = each.value.enable_ipv6
  cloud_init_authorized_keys = each.value.cloud_init_authorized_keys
  labels = merge(
    module.common_labels.labels,
    {
      component = "edge"
      location  = each.value.location
    },
  )
}
