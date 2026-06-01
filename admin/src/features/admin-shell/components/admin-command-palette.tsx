'use client';

import {
  Search,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useTranslations } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import {
  ADMIN_NAV_LABEL_FALLBACKS,
  isAdminRouteActive,
} from '@/features/admin-shell/config/admin-navigation';
import type {
  AdminNavigationMessageKey,
} from '@/features/admin-shell/config/admin-navigation';
import {
  buildAdminCommandPaletteResults,
} from '@/features/admin-shell/config/admin-command-palette';
import type {
  AdminCommandPaletteResult,
} from '@/features/admin-shell/config/admin-command-palette';
import { lockDocumentScroll } from '@/shared/lib/scroll-lock';
import { useAuthStore } from '@/stores/auth-store';

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
    .filter((element) => !element.hasAttribute('disabled'));
}

function isCommandPaletteShortcut(event: KeyboardEvent): boolean {
  return (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k';
}

function useNavigationLabel() {
  const t = useTranslations('Navigation');

  return (key: AdminNavigationMessageKey) => {
    try {
      return t(key);
    } catch {
      return ADMIN_NAV_LABEL_FALLBACKS[key];
    }
  };
}

export function AdminCommandPalette() {
  const router = useRouter();
  const pathname = usePathname();
  const labelFor = useNavigationLabel();
  const user = useAuthStore((state) => state.user);
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const results = buildAdminCommandPaletteResults({
    role: user?.role,
    query,
    labelFor,
  });
  const activeSelectedIndex =
    results.length === 0 ? 0 : Math.min(selectedIndex, results.length - 1);

  const closePalette = () => {
    setIsOpen(false);
    setQuery('');
    setSelectedIndex(0);
  };

  const openPalette = () => {
    setIsOpen(true);
  };

  const activateResult = (result: AdminCommandPaletteResult) => {
    router.push(result.href);
    closePalette();
  };

  useEffect(() => {
    const handleGlobalKeyDown = (event: KeyboardEvent) => {
      if (!isCommandPaletteShortcut(event)) {
        return;
      }

      event.preventDefault();
      setIsOpen(true);
    };

    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => document.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    inputRef.current?.focus();

    return lockDocumentScroll();
  }, [isOpen]);

  const handlePanelKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const eventTarget = event.target as HTMLElement;
    const shouldHandleResultKeys =
      eventTarget === inputRef.current ||
      eventTarget.getAttribute('role') === 'option';

    if (event.key === 'Escape') {
      event.preventDefault();
      closePalette();
      triggerRef.current?.focus();
      return;
    }

    if (event.key === 'Tab' && panelRef.current) {
      const focusableElements = getFocusableElements(panelRef.current);
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (!firstElement || !lastElement) {
        return;
      }

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }

      return;
    }

    if (!shouldHandleResultKeys) {
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setSelectedIndex((currentIndex) =>
        results.length === 0 ? 0 : (currentIndex + 1) % results.length,
      );
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setSelectedIndex((currentIndex) =>
        results.length === 0
          ? 0
          : (currentIndex - 1 + results.length) % results.length,
      );
      return;
    }

    if (event.key === 'Enter' && results[activeSelectedIndex]) {
      event.preventDefault();
      activateResult(results[activeSelectedIndex]);
    }
  };

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={openPalette}
        aria-label={labelFor('commandPalette.open')}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        aria-controls="admin-command-palette"
        className="touch-target inline-flex h-10 w-10 items-center justify-center rounded-md border border-grid-line/30 bg-terminal-surface/60 text-neon-cyan transition-colors hover:border-neon-cyan/45 hover:bg-neon-cyan/10 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
      >
        <Search aria-hidden="true" className="h-4 w-4" />
      </button>

      {isOpen ? (
        <div
          className="fixed inset-0 z-[60] flex items-start justify-center bg-black/65 px-4 pt-[12vh] backdrop-blur-sm sm:px-6"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closePalette();
            }
          }}
        >
          <div
            ref={panelRef}
            id="admin-command-palette"
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-command-palette-title"
            onKeyDown={handlePanelKeyDown}
            className="w-full max-w-2xl overflow-hidden rounded-md border border-neon-cyan/25 bg-terminal-surface/95 shadow-[0_24px_80px_-32px_rgba(0,255,255,0.45)] backdrop-blur-xl"
          >
            <div className="flex items-center gap-3 border-b border-grid-line/30 px-4 py-3">
              <Search
                aria-hidden="true"
                className="h-4 w-4 shrink-0 text-neon-cyan"
              />
              <div className="min-w-0 flex-1">
                <h2
                  id="admin-command-palette-title"
                  className="sr-only"
                >
                  {labelFor('commandPalette.title')}
                </h2>
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setSelectedIndex(0);
                  }}
                  role="combobox"
                  aria-label={labelFor('commandPalette.searchPlaceholder')}
                  aria-expanded="true"
                  aria-controls="admin-command-palette-results"
                  aria-activedescendant={
                    results[activeSelectedIndex]
                      ? `admin-command-result-${results[activeSelectedIndex].id}`
                      : undefined
                  }
                  placeholder={labelFor('commandPalette.searchPlaceholder')}
                  className="h-11 w-full bg-transparent font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-hidden"
                />
              </div>
              <button
                type="button"
                onClick={() => {
                  closePalette();
                  triggerRef.current?.focus();
                }}
                aria-label={labelFor('commandPalette.close')}
                className="touch-target inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-neon-pink/10 hover:text-neon-pink focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-pink"
              >
                <X aria-hidden="true" className="h-4 w-4" />
              </button>
            </div>

            <div
              id="admin-command-palette-results"
              role="listbox"
              aria-label={labelFor('commandPalette.results')}
              className="max-h-[min(28rem,60vh)] overflow-y-auto p-2"
            >
              {results.length > 0 ? (
                <div className="grid gap-1">
                  {results.map((result, index) => {
                    const Icon = result.icon;
                    const isSelected = index === activeSelectedIndex;
                    const isCurrent = isAdminRouteActive(pathname, result.href);
                    const kindLabel = labelFor(
                      result.kind === 'entity'
                        ? 'commandPalette.entityKind'
                        : 'commandPalette.routeKind',
                    );
                    const riskLabel =
                      result.risk === 'write' || result.risk === 'danger'
                        ? labelFor('commandPalette.sensitiveRoute')
                        : null;

                    return (
                      <button
                        key={result.id}
                        id={`admin-command-result-${result.id}`}
                        type="button"
                        role="option"
                        aria-selected={isSelected}
                        aria-current={isCurrent ? 'page' : undefined}
                        onMouseEnter={() => setSelectedIndex(index)}
                        onFocus={() => setSelectedIndex(index)}
                        onClick={() => activateResult(result)}
                        className={cn(
                          'group grid min-h-16 w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan',
                          isSelected
                            ? 'border-neon-cyan/45 bg-neon-cyan/10 text-foreground'
                            : 'border-transparent text-muted-foreground hover:border-grid-line/40 hover:bg-terminal-bg/70 hover:text-foreground',
                        )}
                      >
                        <span
                          className={cn(
                            'flex h-10 w-10 items-center justify-center rounded-md border',
                            isSelected
                              ? 'border-neon-cyan/35 bg-neon-cyan/10 text-neon-cyan'
                              : 'border-grid-line/25 bg-terminal-bg/70 text-muted-foreground group-hover:text-neon-cyan',
                          )}
                        >
                          <Icon aria-hidden="true" className="h-4 w-4" />
                        </span>
                        <span className="min-w-0">
                          <span className="flex min-w-0 flex-wrap items-center gap-2">
                            <span className="truncate font-mono text-sm uppercase tracking-[0.12em]">
                              {result.label}
                            </span>
                            {isCurrent ? (
                              <span className="rounded-sm border border-matrix-green/35 bg-matrix-green/10 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-matrix-green">
                                {labelFor('commandPalette.currentRoute')}
                              </span>
                            ) : null}
                            {riskLabel ? (
                              <span className="rounded-sm border border-amber-300/35 bg-amber-300/10 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-amber-200">
                                {riskLabel}
                              </span>
                            ) : null}
                          </span>
                          <span className="mt-1 block truncate text-xs text-muted-foreground">
                            {result.description}
                          </span>
                        </span>
                        <span className="hidden shrink-0 text-right font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground sm:block">
                          {kindLabel}
                        </span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="rounded-md border border-grid-line/20 bg-terminal-bg/45 px-4 py-10 text-center font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  {labelFor('commandPalette.empty')}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
