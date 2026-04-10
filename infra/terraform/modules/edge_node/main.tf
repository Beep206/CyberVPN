locals {
  effective_labels = merge(
    {
      project     = var.project
      environment = var.environment
      role        = var.role
      managed_by  = "terraform"
    },
    var.labels,
  )
}

resource "hcloud_primary_ip" "ipv4" {
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
  ssh_keys           = var.ssh_keys
  firewall_ids       = var.firewall_ids
  backups            = var.enable_backups
  delete_protection  = var.enable_delete_protection
  rebuild_protection = var.enable_delete_protection
  user_data = coalesce(
    var.user_data_override,
    templatefile("${path.module}/templates/cloud-init.yaml.tftpl", {
      admin_username  = var.admin_username
      ssh_port        = var.ssh_port
      authorized_keys = var.cloud_init_authorized_keys
    }),
  )
  labels = local.effective_labels

  public_net {
    ipv4_enabled = true
    ipv4         = hcloud_primary_ip.ipv4.id
    ipv6_enabled = var.enable_ipv6
  }

  lifecycle {
    ignore_changes = [
      ssh_keys,
      user_data,
    ]
  }
}
