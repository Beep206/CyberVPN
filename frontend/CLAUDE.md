# Frontend Coding Rules

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
| Lenis | 1.3.17 | `lenis` |
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
- **Lenis smooth scroll:** Use `autoRaf: true`. Never manual `requestAnimationFrame` loops. `lenis.destroy()` handles cleanup.
- **AbortController on fetches:** Add timeout via `AbortController` + `setTimeout` for any `fetch()`:
  ```typescript
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000);
  // fetch with { signal: controller.signal }
  clearTimeout(timeoutId);
  ```

### React Patterns

- **No `new Date()` in render.** Use `useState` + `useEffect` to compute dates client-side.
- **ErrorBoundary for 3D scenes.** Every `<Canvas>` must be in `<ErrorBoundary>` from `@/shared/ui/error-boundary.tsx`.
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
- **Message files** must exist for all 39 locales in `messages/{locale}/`.
- **New namespace registration:** Add imports to `i18n/request.ts` in `Promise.all` and return object.

---

## Next.js 16

### Cache Components (`"use cache"`)
- `cacheComponents: true` is enabled in `next.config.ts` — **nothing is cached by default**
- Use `"use cache"` directive to opt-in at file, component, or function level:
  ```typescript
  // File-level: caches all exports (all must be async)
  "use cache"

  // Component-level
  async function ProductCard({ id }: { id: string }) {
    "use cache"
    const product = await fetchProduct(id);
    return <div>{product.name}</div>;
  }

  // Function-level
  async function getProducts() {
    "use cache"
    return db.products.findMany();
  }
  ```
- Use `cacheLife()` for TTL control: `cacheLife('hours')`, `cacheLife('days')`, or custom profiles
- Wrap dynamic content in `<Suspense>` — required when mixing cached and uncached content
- Pass dynamic content as `children` props to cached components (compositional slots pattern)

### proxy.ts (replaces middleware.ts)
- `middleware.ts` is **deprecated** in Next.js 16; use `proxy.ts` instead
- Rename file and export function to `proxy`:
  ```typescript
  // proxy.ts
  import { NextRequest, NextResponse } from 'next/server';
  export function proxy(request: NextRequest) {
    // routing logic only: rewrites, redirects, headers
    return NextResponse.next();
  }
  ```
- Runs on **Node.js runtime** (not Edge) — full Node API access
- **Do NOT put auth logic in proxy** — use layouts or route handlers instead
- `middleware.ts` still works for Edge runtime but will be removed in a future version

### Async Dynamic APIs
- `params`, `searchParams`, `headers()`, `cookies()` are all **Promises** — must `await`:
  ```typescript
  export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
  }
  ```

### Config
- `reactCompiler: true` and `cacheComponents: true` are **top-level** in `next.config.ts` (not `experimental`)
- Turbopack is the default bundler — no opt-in needed
- Use `next-intl/plugin` wrapper: `withNextIntl(config)`

---

## React 19

### New Hooks
- **`useActionState`** — manages form mutation lifecycle (pending/success/error) in one hook:
  ```typescript
  const [state, formAction, isPending] = useActionState(submitForm, initialState);
  return <form action={formAction}>...</form>;
  ```
- **`useOptimistic`** — instant UI feedback during async operations:
  ```typescript
  const [optimisticItems, addOptimistic] = useOptimistic(items);
  ```
- **`useFormStatus`** — access form pending state from nested components without prop drilling:
  ```typescript
  function SubmitButton() {
    const { pending } = useFormStatus();
    return <button disabled={pending}>Submit</button>;
  }
  ```
- **`use()`** — read promises or context in render (must be inside Suspense):
  ```typescript
  function UserProfile({ userPromise }: { userPromise: Promise<User> }) {
    const user = use(userPromise);
    return <span>{user.name}</span>;
  }
  ```

### Server Components
- Prefer RSC for data fetching — zero JS shipped to client
- `"use client"` only when you need hooks, event handlers, or browser APIs
- `<form action={serverAction}>` for declarative form handling with progressive enhancement

### Other Changes
- `ref` is a regular prop — no `forwardRef` needed:
  ```typescript
  function Input({ ref, ...props }: { ref?: React.Ref<HTMLInputElement> }) {
    return <input ref={ref} {...props} />;
  }
  ```
- Automatic batching extended to promises, `setTimeout`, native event handlers

---

## React Compiler

The React Compiler is **enabled** (`reactCompiler: true`) and auto-memoizes components and hooks.

- **Do NOT manually add** `useMemo`, `useCallback`, or `React.memo` — the compiler handles memoization automatically. Remove existing manual memoization where safe.
- **Exception:** Keep `useCallback` when passing callbacks to non-React APIs (third-party event listeners, imperative libs like Three.js).
- **Follow the Rules of React strictly** — the compiler's static analysis depends on them:
  - Don't mutate props, state, or values during render
  - Don't call hooks conditionally
  - Component functions must be pure during render
- **`"use no memo"`** directive to opt-out a problematic component temporarily
- **Verify in React DevTools** — optimized components show a "Memo" badge
- **Don't rely on memoization for correctness** — only for performance
- **Avoid careless spread operators** — `{ ...obj, newProp }` creates new references even with compiler

---

## TypeScript 5.9

- **`import defer`** — deferred module evaluation (lazy execution on first property access):
  ```typescript
  import defer * as heavyLib from './heavy-module';
  // Module only executes when heavyLib.someFunction() is called
  ```
  Only works with `--module preserve` or `--module esnext`.
- **Strict mode** is enabled — all types must be explicit, no implicit `any`
- **Module resolution:** `bundler` (optimized for Next.js/Turbopack)
- **Path alias:** `@/*` maps to `src/*`

---

## Tailwind CSS 4

### CSS-First Configuration
- **No `tailwind.config.js`** — all config lives in `globals.css` via `@theme`:
  ```css
  @import "tailwindcss";

  @theme {
    --color-neon-cyan: #00ffff;
    --color-matrix-green: #00ff88;
    --font-display: 'Orbitron', sans-serif;
  }
  ```
- Design tokens defined as CSS custom properties are auto-detected as utility classes (`bg-neon-cyan`, `text-matrix-green`, `font-display`)
- `@tailwindcss/postcss` replaces `tailwindcss` + `autoprefixer` in PostCSS config

### Renamed Utilities (v3 → v4)
| v3 | v4 |
|----|-----|
| `shadow` | `shadow-sm` |
| `shadow-sm` | `shadow-xs` |
| `rounded` | `rounded-sm` |
| `rounded-sm` | `rounded-xs` |
| `outline-none` | `outline-hidden` |

### New Features
- **`@custom-variant`** for custom selectors: `@custom-variant dark (&:where(.dark, .dark *))`
- **Container queries** built-in (no plugin)
- **P3 color gamut** for wider color space on modern displays
- **3D transform utilities** available
- **Default border color** is `currentColor` (not gray)
- **Automatic content detection** — no `content` array needed; respects `.gitignore`

---

## Motion 12 (ex Framer Motion)

- **Import from `motion/react`**, not `framer-motion`:
  ```typescript
  import { motion, AnimatePresence } from 'motion/react';
  ```
- **`motion.create()`** for custom components with animation support:
  ```typescript
  const MotionCard = motion.create(Card);
  const MotionSvg = motion.create('svg', { type: 'svg' }); // SVG support
  ```
- **`animateView`** (renamed from `view`) for scroll-triggered animations with `interrupt: "wait"` default
- **`useDragControls`** — `.stop()` and `.cancel()` methods available
- **Timeline positioning:** relative offsets like `<+0.5`, `<-1`
- **CSS logical properties:** `paddingBlock`, `marginInline` default to `px` units
- **`framer-motion-3d` removed** — use native R3F animations for 3D
- **`AnimatePresence`** is now deterministic (no non-deterministic behavior)

---

## React Three Fiber 9 + Drei 10

R3F v9 is the React 19 compatibility release. Compatible with React 19.0–19.2.

### Performance
- **On-demand rendering** for static/resting scenes:
  ```tsx
  <Canvas frameloop="demand">
    {/* Call invalidate() when something needs to update */}
  </Canvas>
  ```
- **Re-use geometries and materials** — don't create new instances per mesh
- **`instancedMesh`** for repeated objects (server dots, particles, network nodes):
  ```tsx
  <instancedMesh args={[geometry, material, count]}>
    <sphereGeometry args={[0.02, 8, 8]} />
    <meshBasicMaterial color="cyan" />
  </instancedMesh>
  ```
- **Disable unused Canvas features** for post-processing:
  ```tsx
  <Canvas gl={{
    powerPreference: "high-performance",
    alpha: false,
    antialias: false,
    stencil: false,
    depth: false
  }} />
  ```
- **ErrorBoundary** required around every `<Canvas>` (WebGL crash protection)
- Use `r3f-perf` in dev for shader/texture/vertex monitoring

### Ecosystem
- `@react-three/drei` — helpers (OrbitControls, Html, Environment, etc.)
- `@react-three/postprocessing` — post-processing effects
- R3F v10 (alpha) adds WebGPU support — not yet stable

---

## TanStack Query v5

### API Changes (v4 → v5)
| v4 | v5 |
|----|-----|
| `isLoading` | `isPending` |
| `cacheTime` | `gcTime` |
| `useErrorBoundary` | `throwOnError` |
| `suspense: true` | `useSuspenseQuery` |

### Best Practices
- **Set `staleTime` explicitly** — default is 0 (always refetch):
  ```typescript
  useQuery({ queryKey: ['servers'], queryFn: fetchServers, staleTime: 5 * 60 * 1000 });
  ```
- **`useSuspenseQuery`** for Suspense integration — component suspends until data ready
- **Optimistic updates** with `onMutate` + `onError` rollback
- **Infinite queries:** `maxPages` option limits stored/refetched pages
- **`combine`** option in `useQueries` to merge multiple query results

## TanStack Table v8

- **Always provide `getRowId`** for stable row identity (not array index):
  ```typescript
  useReactTable({ data, columns, getRowId: (row) => row.id });
  ```
- **Model pipeline:** `getCoreRowModel()` → `getSortedRowModel()` → `getFilteredRowModel()` → `getPaginationRowModel()`
- **TanStack Virtual** for 1000+ rows — only visible rows rendered in DOM
- **Headless** — full control over markup and styles

---

## Zustand 5

- **`useShallow`** required for multi-value selectors (prevents infinite re-render loops):
  ```typescript
  import { useShallow } from 'zustand/react/shallow';
  const { count, name } = useStore(useShallow((s) => ({ count: s.count, name: s.name })));
  ```
- **Export custom hooks**, not the raw store — prevents full-store subscriptions:
  ```typescript
  // Good
  export const useCount = () => useStore((s) => s.count);
  // Bad
  export { useStore };
  ```
- **Slice pattern** for modular stores — split by domain
- **Zustand = client state** (UI, preferences); **TanStack Query = server state** (API data)
- **`createWithEqualityFn`** from `zustand/traditional` if custom equality needed (v5 removed it from `create`)

---

## next-intl 4.7

- **Type registration** via `AppConfig` in `declare module 'next-intl'` (not global scope):
  ```typescript
  declare module 'next-intl' {
    interface AppConfig {
      Messages: typeof import('../messages/en-EN/common.json');
      Locale: (typeof locales)[number];
    }
  }
  ```
- **Strict ICU argument typing** available (opt-in)
- **Session cookie** by default for locale (GDPR compliance)
- **`createNavigation`** exports: `usePathname`, `useRouter`, `Link`, `redirect`, `getPathname`
- **`forcePrefix`** option for `redirect` and `getPathname`
- **39 locales** configured; 5 RTL (ar-SA, he-IL, fa-IR, ur-PK, ku-IQ)
- Import `usePathname` and `useRouter` from `@/i18n/navigation`, not `next/navigation`

---

## Lenis 1.3 (Smooth Scroll)

- **Always `autoRaf: true`** — never manual RAF loops:
  ```typescript
  const lenis = new Lenis({
    duration: 1.2,
    smoothWheel: true,
    autoRaf: true,
  });
  ```
- **Cleanup:** `lenis.destroy()` in useEffect return
- **Mobile:** `syncTouch: false` for better performance
- **Prevent scroll:** `data-lenis-prevent` attribute on elements that should ignore smooth scroll
- **Anchor links** disabled by default while scrolling — handle with `lenis.scrollTo()`

---

## ESLint 9 (Flat Config)

- Config file: `eslint.config.mjs` (not `.eslintrc`)
- Uses `defineConfig` + `globalIgnores` from `eslint/config`
- Presets: `eslint-config-next/core-web-vitals` + `eslint-config-next/typescript`
- Enable `react-hooks/todo` rule to catch React Compiler silent failures

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

Before writing code involving these libraries, fetch current docs via context7.
**Fallback**: If context7 is unavailable or returns insufficient results, use `WebSearch` / `WebFetch` to find the official documentation.
- **next-intl** (`/amannn/next-intl`) — middleware, usePathname, useTranslations
- **Lenis** (`/darkroomengineering/lenis`) — autoRaf, destroy, React usage
- **Next.js 16** (`/vercel/next.js`) — App Router, proxy.ts, cache components
- **Motion** (`/motiondivision/motion`) — animation API, motion.create
- **TanStack Query** (`/TanStack/query`) — useQuery, useMutation patterns
- **Zustand** (`/pmndrs/zustand`) — store patterns, useShallow
