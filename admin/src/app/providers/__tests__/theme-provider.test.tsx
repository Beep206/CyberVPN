import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ThemeProvider, useTheme } from '../theme-provider';

function ThemeConsumer() {
  const { resolvedTheme, theme } = useTheme();

  return (
    <div
      data-testid="theme-consumer"
      data-resolved-theme={resolvedTheme}
      data-theme={theme}
    />
  );
}

describe('ThemeProvider', () => {
  const originalMatchMedia = window.matchMedia;

  beforeEach(() => {
    window.localStorage.clear();
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        addEventListener: vi.fn(),
        matches: query.includes('prefers-color-scheme'),
        media: query,
        removeEventListener: vi.fn(),
      })),
    });
  });

  afterEach(() => {
    document.documentElement.className = '';
    document.documentElement.style.colorScheme = '';
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: originalMatchMedia,
    });
  });

  it('does not render script tags and applies the resolved theme to the document', async () => {
    const { container } = render(
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    expect(container.querySelector('script')).toBeNull();

    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    expect(screen.getByTestId('theme-consumer')).toHaveAttribute('data-theme', 'system');
    expect(screen.getByTestId('theme-consumer')).toHaveAttribute('data-resolved-theme', 'dark');
  });
});
