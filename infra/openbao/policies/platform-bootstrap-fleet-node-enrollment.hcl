path "auth/cert-fleet/login" {
  capabilities = ["create", "update"]
}

path "auth/approle-bootstrap/role/bootstrap-fleet-node-enrollment/role-id" {
  capabilities = ["read"]
}

path "auth/approle-bootstrap/role/bootstrap-fleet-node-enrollment/secret-id" {
  capabilities = ["create", "update"]
}

path "kv-shared/data/fleet/bootstrap/*" {
  capabilities = ["read"]
}

path "pki-fleet/issue/fleet-node-enrolled" {
  capabilities = ["create", "update"]
}
