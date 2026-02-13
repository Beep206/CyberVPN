# Session Context

## User Prompts

### Prompt 1

<teammate-message teammate_id="team-lead">
You are the proxy-fix agent. Your task is to fix the ~2000ms TTFB issue on API calls going through Next.js.

## Task from TaskList: #2 — Frontend: Fix Next.js proxy TTFB + trailing slash

## Analysis

The next.config.ts already has rewrites configured:
```typescript
async rewrites() {
    return [{
        source: "/api/v1/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
    }];
}
```

BUT there's `trailingSlash: true` on line 30 o...

