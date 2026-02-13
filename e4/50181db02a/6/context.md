# Session Context

## User Prompts

### Prompt 1

<teammate-message teammate_id="team-lead">
You are the query-dedup agent. Your task is to deduplicate React Query hooks and optimize polling intervals.

## Task from TaskList: #3 — Frontend: Query deduplication + polling optimization

## Problem

Two `useServers()` hooks with the same queryKey `['servers']` but different configs:
1. `frontend/src/features/servers/hooks/useServers.ts` — canonical, has `select` transform, staleTime 30s, NO refetchInterval
2. `frontend/src/app/[locale]/(dashboa...

