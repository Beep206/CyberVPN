# Session Context

## User Prompts

### Prompt 1

<teammate-message teammate_id="team-lead">
You are the backend-cache agent. Your task is to implement a Redis response cache layer for API endpoints and fix redirect_slashes.

## Task from TaskList: #1 — Backend: Redis response cache + redirect_slashes fix

## What to do

### 1. Create `backend/src/infrastructure/cache/response_cache.py`

Create a generic async Redis cache helper:

```python
"""Redis-backed response cache for API endpoints."""

import json
import logging
from collections.abc i...

