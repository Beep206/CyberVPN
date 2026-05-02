locals {
  effective_labels = merge(
    {
      project      = var.project
      environment  = var.environment
      role         = "nats"
      component    = "nats"
      nats_cluster = var.nats_cluster_id
      managed_by   = "terraform"
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
  user_data = templatefile("${path.module}/templates/cloud-init.yaml.tftpl", {
    node_name                  = var.name
    admin_username             = var.admin_username
    ssh_port                   = var.ssh_port
    authorized_keys            = var.cloud_init_authorized_keys
    nats_version               = var.nats_version
    nats_exporter_version      = var.nats_exporter_version
    nats_cluster_id            = var.nats_cluster_id
    client_port                = var.client_port
    cluster_port               = var.cluster_port
    monitor_port               = var.monitor_port
    exporter_port              = var.exporter_port
    advertise_address          = hcloud_primary_ip.ipv4.ip_address
    jetstream_store_dir        = var.jetstream_store_dir
    jetstream_max_file_store   = var.jetstream_max_file_store
    jetstream_max_memory_store = var.jetstream_max_memory_store
    nats_service_unit          = templatefile("${path.module}/templates/nats.service.tftpl", {})
    exporter_service_unit      = templatefile("${path.module}/templates/nats-exporter.service.tftpl", {})
    install_script = templatefile("${path.module}/templates/install-nats.sh.tftpl", {
      nats_version          = var.nats_version
      nats_exporter_version = var.nats_exporter_version
    })
  })
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
