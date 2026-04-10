data "terraform_remote_state" "edge" {
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
  content = data.terraform_remote_state.edge.outputs.edge_nodes[each.value.node].ip
  proxied = each.value.proxied
  comment = each.value.comment
  tags    = each.value.tags
}
