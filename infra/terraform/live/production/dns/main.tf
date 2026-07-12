locals {
  edge_records = {
    for name, record in var.records : name => record
    if record.record_class == "edge"
  }
}

data "terraform_remote_state" "edge" {
  count   = length(local.edge_records) > 0 ? 1 : 0
  backend = "s3"
  config = {
    bucket       = var.edge_state.bucket
    key          = var.edge_state.key
    region       = var.edge_state.region
    use_lockfile = var.edge_state.use_lockfile
  }
}

resource "cloudflare_dns_record" "this" {
  for_each = var.records

  zone_id = var.zone_id
  name    = each.value.name
  ttl     = each.value.ttl
  type    = each.value.type
  content = each.value.record_class == "vpn-node" ? trimspace(each.value.content) : data.terraform_remote_state.edge[0].outputs.edge_nodes[each.value.node].ip
  proxied = each.value.proxied
  comment = each.value.comment
  tags    = each.value.tags
}
