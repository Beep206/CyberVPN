path "kv-apps/data/control-plane/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "kv-shared/data/registry/ghcr" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "kv-shared/data/helix/shared-auth" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "kv-shared/data/integration/remnawave" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
