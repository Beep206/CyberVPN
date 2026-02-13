# Session Context

## User Prompts

### Prompt 1

<teammate-message teammate_id="team-lead">
You are the infra-tune agent. Your task is to tune Redis and PostgreSQL in docker-compose.yml.

## Task from TaskList: #6 — Infrastructure: Redis LRU eviction policy

## File to edit: `infra/docker-compose.yml`

## Changes

### 1. Redis/Valkey (lines 80-111, service `remnawave-redis`)

Current command (lines 91-96):
```yaml
command: >
  valkey-server
  --save ""
  --appendonly no
  --maxmemory-policy noeviction
  --loglevel warning
```

Change to:
```...

