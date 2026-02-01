# Admin Dashboard Coding Rules

Rules derived from code review findings and stack best practices.

## Stack & Versions

| Library | Version | Import |
|---------|---------|--------|
| Next.js | 16.1.5 | `next` |
| React | 19.2.x | `react` |
| TypeScript | 5.9.2 | — |
| Tailwind CSS | 4.1.18 | `@tailwindcss/postcss` |
| React Compiler | 1.0.0 | `babel-plugin-react-compiler` |
| Three.js | 0.174 | `three` |
| @react-three/fiber | 9.1 | `@react-three/fiber` |
| @react-three/drei | 10.7 | `@react-three/drei` |
| Motion | 12.29 | `motion/react` |
| next-intl | 4.7 | `next-intl` |
| TanStack Query | 5.87 | `@tanstack/react-query` |
| TanStack Table | 8.21 | `@tanstack/react-table` |
| Zustand | 5.0.10 | `zustand` |
| Lucide React | 0.563 | `lucide-react` |
| ESLint | 9 | flat config (`eslint.config.mjs`) |

---

## Code Review Rules (Mandatory)

### TypeScript & Type Safety

- **No `any` types.** Always use proper types. For proxy/middleware: `NextRequest` from `next/server`.
- **No `@ts-ignore`.** Use typed assertions: `(navigator as unknown as { deviceMemory?: number }).deviceMemory ?? 0`
- **Browser timer refs:** Use `useRef<ReturnType<typeof setInterval> | null>(null)` — never `useRef<NodeJS.Timeout>`.
- **`deepMerge` pattern:** No mutation of arguments. Check for `null`, arrays. Type as `Record<string, unknown>`, not `any`.

### Memory Leaks

- **Event delegation over per-element listeners.** Use `document.addEventListener('mouseover', ...)` with `.closest()` instead of MutationObserver. Always clean up in useEffect return.
- **AbortController on fetches:** Add timeout via `AbortController` + `setTimeout` for any `fetch()`:
  ```typescript
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000);
  // fetch with { signal: controller.signal }
  clearTimeout(timeoutId);
  ```

### React Patterns

- **No `new Date()` in render.** Use `useState` + `useEffect` to compute dates client-side.
- **ErrorBoundary for 3D scenes.** Every `<Canvas>` must be in `<ErrorBoundary>`.
- **Remove unused hooks.** Don't import hooks unless actively used.

### Performance

- **Hoist static data to module level.** Use `SCREAMING_SNAKE_CASE` for module-level constants.
- **CSS custom properties over hardcoded hex.** Use `var(--color-neon-cyan)` etc.

### DRY

- **Shared navigation config** in `shared/config/navigation-items.ts`.
- **No duplicate components.** Import from `@/shared/ui/` — don't redefine inline.

### Accessibility (a11y)

- **`aria-label`** on all interactive elements.
- **`aria-expanded`** and **`aria-haspopup`** on dropdown/modal triggers.
- **`<caption className="sr-only">`** inside every `<Table>`.

### Internationalization (i18n)

- **No hardcoded UI strings.** Use `useTranslations()` from `next-intl`.
- **Message files** must exist for all 41 locales in `messages/{locale}/`.
- **New namespace registration:** Add imports to `i18n/request.ts` in `Promise.all` and return object.

---

## Next.js 16

### Cache Components (`"use cache"`)
- `cacheComponents: true` is enabled — **nothing cached by default**
- Use `"use cache"` directive to opt-in at file, component, or function level:
  ```typescript
  "use cache" // file-level: caches all exports (all must be async)

  async function DataCard({ id }: { id: string }) {
    "use cache" // component-level
    const data = await fetchData(id);
    return <div>{data.name}</div>;
  }
  ```
- Use `cacheLife()` for TTL: `cacheLife('hours')`, `cacheLife('days')`, or custom profiles
- Wrap dynamic content in `<Suspense>`
- Compositional slots: pass dynamic content as `children` to cached components

### proxy.ts (replaces middleware.ts)
- `middleware.ts` is **deprecated**; use `proxy.ts`:
  ```typescript
  import { NextRequest, NextResponse } from 'next/server';
  export function proxy(request: NextRequest) {
    return NextResponse.next();
  }
  ```
- Runs on **Node.js runtime** (not Edge)
- **No auth logic in proxy** — use layouts or route handlers

### Async Dynamic APIs
- `params`, `searchParams`, `headers()`, `cookies()` are **Promises** — must `await`:
  ```typescript
  export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
  }
  ```

### Config
- `reactCompiler: true` and `cacheComponents: true` are **top-level** (not `experimental`)
- Turbopack is default bundler
- `next-intl/plugin` wrapper: `withNextIntl(config)`

---

## React 19

### New Hooks
- **`useActionState`** — form mutation lifecycle (pending/success/error):
  ```typescript
  const [state, formAction, isPending] = useActionState(submitForm, initialState);
  return <form action={formAction}>...</form>;
  ```
- **`useOptimistic`** — instant UI feedback during async ops:
  ```typescript
  const [optimisticItems, addOptimistic] = useOptimistic(items);
  ```
- **`useFormStatus`** — form pending state from nested components (no prop drilling):
  ```typescript
  function SubmitButton() {
    const { pending } = useFormStatus();
    return <button disabled={pending}>Submit</button>;
  }
  ```
- **`use()`** — read promises/context in render (inside Suspense):
  ```typescript
  const user = use(userPromise);
  ```

### Server Components
- Prefer RSC for data fetching — zero JS shipped
- `"use client"` only for hooks, event handlers, browser APIs
- `<form action={serverAction}>` for declarative form handling

### Other
- `ref` is a regular prop — no `forwardRef` needed
- Automatic batching for promises, `setTimeout`, native events

---

## React Compiler

Enabled via `reactCompiler: true` — auto-memoizes components and hooks.

- **Do NOT manually add** `useMemo`, `useCallback`, or `React.memo` — compiler handles it
- **Exception:** Keep `useCallback` for non-React APIs (Three.js, imperative libs)
- **Follow Rules of React strictly** — compiler depends on them
- **`"use no memo"`** to opt-out problematic components
- **React DevTools** — optimized components show "Memo" badge
- **Avoid careless spread operators** — `{ ...obj, newProp }` creates new references

---

## TypeScript 5.9

- **`import defer`** for lazy module execution:
  ```typescript
  import defer * as heavyLib from './heavy-module';
  ```
- **Strict mode** enabled — no implicit `any`
- **Module resolution:** `bundler`
- **Path alias:** `@/*` → `src/*`

---

## Tailwind CSS 4

### CSS-First Configuration
- **No `tailwind.config.js`** — config via `@theme` in `globals.css`:
  ```css
  @import "tailwindcss";
  @theme {
    --color-neon-cyan: #00ffff;
    --font-display: 'Orbitron', sans-serif;
  }
  ```
- CSS custom properties auto-generate utility classes

### Renamed Utilities (v3 → v4)
| v3 | v4 |
|----|-----|
| `shadow` | `shadow-sm` |
| `shadow-sm` | `shadow-xs` |
| `rounded` | `rounded-sm` |
| `rounded-sm` | `rounded-xs` |
| `outline-none` | `outline-hidden` |

### New Features
- **`@custom-variant`** for custom selectors (dark mode)
- **Container queries** built-in
- **P3 color gamut** available
- **3D transform utilities**
- **Default border color:** `currentColor`
- **Automatic content detection** — respects `.gitignore`

---

## Motion 12 (ex Framer Motion)

- **Import from `motion/react`**, not `framer-motion`
- **`motion.create()`** for custom components: `motion.create(Card)`, `motion.create('svg', { type: 'svg' })`
- **`animateView`** (renamed from `view`) for scroll-triggered animations
- **`useDragControls`** — `.stop()` and `.cancel()` methods
- **Timeline positioning:** `<+0.5`, `<-1` syntax
- **`framer-motion-3d` removed** — use native R3F animations
- **`AnimatePresence`** is deterministic

---

## React Three Fiber 9 + Drei 10

R3F v9 = React 19 compatibility (19.0–19.2).

### Performance
- **On-demand rendering:** `<Canvas frameloop="demand">` + `invalidate()`
- **Re-use geometries/materials** across meshes
- **`instancedMesh`** for repeated objects (server dots, particles)
- **Disable unused Canvas features:**
  ```tsx
  <Canvas gl={{ powerPreference: "high-performance", alpha: false, antialias: false, stencil: false, depth: false }} />
  ```
- **ErrorBoundary** around every `<Canvas>`
- **`r3f-perf`** in dev for monitoring

---

## TanStack Query v5

| v4 | v5 |
|----|-----|
| `isLoading` | `isPending` |
| `cacheTime` | `gcTime` |
| `useErrorBoundary` | `throwOnError` |
| `suspense: true` | `useSuspenseQuery` |

- **Set `staleTime` explicitly** (default 0):
  ```typescript
  useQuery({ queryKey: ['servers'], queryFn: fetchServers, staleTime: 5 * 60 * 1000 });
  ```
- **`useSuspenseQuery`** for Suspense integration
- **`maxPages`** for infinite queries
- **`combine`** option in `useQueries`

## TanStack Table v8

- **Always `getRowId`** for stable row identity (not index)
- **Pipeline:** `getCoreRowModel()` → `getSortedRowModel()` → `getFilteredRowModel()` → `getPaginationRowModel()`
- **TanStack Virtual** for 1000+ rows
- **Headless** — full control over markup/styles

---

## Zustand 5

- **`useShallow`** for multi-value selectors:
  ```typescript
  import { useShallow } from 'zustand/react/shallow';
  const { count, name } = useStore(useShallow((s) => ({ count: s.count, name: s.name })));
  ```
- **Export custom hooks**, not raw store
- **Slice pattern** for modular stores
- **Zustand = client state**; **TanStack Query = server state**
- **`createWithEqualityFn`** from `zustand/traditional` if custom equality needed

---

## next-intl 4.7

- **Type registration** via `AppConfig`:
  ```typescript
  declare module 'next-intl' {
    interface AppConfig {
      Messages: typeof import('../messages/en-EN/common.json');
      Locale: (typeof locales)[number];
    }
  }
  ```
- **Strict ICU argument typing** (opt-in)
- **Session cookie** by default (GDPR)
- **`createNavigation`** exports: `usePathname`, `useRouter`, `Link`, `redirect`
- Import navigation hooks from `@/i18n/navigation`, not `next/navigation`
- **41 locales**; 5 RTL (ar-SA, he-IL, fa-IR, ur-PK, ku-IQ)

---

## ESLint 9 (Flat Config)

- Config: `eslint.config.mjs` (not `.eslintrc`)
- `defineConfig` + `globalIgnores` from `eslint/config`
- Presets: `eslint-config-next/core-web-vitals` + `eslint-config-next/typescript`
- Enable `react-hooks/todo` to catch React Compiler failures

---

## Performance & Architecture Anti-Patterns (Lessons Learned)

Rules from skills audits (next-best-practices + vercel-react-best-practices). These are common mistakes found in this codebase — do not repeat them.

### 1. React.cache() on i18n Loaders (CRITICAL)
- Wrap `loadLocaleMessages` / `loadMessages` in `i18n/request.ts` with `cache()` from `react`
- Deduplicates per-request when the same locale is loaded multiple times (base + current)
- **Anti-pattern:** calling async message loaders without `cache()` → duplicate fetches per render pass

### 2. useRef for High-Frequency Transient Values (MEDIUM)
- FPS counters, ping values, clocks updating every frame/second: use `useRef<HTMLSpanElement>` + direct `textContent` mutation
- **Anti-pattern:** `useState` for values changing 10–60×/sec → full component re-renders each time
- **Pattern:** `const fpsRef = useRef<HTMLSpanElement>(null)` → `fpsRef.current!.textContent = value`

### 3. Pre-Normalize Search Data at Module Level (LOW)
- For filterable lists (languages, users): pre-compute `.toLowerCase()` once in a module-level constant
- **Anti-pattern:** `.toLowerCase()` on every keystroke inside filter callbacks
- **Pattern:** `LANGUAGES_RAW.map(l => ({ ...l, _searchName: l.name.toLowerCase() }))`

### 4. startTransition for Search/Filter Inputs (LOW)
- Wrap non-urgent state updates (search queries, filter text) in `startTransition`
- **Anti-pattern:** `onChange={(e) => setQuery(e.target.value)}` blocks typing on large lists
- **Pattern:** `onChange={(e) => startTransition(() => setQuery(e.target.value))}`

### 5. content-visibility for Scrollable Lists (LOW)
- Add `[content-visibility:auto] [contain-intrinsic-size:auto_<height>px]` to repeated list items in scroll containers
- **Anti-pattern:** rendering all notification/list items even when off-screen
- Only useful for lists with 10+ items in a scrollable container

### 6. Stable Keys for Three.js Mapped Elements (MEDIUM)
- Use coordinate-based or ID-based keys, never array index (`key={i}`)
- **Anti-pattern:** `key={i}` → full unmount/remount when array order changes
- **Pattern:** `` key={`${conn.from.lat},${conn.from.lng}-${conn.to.lat},${conn.to.lng}`} ``

### 7. Tailwind Classes Over Inline Styles for Colors (LOW)
- Use Tailwind conditional classes instead of `style={{ backgroundColor: ... }}`
- **Anti-pattern:** `style={{ backgroundColor: load > 80 ? '#...' : '#...' }}` bypasses design system
- **Pattern:** `` className={`h-full ${load > 80 ? 'bg-server-warning' : 'bg-matrix-green'}`} ``

### 8. Server Actions Need Auth (HIGH)
- Every `'use server'` action must call `requireAuth()` before any mutation
- **Anti-pattern:** server actions without auth check are publicly callable
- **Pattern:** create `shared/lib/actions.ts` with `requireAuth()`, import in all server actions

### 9. Required Next.js File Conventions (HIGH)
Every route group MUST have:
- `error.tsx` — error boundary for the route
- `not-found.tsx` — 404 handling
- `loading.tsx` — Suspense fallback
- `layout.tsx` with `generateMetadata` — SEO metadata
- Root must have: `robots.ts`, `sitemap.ts`, `opengraph-image.tsx`
- **Anti-pattern:** missing these files → no error handling, no SEO, no loading states

### 10. Remove Unused Imports Aggressively
- Don't leave unused imports (hooks, components, types) in files
- **Anti-pattern:** importing `Bell`, `cn`, `router`, `pathname` etc. and never using them
- ESLint catches some; manually verify after every refactoring session

---

## context7 Documentation

Fetch current docs via context7 before writing code.
**Fallback**: If context7 is unavailable or returns insufficient results, use `WebSearch` / `WebFetch` to find the official documentation.
- **next-intl** (`/amannn/next-intl`)
- **Next.js 16** (`/vercel/next.js`)
- **Motion** (`/motiondivision/motion`)
- **TanStack Query** (`/TanStack/query`)
- **Zustand** (`/pmndrs/zustand`)
