# Session Context

## User Prompts

### Prompt 1

<teammate-message teammate_id="team-lead">
You are the auth-fix agent. Your task is to fix the auth race condition where API requests fire before auth refresh completes.

## Task from TaskList: #5 — Frontend: Auth race condition fix

## Problem
HAR analysis shows: API request fires → gets 401 → triggers token refresh → retries → adds ~2s latency. The issue is that during a refresh cycle, other requests still fire and get 401s.

## File to edit: `frontend/src/lib/api/client.ts`

## Curr...

