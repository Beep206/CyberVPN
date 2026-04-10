locals {
  admin_source_ips   = concat(var.admin_ipv4_cidrs, var.admin_ipv6_cidrs)
  metrics_source_ips = concat(var.metrics_ipv4_cidrs, var.metrics_ipv6_cidrs)

  inbound_rules = concat(
    [
      {
        description = "Administrative SSH access"
        direction   = "in"
        protocol    = "tcp"
        port        = tostring(var.ssh_port)
        source_ips  = local.admin_source_ips
      }
    ],
    var.allow_https_tcp ? [
      {
        description = "VPN TCP ingress"
        direction   = "in"
        protocol    = "tcp"
        port        = "443"
        source_ips  = ["0.0.0.0/0", "::/0"]
      }
    ] : [],
    var.allow_https_udp ? [
      {
        description = "VPN UDP ingress"
        direction   = "in"
        protocol    = "udp"
        port        = "443"
        source_ips  = ["0.0.0.0/0", "::/0"]
      }
    ] : [],
    length(local.metrics_source_ips) > 0 ? [
      {
        description = "Metrics ingress"
        direction   = "in"
        protocol    = "tcp"
        port        = tostring(var.metrics_port)
        source_ips  = local.metrics_source_ips
      }
    ] : [],
  )
}

resource "hcloud_firewall" "this" {
  name   = var.name
  labels = var.labels

  lifecycle {
    precondition {
      condition     = length(local.admin_source_ips) > 0
      error_message = "At least one admin CIDR must be provided for SSH access."
    }
  }

  dynamic "rule" {
    for_each = local.inbound_rules

    content {
      direction   = rule.value.direction
      protocol    = rule.value.protocol
      port        = rule.value.port
      source_ips  = rule.value.source_ips
      description = rule.value.description
    }
  }
}
