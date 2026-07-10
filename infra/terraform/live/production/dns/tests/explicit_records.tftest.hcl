mock_provider "cloudflare" {}

variables {
  cloudflare_api_token = "test-token-not-a-production-secret"
  zone_id              = "00000000000000000000000000000000"
  edge_state = {
    bucket = "must-not-be-read-for-explicit-records"
    key    = "must-not-be-read-for-explicit-records"
    region = "eu-central-1"
  }
}

run "explicit_dual_stack_records_do_not_require_edge_state" {
  command = plan

  variables {
    records = {
      de-3-vpn-ipv4 = {
        name         = "de-3.cyber-vpn.org"
        content      = "138.124.115.206"
        record_class = "vpn-node"
        type         = "A"
        ttl          = 1
        proxied      = false
        tags         = ["environment:production", "component:vpn-node", "region:de"]
      }
      de-3-vpn-ipv6 = {
        name         = "de-3.cyber-vpn.org"
        content      = "2a0b:4140:ba84::2"
        record_class = "vpn-node"
        type         = "AAAA"
        ttl          = 1
        proxied      = false
        tags         = ["environment:production", "component:vpn-node", "region:de"]
      }
    }
  }

  assert {
    condition     = length(data.terraform_remote_state.edge) == 0
    error_message = "Explicit DNS records must not read production edge remote state."
  }

  assert {
    condition = (
      cloudflare_dns_record.this["de-3-vpn-ipv4"].content == "138.124.115.206"
      && cloudflare_dns_record.this["de-3-vpn-ipv6"].content == "2a0b:4140:ba84::2"
      && !cloudflare_dns_record.this["de-3-vpn-ipv4"].proxied
      && !cloudflare_dns_record.this["de-3-vpn-ipv6"].proxied
    )
    error_message = "The explicit DE3 A/AAAA pair must remain dual-stack and DNS-only."
  }
}

run "vpn_node_pair_rejects_mixed_cloudflare_proxying" {
  command = plan

  variables {
    records = {
      ipv4 = {
        name         = "de-3.cyber-vpn.org"
        content      = "138.124.115.206"
        record_class = "vpn-node"
        type         = "A"
        ttl          = 1
        proxied      = false
      }
      ipv6 = {
        name         = "de-3.cyber-vpn.org"
        content      = "2a0b:4140:ba84::2"
        record_class = "vpn-node"
        type         = "AAAA"
        ttl          = 1
        proxied      = true
      }
    }
  }

  expect_failures = [var.records]
}

run "edge_records_reject_blank_content" {
  command = plan

  variables {
    records = {
      unsafe = {
        name         = "edge.example.com"
        node         = "edge-prod-01"
        content      = "   "
        record_class = "edge"
        type         = "A"
        proxied      = false
      }
    }
  }

  expect_failures = [var.records]
}

run "edge_records_reject_explicit_content" {
  command = plan

  variables {
    records = {
      unsafe = {
        name         = "edge.example.com"
        node         = "edge-prod-01"
        content      = "192.0.2.44"
        record_class = "edge"
        type         = "A"
        proxied      = false
      }
    }
  }

  expect_failures = [var.records]
}

run "vpn_node_records_reject_blank_content" {
  command = plan

  variables {
    records = {
      unsafe = {
        name         = "de-3.cyber-vpn.org"
        content      = "   "
        record_class = "vpn-node"
        type         = "AAAA"
        proxied      = false
      }
    }
  }

  expect_failures = [var.records]
}
