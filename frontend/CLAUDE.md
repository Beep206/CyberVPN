# Frontend Coding Rules

Rules derived from code review findings. Follow these to prevent recurring issues.

## TypeScript & Type Safety

- **No `any` types.** Always use proper types. For middleware: `NextRequest` from `next/server`.
- **No `@ts-ignore`.** Use typed assertions instead: `(navigator as unknown as { deviceMemory?: number }).deviceMemory ?? 0`
- **Browser timer refs:** Use `useRef<ReturnType<typeof setInterval> | null>(null)` — never `useRef<NodeJS.Timeout>`. Browser `setInterval`/`setTimeout` return `number`, not `NodeJS.Timeout`.
- **`deepMerge` pattern:** No mutation of arguments. Check for `null`, arrays, and use `Object.prototype.hasOwnProperty.call()`. Type as `Record<string, unknown>`, not `any`.

## Memory Leaks

- **Event delegation over per-element listeners.** Use `document.addEventListener('mouseover', ...)` with `.closest()` instead of attaching listeners to each element via MutationObserver. Always clean up in useEffect return.
- **Lenis smooth scroll:** Use `autoRaf: true` option. Never create manual `requestAnimationFrame` loops. `lenis.destroy()` handles all cleanup.
- **AbortController on fetches:** Add timeout via `AbortController` + `setTimeout` for any `fetch()` call that could hang:
  ```typescript
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000);
  // ... fetch with { signal: controller.signal }
  clearTimeout(timeoutId);
  ```

## React Patterns

- **Wrap closures in `useCallback`** when used inside `useEffect`. Add the callback to the effect's dependency array. Prevents stale closures.
- **Remove unused hooks.** Don't import `useTransition` or other hooks unless actively used.
- **No `new Date()` in render.** Use `useState` + `useEffect` to compute dates client-side. This avoids Next.js pre-render errors and hydration mismatches.
- **ErrorBoundary for 3D scenes.** Every `<Canvas>` (Three.js/R3F) must be wrapped in `<ErrorBoundary>`. Use the shared component from `@/shared/ui/error-boundary.tsx`. WebGL crashes must not take down the page.

## Performance

- **Hoist static data to module level.** Arrays and objects that don't depend on props/state (mock data, default configs, constants) must be defined outside the component. Use `SCREAMING_SNAKE_CASE` for module-level constants.
- **CSS custom properties over hardcoded hex.** Use `var(--color-neon-cyan)`, `var(--foreground)` etc. for theme support.

## Imports & Navigation (next-intl)

- **`usePathname`** must be imported from `@/i18n/navigation` (created by `createNavigation`), not from `next/navigation`. The i18n version strips the locale prefix.
- **`useRouter`** must be imported from `@/i18n/navigation` for locale-aware routing.
- **Middleware typing:** `export default async function middleware(request: NextRequest)` — always typed.

## DRY

- **Shared navigation config.** Navigation items used in multiple sidebars go in `shared/config/navigation-items.ts`.
- **No duplicate components.** If a component like `ScrambleText` exists in `@/shared/ui/`, import it. Don't redefine inline.

## Accessibility (a11y)

- **`aria-label`** on all interactive elements (`data-hoverable`, buttons, links without visible text).
- **`aria-expanded`** and **`aria-haspopup`** on dropdown/modal trigger buttons.
- **`<caption className="sr-only">`** inside every `<Table>` for screen reader context.

## Internationalization (i18n)

- **No hardcoded UI strings.** All user-facing text must use `useTranslations()` from `next-intl`.
- **Message files** must exist for all 27 locales in `messages/{locale}/`. When adding a new namespace JSON, copy it to every locale directory.
- **New namespace registration:** Add imports to `i18n/request.ts` in both `Promise.all` and the return object.

## Configuration

- **`package.json` name** must match the workspace purpose (e.g., `vpn-frontend`, not `vpn-admin`).
- **`tsconfig.json` jsx:** Next.js 16 uses `react-jsx` (React automatic runtime). Don't change to `preserve` — Next.js will auto-correct it back.

## context7 Documentation

Before writing code involving these libraries, fetch current docs via context7:
- **next-intl** (`/amannn/next-intl`) — middleware, usePathname, useTranslations
- **Lenis** (`/darkroomengineering/lenis`) — autoRaf, destroy, React usage
- **Next.js 16** (`/vercel/next.js`) — App Router, middleware/proxy, jsx config
