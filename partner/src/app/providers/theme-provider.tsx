'use client';

import * as React from 'react';

type Theme = 'light' | 'dark' | 'system';
type ResolvedTheme = 'light' | 'dark';
type ThemeAttribute = 'class' | `data-${string}`;

interface ThemeProviderProps {
  attribute?: ThemeAttribute | ThemeAttribute[];
  children: React.ReactNode;
  defaultTheme?: Theme;
  disableTransitionOnChange?: boolean;
  enableColorScheme?: boolean;
  enableSystem?: boolean;
  forcedTheme?: Theme;
  storageKey?: string;
  value?: Partial<Record<ResolvedTheme, string>>;
}

interface ThemeContextValue {
  forcedTheme?: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  systemTheme: ResolvedTheme;
  theme: Theme;
  themes: Theme[];
}

const THEME_STORAGE_KEY = 'theme';
const SYSTEM_THEME_MEDIA_QUERY = '(prefers-color-scheme: dark)';
const DEFAULT_THEME: Theme = 'system';
const DEFAULT_RESOLVED_THEME: ResolvedTheme = 'dark';
const FALLBACK_CONTEXT: ThemeContextValue = {
  forcedTheme: undefined,
  resolvedTheme: DEFAULT_RESOLVED_THEME,
  setTheme: () => {},
  systemTheme: DEFAULT_RESOLVED_THEME,
  theme: DEFAULT_THEME,
  themes: ['light', 'dark', 'system'],
};

const ThemeContext = React.createContext<ThemeContextValue>(FALLBACK_CONTEXT);
const useIsomorphicLayoutEffect =
  typeof window === 'undefined' ? React.useEffect : React.useLayoutEffect;

function isTheme(value: unknown): value is Theme {
  return value === 'light' || value === 'dark' || value === 'system';
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return DEFAULT_RESOLVED_THEME;
  }

  return window.matchMedia(SYSTEM_THEME_MEDIA_QUERY).matches ? 'dark' : 'light';
}

function readStoredTheme(storageKey: string, defaultTheme: Theme): Theme {
  if (typeof window === 'undefined') {
    return defaultTheme;
  }

  try {
    const storedValue = window.localStorage.getItem(storageKey);
    return isTheme(storedValue) ? storedValue : defaultTheme;
  } catch {
    return defaultTheme;
  }
}

function resolveTheme(
  theme: Theme,
  systemTheme: ResolvedTheme,
  enableSystem: boolean,
): ResolvedTheme {
  if (theme === 'system') {
    return enableSystem ? systemTheme : DEFAULT_RESOLVED_THEME;
  }

  return theme;
}

function disableTransitionsTemporarily() {
  if (typeof window === 'undefined') {
    return () => {};
  }

  const style = document.createElement('style');
  style.appendChild(
    document.createTextNode(
      '*,*::before,*::after{transition:none!important;animation:none!important}',
    ),
  );
  document.head.appendChild(style);

  return () => {
    window.getComputedStyle(document.body);
    window.requestAnimationFrame(() => {
      document.head.removeChild(style);
    });
  };
}

function applyThemeAttribute(
  attribute: ThemeAttribute | ThemeAttribute[],
  resolvedTheme: ResolvedTheme,
  value?: Partial<Record<ResolvedTheme, string>>,
) {
  const root = document.documentElement;
  const attributes = Array.isArray(attribute) ? attribute : [attribute];
  const classValues = value ? Object.values(value) : ['light', 'dark'];
  const mappedValue = value?.[resolvedTheme] ?? resolvedTheme;

  attributes.forEach((currentAttribute) => {
    if (currentAttribute === 'class') {
      root.classList.remove(...classValues);
      root.classList.add(mappedValue);
      return;
    }

    root.setAttribute(currentAttribute, mappedValue);
  });
}

export function ThemeProvider({
  attribute = 'class',
  children,
  defaultTheme = DEFAULT_THEME,
  disableTransitionOnChange = false,
  enableColorScheme = true,
  enableSystem = true,
  forcedTheme,
  storageKey = THEME_STORAGE_KEY,
  value,
}: ThemeProviderProps) {
  const [theme, setThemeState] = React.useState<Theme>(() =>
    forcedTheme ?? readStoredTheme(storageKey, defaultTheme),
  );
  const [systemTheme, setSystemTheme] = React.useState<ResolvedTheme>(() => getSystemTheme());

  const setTheme = React.useCallback(
    (nextTheme: Theme) => {
      if (!isTheme(nextTheme)) {
        return;
      }

      setThemeState(nextTheme);

      if (typeof window === 'undefined') {
        return;
      }

      try {
        window.localStorage.setItem(storageKey, nextTheme);
      } catch {}
    },
    [storageKey],
  );

  React.useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return () => {};
    }

    const mediaQuery = window.matchMedia(SYSTEM_THEME_MEDIA_QUERY);
    const handleChange = () => {
      setSystemTheme(mediaQuery.matches ? 'dark' : 'light');
    };

    handleChange();
    mediaQuery.addEventListener?.('change', handleChange);

    return () => {
      mediaQuery.removeEventListener?.('change', handleChange);
    };
  }, []);

  React.useEffect(() => {
    if (typeof window === 'undefined') {
      return () => {};
    }

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== storageKey) {
        return;
      }

      setThemeState(isTheme(event.newValue) ? event.newValue : defaultTheme);
    };

    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener('storage', handleStorage);
    };
  }, [defaultTheme, storageKey]);

  const resolvedTheme = resolveTheme(forcedTheme ?? theme, systemTheme, enableSystem);

  useIsomorphicLayoutEffect(() => {
    if (typeof document === 'undefined') {
      return () => {};
    }

    const cleanupTransitions = disableTransitionOnChange
      ? disableTransitionsTemporarily()
      : () => {};

    applyThemeAttribute(attribute, resolvedTheme, value);

    if (enableColorScheme) {
      document.documentElement.style.colorScheme = resolvedTheme;
    }

    cleanupTransitions();
    return () => {};
  }, [attribute, disableTransitionOnChange, enableColorScheme, resolvedTheme, value]);

  const contextValue = React.useMemo<ThemeContextValue>(
    () => ({
      forcedTheme,
      resolvedTheme,
      setTheme,
      systemTheme,
      theme: forcedTheme ?? theme,
      themes: enableSystem ? ['light', 'dark', 'system'] : ['light', 'dark'],
    }),
    [enableSystem, forcedTheme, resolvedTheme, setTheme, systemTheme, theme],
  );

  return <ThemeContext.Provider value={contextValue}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return React.useContext(ThemeContext);
}
