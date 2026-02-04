# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CyberVPN is a VPN business management platform with a cyberpunk-themed admin dashboard. It's structured as an npm workspaces monorepo with the admin panel as the primary development focus.

**Stack**: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, Three.js (React Three Fiber)

## Commands

```bash
# Development (from repo root)
npm install          # Install all workspace dependencies
npm run dev          # Start admin dashboard (localhost:3000)
npm run build        # Production build
npm run lint         # ESLint validation

# Or run directly in admin/
cd admin && npm run dev

# Infrastructure (Docker)
cd infra && docker compose up -d                    # Core services
docker compose --profile monitoring up -d           # Add Prometheus/Grafana
docker compose --profile bot up -d                  # Add Telegram bot
```

## Development Rules

### Library Documentation
**MANDATORY**: When writing or modifying code that uses any library, ALWAYS fetch up-to-date documentation using Context7 MCP tools before implementation.

**Process**:
1. Before using any library function or API, call Context7 to get current documentation
2. **Fallback**: If Context7 is unavailable or returns insufficient results, use `WebSearch` / `WebFetch` to find the official documentation for the library
3. Verify API signatures, parameters, and return types match the documentation
4. Use documented patterns and best practices from the library maintainers

**Example workflow**:
```bash
# REQUIRED before implementing/modifying code with a library
mcp-cli info plugin_context7_context7/query-docs
mcp-cli call plugin_context7_context7/query-docs '{"library": "react", "query": "useEffect dependencies"}'

# FALLBACK — if Context7 fails or returns no results:
# Use WebSearch to find official docs, then WebFetch to read them
```

### Version Management
**PROHIBITED**: Downgrading library versions is strictly forbidden.

- Never reduce package version numbers in `package.json`
- Always upgrade forward or maintain current versions
- If compatibility issues arise, fix the code to work with current versions
- Document version constraints in comments if needed

## Architecture

### Monorepo Structure
- **admin/** - Next.js admin dashboard (primary workspace)
- **apps/** - User-facing apps (landing, portal) - placeholder
- **services/** - Backend services (API, bot, workers) - placeholder
- **packages/** - Shared libraries - placeholder
- **infra/** - Docker Compose stack for local development
- **plan/** - Technical documentation and deployment guides (Russian)

### Admin App Structure (`admin/src/`)

Follows Feature-Sliced Design with Atomic Design for components:

```
app/[locale]/          # Next.js App Router with i18n routing
  (dashboard)/         # Dashboard route group (servers, users, analytics, etc.)

3d/                    # Three.js scenes and shaders
  scenes/GlobalNetwork.tsx  # Main 3D globe visualization

widgets/               # Page-level composed components
  cyber-sidebar.tsx    # Navigation sidebar
  terminal-header.tsx  # Header with FPS, ping, clock, locale switcher
  servers-data-grid.tsx  # TanStack React Table implementation

shared/ui/             # Component library (Atomic Design)
  atoms/               # CypherText, ServerStatusDot, Scanlines
  molecules/           # ServerCard
  organisms/           # Table components

entities/              # Domain models with TypeScript types
  server/model/types.ts  # Server, ServerStatus, VpnProtocol
  user/model/types.ts    # User types

i18n/                  # Internationalization (next-intl)
  config.ts            # 27 locales, RTL support (ar-SA, he-IL, fa-IR)
```

### Key Patterns

**Path alias**: `@/*` maps to `admin/src/*`

**Server Components** (async pages):
```tsx
export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Dashboard' });
  // ...
}
```

**Client Components** use `'use client'` directive with motion for animations

**Type-safe status maps**:
```tsx
type ServerStatus = 'online' | 'offline' | 'warning' | 'maintenance';
const statusColorMap: Record<ServerStatus, string> = { ... };
```

### Design System

Cyberpunk theme with:
- Colors: `--color-matrix-green (#00ff88)`, `--color-neon-cyan (#00ffff)`, `--color-neon-pink (#ff00ff)`
- Fonts: Orbitron (display), JetBrains Mono (code)
- Effects: Scanlines overlay, CypherText scramble animation, 3D card transforms

### Infrastructure

Local Docker stack includes:
- **remnawave** - VPN backend API (port 3000)
- **PostgreSQL 17.7** - Database (port 6767)
- **Valkey/Redis** - Cache (port 6379)
- **Prometheus/Grafana** - Monitoring (optional profile)

### i18n

27 locales configured in `admin/src/i18n/config.ts`. Message files in `admin/messages/{locale}/`. Default: `en-EN`. RTL support for Arabic, Hebrew, Farsi.

## Task Master AI

**Task Master AI is installed globally and used via CLI commands.**

```bash
# Verify global installation
task-master --version

# Common commands
task-master list         # Show all tasks
task-master next         # Get next task
task-master show <id>    # View task details
```

**Full documentation and commands:**
@./.taskmaster/CLAUDE.md

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

<!-- bv-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View issues (launches TUI - avoid in automated sessions)
bv

# CLI commands for agents (use these instead)
bd ready              # Show issues ready to work (no blockers)
bd list --status=open # All open issues
bd show <id>          # Full issue details with dependencies
bd create --title="..." --type=task --priority=2
bd update <id> --status=in_progress
bd close <id> --reason="Completed"
bd close <id1> <id2>  # Close multiple issues at once
bd sync               # Commit and push changes
```

### Workflow Pattern

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `bd close <id>`
5. **Sync**: Always run `bd sync` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)
- **Types**: task, bug, feature, epic, question, docs
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
bd sync                 # Commit beads changes
git commit -m "..."     # Commit code
bd sync                 # Commit any new beads changes
git push                # Push to remote
```

### Best Practices

- Check `bd ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `bd create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always `bd sync` before ending session

<!-- end-bv-agent-instructions -->
