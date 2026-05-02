locals {
  effective_labels = merge(
    {
      project         = var.project
      environment     = var.environment
      role            = "openbao"
      component       = "openbao"
      openbao_cluster = var.openbao_cluster_id
      managed_by      = "terraform"
    },
    var.labels,
  )

  tls_common_name = trimspace(var.tls_common_name) != "" ? trimspace(var.tls_common_name) : var.name
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
    admin_username       = var.admin_username
    ssh_port             = var.ssh_port
    authorized_keys      = var.cloud_init_authorized_keys
    openbao_version      = var.openbao_version
    openbao_cluster_id   = var.openbao_cluster_id
    api_addr             = "https://${hcloud_primary_ip.ipv4.ip_address}:${var.api_port}"
    cluster_addr         = "https://${hcloud_primary_ip.ipv4.ip_address}:${var.cluster_port}"
    api_port             = var.api_port
    cluster_port         = var.cluster_port
    metrics_port         = var.metrics_port
    advertise_address    = hcloud_primary_ip.ipv4.ip_address
    tls_common_name      = local.tls_common_name
    kms_key_alias        = var.kms_key_alias
    aws_region           = var.aws_region
    retry_join_api_addrs = var.retry_join_api_addrs
    openbao_config_hcl = templatefile("${path.module}/templates/openbao.hcl.tftpl", {
      api_addr             = "https://${hcloud_primary_ip.ipv4.ip_address}:${var.api_port}"
      cluster_addr         = "https://${hcloud_primary_ip.ipv4.ip_address}:${var.cluster_port}"
      api_port             = var.api_port
      aws_region           = var.aws_region
      cluster_port         = var.cluster_port
      kms_key_alias        = var.kms_key_alias
      metrics_port         = var.metrics_port
      node_id              = var.name
      retry_join_api_addrs = var.retry_join_api_addrs
    })
    openbao_service_unit = templatefile("${path.module}/templates/openbao.service.tftpl", {})
    install_script = templatefile("${path.module}/templates/install-openbao.sh.tftpl", {
      openbao_version   = var.openbao_version
      kms_key_alias     = var.kms_key_alias
      aws_region        = var.aws_region
      api_port          = var.api_port
      cluster_port      = var.cluster_port
      metrics_port      = var.metrics_port
      tls_common_name   = local.tls_common_name
      advertise_address = hcloud_primary_ip.ipv4.ip_address
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
