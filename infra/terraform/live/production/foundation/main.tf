module "common_labels" {
  source      = "../../../modules/common_labels"
  project     = var.project_name
  environment = var.environment
  extra       = var.common_labels
}

module "edge_firewall" {
  source             = "../../../modules/firewall_policy"
  name               = coalesce(var.firewall_name, "${var.project_name}-${var.environment}-edge")
  labels             = module.common_labels.labels
  ssh_port           = var.ssh_port
  admin_ipv4_cidrs   = var.admin_ipv4_cidrs
  admin_ipv6_cidrs   = var.admin_ipv6_cidrs
  metrics_port       = var.edge_metrics_port
  metrics_ipv4_cidrs = var.edge_metrics_ipv4_cidrs
  metrics_ipv6_cidrs = var.edge_metrics_ipv6_cidrs
}

resource "hcloud_ssh_key" "admin" {
  for_each   = var.ssh_keys
  name       = "${var.project_name}-${var.environment}-${each.key}"
  public_key = each.value.public_key
  labels     = merge(module.common_labels.labels, each.value.labels)
}
