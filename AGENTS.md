# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CyberVPN is a VPN business management platform with a cyberpunk-themed frontend dashboard. It's structured as an npm workspaces monorepo with the frontend app as the primary development focus.

**Stack**: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, Three.js (React Three Fiber)

**IMPORTANT**: In Next.js 16.1+ for this project, you MUST use `src/proxy.ts` instead of `src/middleware.ts` for middleware configuration.

## Commands

```bash
# Development (from repo root)
npm install          # Install all workspace dependencies
npm run dev          # Start frontend app (localhost:3000)
npm run build        # Production build
npm run lint         # ESLint validation

# Or run directly in frontend/
cd frontend && npm run dev

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

## WSL & Antigravity Compatibility

When operating in this repository as an AI agent on a **WSL Ubuntu** environment (especially within **Antigravity**), adhere to these rules:

### 1. Syntax for Chaining Commands
You can safely use standard bash operators like `&&` and `||`.
- **PRO-TIP**: To ensure stability, **DO NOT chain complex commands** (like `add`, `commit`, `sync`, `push`) in a single string. Execute each step as a **separate tool call**. This prevents signal/EOF confusion in Antigravity.

### 2. Terminal Background Jobs
Long-running dev servers can block the AI terminal if not handled properly.
- **MANDATORY**: When launching servers, prefer `nohup` in the background to prevent the UI from hanging.
  Example: `nohup npm run dev > /tmp/next.log 2>&1 &`

### 3. Git Commits
If interactive Husky hooks hang the process:
- **MANDATORY**: Append `--no-verify` to `git commit` commands if problems occur.

### 4. Background Dev Servers
Next.js telemetry prompts can hang the process.
- **MANDATORY**: Disable telemetry: `NEXT_TELEMETRY_DISABLED=1 npm run dev`

### 5. IDE Settings (User Hint)
If hangs persist, ensure that **Terminal > Integrated > Shell Integration** is **DISABLED** in your IDE (Antigravity/VS Code) settings to prevent escape sequence conflicts.

## Architecture

### Monorepo Structure
- **frontend/** - Next.js frontend app (primary workspace)
- **apps/** - User-facing apps (landing, portal) - placeholder
- **services/** - Backend services (API, bot, workers) - placeholder
- **packages/** - Shared libraries - placeholder
- **infra/** - Docker Compose stack for local development
- **docs/plans/** - Technical documentation and deployment guides

### Frontend App Structure (`frontend/src/`)

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
  config.ts            # 38 locales: en-EN, ru-RU, zh-CN, hi-IN, id-ID, vi-VN, th-TH, ja-JP, ko-KR, ar-SA, fa-IR, tr-TR, ur-PK, bn-BD, ms-MY, es-ES, kk-KZ, be-BY, my-MM, uz-UZ, ha-NG, yo-NG, ku-IQ, am-ET, fr-FR, tk-TM, he-IL, de-DE, pt-PT, it-IT, nl-NL, pl-PL, fil-PH, uk-UA, cs-CZ, ro-RO, hu-HU, sv-SE, RTL support (ar-SA, he-IL, fa-IR)
```

### Key Patterns

**Path alias**: `@/*` maps to `frontend/src/*`

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

38 locales: en-EN, ru-RU, zh-CN, hi-IN, id-ID, vi-VN, th-TH, ja-JP, ko-KR, ar-SA, fa-IR, tr-TR, ur-PK, bn-BD, ms-MY, es-ES, kk-KZ, be-BY, my-MM, uz-UZ, ha-NG, yo-NG, ku-IQ, am-ET, fr-FR, tk-TM, he-IL, de-DE, pt-PT, it-IT, nl-NL, pl-PL, fil-PH, uk-UA, cs-CZ, ro-RO, hu-HU, sv-SE configured in `frontend/src/i18n/config.ts`. Message files in `frontend/messages/{locale}/`. Default: `en-EN`. RTL support for Arabic, Hebrew, Farsi.
