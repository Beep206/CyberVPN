# CyberVPN Infrastructure Rules

Apply the root completion contract plus these infrastructure rules.

- Local/staging infrastructure may be installed, started and repaired
  autonomously. Production deployment or production data mutation requires an
  explicit task scope, even though the CLI has technical access.
- Never commit secrets. Use environment/secret-manager references and provide
  safe examples.
- Preserve least privilege, network segmentation, health checks, resource
  bounds, rolling/reversible deployment and observability.
- Validate Compose, Terraform, Helm/Kubernetes and CI syntax with the relevant
  native tools. Include rollback and failure evidence for release changes.
