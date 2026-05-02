path "auth/cert-fleet/login" {
  capabilities = ["create", "update"]
}

path "kv-shared/data/fleet/runtime/*" {
  capabilities = ["read"]
}

path "pki-fleet/issue/fleet-node-enrolled" {
  capabilities = ["create", "update"]
}
