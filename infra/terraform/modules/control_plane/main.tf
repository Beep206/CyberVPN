module "node" {
  source = "../edge_node"

  name                       = var.name
  project                    = var.project
  environment                = var.environment
  role                       = "control-plane"
  location                   = var.location
  server_type                = var.server_type
  image                      = var.image
  ssh_keys                   = var.ssh_keys
  firewall_ids               = var.firewall_ids
  admin_username             = var.admin_username
  ssh_port                   = var.ssh_port
  enable_backups             = var.enable_backups
  enable_delete_protection   = var.enable_delete_protection
  enable_ipv6                = var.enable_ipv6
  cloud_init_authorized_keys = var.cloud_init_authorized_keys
  labels = merge(
    var.labels,
    length(var.service_roles) > 0 ? {
      workload_roles = join(",", sort(var.service_roles))
    } : {},
  )
}
