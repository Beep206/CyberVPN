# staging/openbao

This stack provisions the legacy `staging` implementation path for the canonical
`nonprod` OpenBao foundation.

It creates:

- a dedicated Hetzner VM for `openbao-nonprod`;
- an AWS KMS key and alias for auto-unseal;
- a firewall exposing SSH, the OpenBao API/UI listener, and the dedicated metrics listener;
- cloud-init bootstrap that installs pinned OpenBao, writes the systemd unit,
  prepares TLS material, and leaves service start gated on `/etc/openbao/openbao.env`.

Typical flow:

1. Copy `backend.hcl.example` to `backend.hcl`.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Export `TF_VAR_hcloud_token`.
4. Export AWS credentials or `AWS_PROFILE` with permission to manage the non-prod KMS key.
5. Initialize and apply:

```bash
tofu -chdir=infra/terraform/live/staging/openbao init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/openbao plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/openbao apply -var-file=terraform.tfvars
```

After the VM exists, complete host bootstrap with the canonical OpenBao helper:

1. Create `/etc/openbao/openbao.env` from the generated example using the real AWS KMS credentials.
2. Start the service with `systemctl start openbao`.
3. Run the `infra/scripts/openbao_bootstrap.py` workflow to initialize the cluster,
   apply the baseline namespace/auth/mount/policy layout, and optionally configure
   `oidc-operators` and future `jwt-k8s-*` mounts.
4. Enable the file audit device once the cluster is initialized:

```bash
bao audit enable file file_path=/var/log/openbao/audit.log
```

Useful source-controlled inputs for the helper live under:

- `infra/openbao/policies/`
- `infra/openbao/examples/oidc-operators-config.json.example`
- `infra/openbao/examples/jwt-mounts.json.example`

`staging/openbao` is an implementation path only. The canonical environment id and
cluster id remain `nonprod` and `openbao-nonprod`.
