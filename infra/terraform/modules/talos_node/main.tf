locals {
  effective_labels = merge(
    {
      project            = var.project
      environment        = var.environment
      role               = var.node_role
      component          = "talos"
      management_cluster = var.management_cluster_id
      managed_by         = "terraform"
    },
    var.labels,
  )

  primary_ip_id      = var.existing_primary_ip_id != null ? var.existing_primary_ip_id : hcloud_primary_ip.ipv4[0].id
  primary_ip_address = var.existing_primary_ip_address != null ? var.existing_primary_ip_address : hcloud_primary_ip.ipv4[0].ip_address
}

resource "hcloud_primary_ip" "ipv4" {
  count             = var.existing_primary_ip_id == null ? 1 : 0
  name              = "${var.name}-ipv4"
  type              = "ipv4"
  location          = var.location
  assignee_type     = "server"
  auto_delete       = false
  delete_protection = var.enable_delete_protection
  labels            = local.effective_labels
}

resource "hcloud_server" "this" {
  name               = var.name
  server_type        = var.server_type
  image              = var.image
  location           = var.location
  firewall_ids       = var.firewall_ids
  backups            = var.enable_backups
  delete_protection  = var.enable_delete_protection
  rebuild_protection = var.enable_delete_protection
  user_data          = trimspace(var.user_data) != "" ? var.user_data : null
  labels             = local.effective_labels

  public_net {
    ipv4_enabled = true
    ipv4         = local.primary_ip_id
    ipv6_enabled = var.enable_ipv6
  }

  lifecycle {
    ignore_changes = [
      user_data,
    ]
  }
}
