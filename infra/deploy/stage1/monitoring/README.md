# Stage 1 Production Monitoring

This compose stack is the production acceptance monitoring sidecar for
`prod-app-1`. It is intentionally separate from `infra/docker-compose.yml`,
which is a broad local/development stack with placeholder credentials.

The sidecar:

- binds Prometheus, Grafana, and Alertmanager only to `127.0.0.1`;
- joins the existing Stage 1 Docker networks to scrape Remnawave internally;
- renders Remnawave metrics basic-auth credentials on the server from the
  already-running Remnawave container;
- provisions only sanitized repository dashboards/rules.

Deploy it with:

```bash
STAGE1_PROD_HOST=45.87.41.146 \
STAGE1_PROD_USER=root \
STAGE1_PROD_SSH_KEY_FILE="$HOME/.ssh/MainKey2_private_fixed.pem" \
scripts/deploy/stage1-monitoring-deploy.sh
```
