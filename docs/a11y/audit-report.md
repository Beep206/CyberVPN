# CyberVPN Accessibility Audit Report (A11Y-01.1)

**Date:** 2026-02-10
**Scope:** Static code audit of CyberVPN frontend (`frontend/src/`)
**Standard:** WCAG 2.1 Level AA
**Auditor:** UI/UX & Brand Designer (automated static analysis)

---

## Executive Summary

The CyberVPN frontend demonstrates **above-average accessibility baseline** for a cyberpunk-themed dashboard. The auth pages include `aria-label`, `aria-invalid`, `aria-describedby`, `role="alert"` on errors, and focus management for error messages. The `CyberInput` component is a well-structured accessible form input with proper `htmlFor`/`id` binding.

However, the audit uncovered **37 issues across 24 files**, including several critical and serious findings that would prevent WCAG 2.1 AA compliance. The most impactful categories are:

| Severity | Count |
|----------|-------|
| Critical | 5 |
| Serious  | 12 |
| Moderate | 13 |
| Minor    | 7 |

---

## Table of Contents

1. [Global / Layout Issues](#1-global--layout-issues)
2. [Navigation (Sidebar)](#2-navigation-sidebar)
3. [Terminal Header](#3-terminal-header)
4. [Auth Pages (Login / Register)](#4-auth-pages-login--register)
5. [Dashboard Layout & Pages](#5-dashboard-layout--pages)
6. [Data Grids (Servers / Users)](#6-data-grids-servers--users)
7. [Modal Component](#7-modal-component)
8. [Notification Dropdown](#8-notification-dropdown)
9. [Shared UI Components](#9-shared-ui-components)
10. [Color Contrast Concerns](#10-color-contrast-concerns)
11. [Landing Page](#11-landing-page)
12. [Footer](#12-footer)

---

## 1. Global / Layout Issues

### 1.1 [CRITICAL] No skip-navigation link
- **WCAG:** 2.4.1 Bypass Blocks (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/layout.tsx`
- **Line:** 57-90 (entire layout)
- **Description:** The root layout renders no skip-navigation link. Users relying on keyboard navigation must tab through the entire sidebar and header on every page load before reaching main content.
- **Fix:** Add a visually-hidden skip link as the first focusable child of `<body>`:
  ```tsx
  <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute ...">
    Skip to main content
  </a>
  ```
  And assign `id="main-content"` to the `<main>` element.

### 1.2 [SERIOUS] No `dir` attribute for RTL locales
- **WCAG:** 1.3.2 Meaningful Sequence (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/layout.tsx`
- **Line:** 58
- **Description:** The `<html>` element only sets `lang={locale}` but never sets `dir="rtl"` for RTL locales (ar-SA, he-IL, fa-IR, ur-PK, ku-IQ). The project supports 41 locales including 5 RTL ones.
- **Fix:** Compute `dir` from locale and apply: `<html lang={locale} dir={isRtl ? 'rtl' : 'ltr'}>`

### 1.3 [MODERATE] Scanline overlay may reduce readability
- **WCAG:** 1.4.3 Contrast Minimum (Level AA)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/layout.tsx`
- **Line:** 84
- **Description:** A fixed `z-50 scanline opacity-20` overlay is rendered over the entire page. While `opacity-20` is low, it reduces effective contrast on all text beneath it. This interacts with the `z-50` Scanlines component in the dashboard layout as well.
- **Fix:** Ensure combined scanline overlays do not reduce effective text contrast below 4.5:1. Consider making scanlines purely decorative with `aria-hidden="true"` and verifying final composite contrast.

### 1.4 [MINOR] Missing `<meta name="viewport">` explicit check
- **WCAG:** 1.4.10 Reflow (Level AA)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/layout.tsx`
- **Description:** Next.js automatically adds a viewport meta tag, but there is no explicit `viewport` export. Ensure `maximum-scale` is not restricted (it should not be `1.0` as this disables pinch-to-zoom).
- **Fix:** Verify the generated meta viewport allows zooming up to at least 200%.

---

## 2. Navigation (Sidebar)

### 2.1 [SERIOUS] Missing `aria-label` on `<nav>` elements
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **Files:**
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/cyber-sidebar.tsx` line 34
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/mobile-sidebar.tsx` line 71
- **Description:** Both `<nav>` elements lack an `aria-label` or `aria-labelledby` attribute. Screen reader users cannot distinguish between multiple navigation landmarks.
- **Fix:** Add `aria-label="Main navigation"` to both nav elements.

### 2.2 [SERIOUS] Missing `aria-current="page"` on active nav links
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **Files:**
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/cyber-sidebar.tsx` lines 41-91
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/mobile-sidebar.tsx` lines 78-106
- **Description:** Active navigation items are indicated only visually (cyan highlight, border, dot). There is no `aria-current="page"` attribute on the active link.
- **Fix:** Add `aria-current={isActive ? 'page' : undefined}` to each `<Link>` component.

### 2.3 [MODERATE] CypherText scramble animation harms screen readers
- **WCAG:** 1.3.1 Info and Relationships (Level A), 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/shared/ui/atoms/cypher-text.tsx` lines 89-96
- **Description:** The `CypherText` component renders scrambled characters during its animation. Screen readers will announce the scrambled text rather than the final value. The component renders a plain `<span>` with no `aria-label`.
- **Fix:** Add `aria-label={text}` to the outer `<span>` so the final text is always accessible. Optionally add `aria-hidden="true"` to the animated display text and render the real text in a visually-hidden span.

### 2.4 [MODERATE] Decorative glitch overlay text not hidden from AT
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/cyber-sidebar.tsx` lines 74-79
- **Description:** Decorative duplicate text elements (pink and cyan glitch overlays) are visible to assistive technology. Screen readers will announce the link label three times.
- **Fix:** Add `aria-hidden="true"` to both decorative `<span>` elements at lines 74 and 77.

### 2.5 [MODERATE] Sidebar `<aside>` missing `aria-label`
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/cyber-sidebar.tsx` line 25
- **Description:** The `<aside>` element is not labeled.
- **Fix:** Add `aria-label="Sidebar"` or a more descriptive label.

---

## 3. Terminal Header

### 3.1 [SERIOUS] Menu button has no accessible label
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/terminal-header.tsx` lines 77-81
- **Description:** The hamburger menu button (wrapped in `MagneticButton` + `div`) is a `<div>` with a `Menu` icon but no `aria-label`, no `role="button"`, and no keyboard handler. It is not an interactive element.
- **Fix:** Replace the `<div>` with a `<button>` element and add `aria-label="Open menu"`. The `MagneticButton` wrapper also has no semantic role.

### 3.2 [MODERATE] Live data (FPS, ping, time) not in `aria-live` regions
- **WCAG:** 4.1.3 Status Messages (Level AA)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/terminal-header.tsx` lines 83-93
- **Description:** FPS and ping values update frequently via ref mutations. These are informational status displays. While using `useRef` + `textContent` is correct for performance, screen readers cannot discover changes. However, these updates are cosmetic and announcing them would be noisy.
- **Fix:** This is acceptable as-is since high-frequency updates would degrade AT experience. Ensure these are labeled with `aria-label` for static discovery.

### 3.3 [MINOR] Network status pulse icon has no text alternative
- **WCAG:** 1.1.1 Non-text Content (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/terminal-header.tsx` lines 96-99
- **Description:** The `Wifi` icon is purely decorative alongside the "NET UPLINK" text, which is acceptable. But on mobile the text is hidden (`hidden md:inline`), leaving only the icon with no text alternative.
- **Fix:** Add `aria-label` to the container or add a `sr-only` span for mobile.

---

## 4. Auth Pages (Login / Register)

### 4.1 [MINOR] Password toggle button has `tabIndex={-1}`
- **WCAG:** 2.1.1 Keyboard (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/features/auth/components/CyberInput.tsx` line 101
- **Description:** The "Show/Hide password" toggle has `tabIndex={-1}`, making it unreachable by keyboard. While this may be intentional UX, keyboard-only users cannot toggle password visibility.
- **Fix:** Remove `tabIndex={-1}` to allow keyboard access, or document the intentional exclusion.

### 4.2 [MINOR] Registration mode toggle group lacks `role="radiogroup"`
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(auth)/register/page.tsx` lines 97-124
- **Description:** The Email/Username toggle is implemented with two buttons but lacks semantic group role. The selected state is communicated only through visual styling.
- **Fix:** Add `role="radiogroup"` to the container and `role="radio"` + `aria-checked={isActive}` to each button. Alternatively, use `aria-pressed` on the buttons.

### 4.3 [MODERATE] "Remember me" checkbox has redundant `aria-label`
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(auth)/login/page.tsx` lines 129-139
- **Description:** The checkbox has both a wrapping `<label>` element (which provides an accessible name via its text content) and an `aria-label`. The `aria-label` overrides the visible label text. This is not a violation but can cause confusion if they diverge.
- **Fix:** Remove `aria-label` from the checkbox since the wrapping `<label>` already provides the accessible name.

### 4.4 [MODERATE] Custom checkbox (register page) uses `sr-only` with no visible focus ring
- **WCAG:** 2.4.7 Focus Visible (Level AA)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(auth)/register/page.tsx` lines 203-226
- **Description:** The terms checkbox input is `sr-only` (visually hidden), with a decorative `<div>` sibling showing `peer-focus:ring-2`. The `peer-focus` approach relies on the hidden input receiving focus and the adjacent sibling showing the ring. This is fragile; verify that the focus ring is actually visible when tabbing to this element.
- **Fix:** Test and verify that `peer-focus:ring-2` actually displays on the visible checkbox proxy.

### 4.5 [POSITIVE] Auth form error handling is well-implemented
- **Description:** Both login and register pages use `role="alert"`, `ref` + focus management for errors, `aria-invalid`, and `aria-describedby` connecting inputs to error messages. This is solid accessibility practice.

---

## 5. Dashboard Layout & Pages

### 5.1 [CRITICAL] `<main>` element missing `id` for skip navigation
- **WCAG:** 2.4.1 Bypass Blocks (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(dashboard)/layout.tsx` line 21
- **Description:** The `<main>` element has no `id` attribute. Even if a skip link were added, there is no target.
- **Fix:** Add `id="main-content"` and optionally `tabIndex={-1}` to the `<main>` element.

### 5.2 [SERIOUS] Dashboard page headings hierarchy
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx`
- **Description:** The page has an `<h1>` for the title (line 22), `<h2>` for stats (lines 34, 41, 46), and another `<h2>` for "Server Matrix" (line 52). This hierarchy is correct. However, no `<section>` landmarks wrap these groups.
- **Fix:** Wrap logical sections in `<section>` elements with `aria-labelledby` pointing to their respective headings for improved navigation.

### 5.3 [MODERATE] 3D background has no fallback text
- **WCAG:** 1.1.1 Non-text Content (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/(dashboard)/layout.tsx` line 26
- **Description:** The `GlobalNetworkWrapper` (3D canvas) is purely decorative but is not explicitly hidden from AT.
- **Fix:** Add `aria-hidden="true"` to the 3D background container.

---

## 6. Data Grids (Servers / Users)

### 6.1 [CRITICAL] Tables missing `<caption>` element
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **Files:**
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/servers-data-grid.tsx` lines 137-162
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/users-data-grid.tsx` lines 130-155
- **Description:** Both data tables rendered by `<Table>` have no `<caption>` element. Screen readers cannot announce the purpose of these tables. The project's own `CLAUDE.md` mandates `<caption className="sr-only">` inside every `<Table>`.
- **Fix:** Add a visually-hidden `<caption>` to each table:
  ```tsx
  <Table>
    <caption className="sr-only">{t('tableCaption')}</caption>
    ...
  </Table>
  ```
  The `Table` component in `/home/beep/projects/VPNBussiness/frontend/src/shared/ui/organisms/table.tsx` should be updated to accept a `caption` prop.

### 6.2 [SERIOUS] Sortable column headers not keyboard-accessible
- **WCAG:** 2.1.1 Keyboard (Level A)
- **Files:**
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/servers-data-grid.tsx` lines 139-149
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/users-data-grid.tsx` lines 131-142
- **Description:** Table headers render as `<th>` elements via `flexRender`. If columns are sortable, users should be able to activate sorting via keyboard. There are no `onClick`, `onKeyDown`, `role="columnheader"`, or `aria-sort` attributes.
- **Fix:** Add click/keydown handlers to sortable headers. Set `aria-sort="ascending"` / `aria-sort="descending"` / `aria-sort="none"` based on current sort state. Make headers focusable with `tabIndex={0}`.

### 6.3 [SERIOUS] "Deploy Node" button missing accessible name context
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/servers-data-grid.tsx` line 131
- **Description:** The "Deploy Node" button is a bare `<button>` element (not using the `Button` component) with no `type` attribute. Without `type="button"`, it defaults to `type="submit"` inside a form context.
- **Fix:** Add `type="button"` to the deploy button.

### 6.4 [SERIOUS] Users search input has no label
- **WCAG:** 1.3.1 Info and Relationships (Level A), 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/users-data-grid.tsx` lines 122-126
- **Description:** The search input has a `placeholder` but no `<label>`, `aria-label`, or `aria-labelledby`. The placeholder disappears on focus, leaving no persistent label.
- **Fix:** Add `aria-label={t('searchPlaceholder')}` to the input.

### 6.5 [MODERATE] Load percentage bars missing accessible value
- **WCAG:** 1.1.1 Non-text Content (Level A)
- **Files:**
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/servers-data-grid.tsx` lines 76-86
  - `/home/beep/projects/VPNBussiness/frontend/src/widgets/users-data-grid.tsx` lines 64-76
- **Description:** Progress bars are rendered as plain `<div>` elements. While the percentage text is visible, the progress bar itself lacks `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, and `aria-valuemax`.
- **Fix:** Add `role="progressbar"` with appropriate ARIA value attributes to the outer bar container.

### 6.6 [MODERATE] ServerStatusDot has no accessible text
- **WCAG:** 1.1.1 Non-text Content (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/shared/ui/atoms/server-status-dot.tsx` lines 17-33
- **Description:** The `ServerStatusDot` component renders colored dots with no text alternative. The status label is rendered separately in the servers grid, but when used standalone (e.g., in `ServerCard`), there is no accessible name.
- **Fix:** Add `role="img"` and `aria-label` prop to the component, or a `sr-only` span with the status text.

---

## 7. Modal Component

### 7.1 [CRITICAL] Modal has no `role="dialog"` or `aria-modal`
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/shared/ui/modal.tsx` lines 82-123
- **Description:** The modal container is a `<motion.div>` without `role="dialog"` or `aria-modal="true"`. Screen readers will not announce it as a dialog. The `<h2>` title exists but is not connected via `aria-labelledby`.
- **Fix:** Add `role="dialog"`, `aria-modal="true"`, and `aria-labelledby` pointing to the title element's `id`.

### 7.2 [SERIOUS] Modal has no focus trap
- **WCAG:** 2.4.3 Focus Order (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/shared/ui/modal.tsx`
- **Description:** The modal handles Escape key (line 55) and prevents body scroll (line 37), but there is no focus trap. Users can Tab out of the modal into background content. Focus is also not moved to the modal when it opens.
- **Fix:** Implement focus trapping using a library (e.g., `@headlessui/react` FocusTrap) or manual implementation. Move focus to the first focusable element or the modal container on open. Return focus to the trigger element on close.

### 7.3 [SERIOUS] Close button missing `aria-label`
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/shared/ui/modal.tsx` lines 100-105
- **Description:** The close button renders only an `<X>` icon with no `aria-label`.
- **Fix:** Add `aria-label="Close dialog"` or equivalent localized string.

---

## 8. Notification Dropdown

### 8.1 [SERIOUS] Bell button missing `aria-label` and `aria-expanded`
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/features/notifications/notification-dropdown.tsx` lines 56-66
- **Description:** The notification bell `Button` has no `aria-label`, no `aria-expanded`, and no `aria-haspopup`. Screen readers announce it only as "button" with no purpose indication.
- **Fix:** Add:
  ```tsx
  aria-label={`Notifications, ${unreadCount} unread`}
  aria-expanded={isOpen}
  aria-haspopup="true"
  ```

### 8.2 [MODERATE] Notification dropdown panel not labeled
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/features/notifications/notification-dropdown.tsx` lines 70-126
- **Description:** The dropdown panel has no `role` attribute (should be `role="menu"` or `role="dialog"` depending on behavior) and no `aria-label`.
- **Fix:** Add `role="dialog"` with `aria-label="Notifications"` or use a proper menu pattern.

### 8.3 [MODERATE] Dropdown closes only on mouse click outside, not on Escape
- **WCAG:** 2.1.1 Keyboard (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/features/notifications/notification-dropdown.tsx` lines 42-50
- **Description:** The close-on-click-outside handler uses `mousedown` only. There is no Escape key handler for keyboard users.
- **Fix:** Add a `keydown` listener for Escape to close the dropdown.

### 8.4 [MODERATE] Notification items are not focusable
- **WCAG:** 2.1.1 Keyboard (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/features/notifications/notification-dropdown.tsx` lines 89-116
- **Description:** Notification items are `<div>` elements with `cursor-pointer` styling but no `tabIndex`, `role`, or keyboard handlers. They are not keyboard-navigable.
- **Fix:** Make notification items focusable `<button>` or `<a>` elements, or add `tabIndex={0}`, `role="button"`, and `onKeyDown` handlers.

---

## 9. Shared UI Components

### 9.1 [MODERATE] `MagneticButton` wraps interactive elements in a non-semantic `div`
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/shared/ui/magnetic-button.tsx` lines 49-59
- **Description:** `MagneticButton` renders as `motion.div` wrapping children (which are often buttons). The div has `onMouseMove` and `onClick` handlers but no semantic role. The `onClick` prop means the div is interactive but not keyboard-accessible.
- **Fix:** Remove `onClick` from `MagneticButton` (let the child handle it) or change to a semantic element. The magnetic effect should be purely visual without intercepting interaction.

### 9.2 [MINOR] `InceptionButton` uses `div` with `onClick` as interactive wrapper
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/components/ui/InceptionButton.tsx` lines 118-127
- **Description:** The outer wrapper `<div>` has an `onClick` handler, making it interactive without being a semantic button element.
- **Fix:** The click handler should only exist on the child button, not the wrapping div, or the div should have `role="presentation"`.

### 9.3 [CRITICAL] `Button` component wraps `<button>` in multiple `<div>` layers
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/components/ui/button.tsx` lines 45-70
- **Description:** The `Button` component wraps the native `<button>` in both `InceptionButton` and `MagneticButton`, each adding a `<div>` with `onClick`. This means clicking the outer divs triggers the `onClick` prop but the actual `<button>` may not receive the click event for form submission. The `onClick` is extracted separately from `...props` (line 46) and passed to `InceptionButton`, meaning the `<button>` element itself has no `onClick` handler. This creates confusing interaction semantics.
- **Fix:** Ensure click events properly propagate to the native `<button>`. The magnetic and inception effects should be purely visual wrappers, not interaction interceptors.

### 9.4 [MINOR] `Scanlines` component not marked as decorative
- **WCAG:** 1.1.1 Non-text Content (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/shared/ui/atoms/scanlines.tsx` lines 1-17
- **Description:** The Scanlines overlay contains three `<div>` elements that are purely decorative but lack `aria-hidden="true"` on the parent container.
- **Fix:** Add `aria-hidden="true"` to the outermost `<div>`.

---

## 10. Color Contrast Concerns

### 10.1 [SERIOUS] Neon colors on dark background - calculated contrast issues
- **WCAG:** 1.4.3 Contrast Minimum (Level AA)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/globals.css`

**Dark mode analysis** (most critical since it is the primary cyberpunk theme):

| Foreground Color | Hex | Background | Approx Ratio | Passes AA? |
|-----------------|-----|-----------|-------------|------------|
| `--color-neon-cyan` | `#00ffff` | `--depth-0` (~`#070711`) | ~16.4:1 | Yes |
| `--color-matrix-green` | `#00ff88` | `--depth-0` (~`#070711`) | ~14.7:1 | Yes |
| `--color-neon-pink` | `#ff00ff` | `--depth-0` (~`#070711`) | ~5.5:1 | Yes (normal text) |
| `--muted-foreground` | oklch(0.60 0.05 195) | `--depth-0` (~`#070711`) | ~5.2:1 | Yes (barely) |
| `--color-server-warning` | `#ffff00` | `--depth-0` (~`#070711`) | ~18:1 | Yes |
| `--muted-foreground/60` (used in header) | ~40% opacity muted | `--depth-1` | ~3.1:1 | **FAIL** |
| `text-muted-foreground/40` (footer copyright) | ~40% opacity muted | terminal-bg | ~2.1:1 | **FAIL** |
| `text-muted-foreground/50` (footer status) | ~50% opacity muted | terminal-bg | ~2.6:1 | **FAIL** |
| `text-muted-foreground/30` (placeholder text) | ~30% opacity | input bg | ~1.7:1 | **FAIL** (placeholders exempt under WCAG, but very low) |
| `border-grid-line/30` (borders at 30% opacity) | -- | -- | -- | Borders need 3:1 for non-text elements |

**Key failing patterns:**
- Opacity-reduced muted text (e.g., `text-muted-foreground/60`, `/40`, `/50`) throughout header, footer, and data grids
- FPS/ping label `text-muted-foreground/60` in terminal header (line 85)
- Footer copyright text at `/40` opacity

**Light mode analysis:**
The light mode uses desaturated oklch values. The neon colors map to darker, more saturated versions which should maintain better contrast on the lighter backgrounds. However, `--muted-foreground` at oklch(0.30 0.02 250) on `--depth-0` at oklch(0.65 0.015 250) yields approximately 2.5:1, which **FAILS**.

- **Fix:** Audit all text instances using opacity modifiers below `/70` on muted-foreground. Replace with dedicated low-emphasis color tokens that meet 4.5:1 minimum contrast.

### 10.2 [SERIOUS] `text-neon-cyan/80` on dark card backgrounds
- **WCAG:** 1.4.3 Contrast Minimum (Level AA)
- **Files:** Multiple files use `text-neon-cyan/80` (e.g., IP addresses in servers grid, time display in header)
- **Description:** 80% opacity cyan on near-black is likely fine (~13:1), but combined with the scanline overlay reducing effective contrast, edge cases may fail.
- **Fix:** Verify composite contrast after scanline overlay application.

---

## 11. Landing Page

### 11.1 [SERIOUS] Landing page `<header>` inside `<main>` misuses semantic elements
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/app/[locale]/page.tsx` line 11
- **Description:** The page renders `<TerminalHeader />` inside `<main>`, but the header is a `<header>` element. The `<header>` should be outside or adjacent to `<main>`, not inside it.
- **Fix:** Move `<TerminalHeader />` outside of `<main>` in the landing page layout.

### 11.2 [MINOR] Hero section heading hierarchy
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/landing-hero.tsx` line 47
- **Description:** The `<h1>` uses `ScrambleText` which may present garbled text to screen readers during animation. Same concern as CypherText (issue 2.3).
- **Fix:** Ensure `ScrambleText` has `aria-label={text}` on the container.

---

## 12. Footer

### 12.1 [MODERATE] Newsletter email input has no `<label>` or `aria-label`
- **WCAG:** 1.3.1 Info and Relationships (Level A), 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/footer.tsx` lines 186-189
- **Description:** The newsletter `<Input>` has a placeholder `enter_email.exe` but no accessible label. The decorative `root@user:~$` prefix is not associated with the input.
- **Fix:** Add `aria-label="Email address for newsletter"` to the `<Input>`.

### 12.2 [MODERATE] "INIT" submit button lacks descriptive label
- **WCAG:** 4.1.2 Name, Role, Value (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/footer.tsx` lines 190-193
- **Description:** The newsletter submit button says "INIT" with an arrow icon. While visible text is "INIT", it is not descriptive.
- **Fix:** Add `aria-label="Subscribe to newsletter"`.

### 12.3 [MODERATE] Hardcoded English strings
- **WCAG:** 3.1.2 Language of Parts (Level AA)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/footer.tsx` lines 115, 143, 172, and various others
- **Description:** Section headers ("Product", "Support", "Stay Connected"), the "or" separator, and descriptions are hardcoded in English rather than using `useTranslations()`. This violates the project's i18n rules and harms non-English users.
- **Fix:** Move all visible strings to translation files.

### 12.4 [MINOR] Footer social links use `href="#"`
- **WCAG:** 2.4.4 Link Purpose (Level A)
- **File:** `/home/beep/projects/VPNBussiness/frontend/src/widgets/footer.tsx` lines 96-108
- **Description:** Social media links have `href="#"` which causes the page to scroll to top when clicked. The `sr-only` span providing the label is good practice.
- **Fix:** Use real URLs or `href="/"` with `aria-disabled="true"` if not yet implemented.

---

## Summary of Fixes by Priority

### Immediate (Critical)
1. Add skip-navigation link to root layout
2. Add `<caption>` to all data tables
3. Add `role="dialog"` + `aria-modal` + `aria-labelledby` to Modal
4. Fix Button component click propagation (InceptionButton/MagneticButton wrapping)
5. Add `id="main-content"` to dashboard `<main>`

### High Priority (Serious)
6. Add `aria-label` to `<nav>` elements in both sidebars
7. Add `aria-current="page"` to active nav links
8. Add `aria-label`, `aria-expanded`, `aria-haspopup` to notification bell
9. Implement focus trap in Modal
10. Add `aria-label="Close dialog"` to modal close button
11. Add accessible labels/roles to sortable table headers
12. Add `aria-label` to users search input
13. Fix muted-foreground opacity contrast failures
14. Add `dir` attribute for RTL locales
15. Fix terminal header menu button (make it a real `<button>`)
16. Add Escape key handler to notification dropdown
17. Fix landing page semantic structure (`<header>` outside `<main>`)

### Medium Priority (Moderate)
18. Add `aria-label` to CypherText and ScrambleText components
19. Hide decorative glitch text with `aria-hidden`
20. Add `role="progressbar"` + ARIA values to progress bars
21. Add `aria-hidden="true"` to 3D background container
22. Add `aria-hidden="true"` to Scanlines component
23. Add accessible label to ServerStatusDot
24. Fix notification items to be keyboard-accessible
25. Add radio group semantics to registration mode toggle
26. Add `aria-label` to sidebar `<aside>`
27. Add label to newsletter email input
28. Add label to newsletter submit button
29. Localize hardcoded footer strings
30. Verify custom checkbox focus ring visibility

### Low Priority (Minor)
31. Remove redundant `aria-label` from "remember me" checkbox
32. Add text alternative for Wifi icon on mobile
33. Fix footer social links (remove `href="#"`)
34. Review password toggle `tabIndex` decision
35. Review InceptionButton wrapper semantics
36. Review Scanlines composite contrast impact
37. Verify viewport meta allows zoom

---

## Methodology

This audit was conducted through static code analysis. The following could not be verified without a running application:
- Actual rendered color contrast (especially with oklch values and opacity compositing)
- Focus order and tab sequence
- Screen reader announcement of dynamic content
- Touch target sizes
- Reduced motion behavior (though CSS is present in globals.css)
- RTL layout rendering

**Recommended next steps:**
1. Fix all Critical and Serious issues
2. Run automated accessibility testing with axe-core once the app can be built
3. Conduct manual screen reader testing (NVDA + Firefox, VoiceOver + Safari)
4. Verify color contrast using a browser dev tools contrast checker with the running app
5. Test keyboard navigation flow end-to-end
