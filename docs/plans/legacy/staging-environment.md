# Staging Environment

Manual-trigger deployment for validating changes before production.

## Trigger

Actions tab > "Deploy to Staging" > Run workflow. Select backend/frontend toggles.

## GitHub Environment Setup

1. Create environment "staging" in repo Settings > Environments
2. Add protection rules: required reviewers (optional)
3. Add environment variables:
   - `STAGING_URL` - staging site URL
   - `STAGING_API_URL` - backend API URL for frontend build
   - `STAGING_SENTRY_DSN` - Sentry DSN for staging

## What Gets Built

| Component | Artifact | Tag |
|-----------|----------|-----|
| Backend | Docker image pushed to GHCR | `staging`, `staging-<sha>` |
| Frontend | Next.js build uploaded as artifact | 7-day retention |

## Deployment Steps (TODO)

The workflow currently builds artifacts only. When staging infra is provisioned:

1. Add SSH/cloud deploy step to `deploy` job
2. Pull Docker image on staging server
3. Run migrations: `docker exec backend alembic upgrade head`
4. Deploy frontend via rsync/CDN upload
5. Verify health: `curl https://staging.example.com/health`

## Rollback

Re-run the workflow with a previous commit SHA, or pull a previous `staging-<sha>` image:

```bash
docker pull ghcr.io/<repo>/backend:staging-<previous-sha>
docker compose up -d
```
