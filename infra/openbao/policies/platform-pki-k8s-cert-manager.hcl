path "pki-k8s/issue/*" {
  capabilities = ["create", "update"]
}

path "pki-k8s/sign/*" {
  capabilities = ["create", "update"]
}

path "pki-k8s/roles/*" {
  capabilities = ["read", "list"]
}

path "pki-k8s/certs" {
  capabilities = ["list"]
}
