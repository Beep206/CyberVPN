import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LanguageSelector } from '../language-selector';

const replaceMock = vi.fn();

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
  usePathname: () => '/dashboard',
}));

vi.mock('@/shared/ui/country-flag', () => ({
  CountryFlag: ({ code }: { code: string }) => <span data-testid={`flag-${code}`}>{code}</span>,
}));

vi.mock('@/shared/ui/magnetic-button', () => ({
  MagneticButton: ({ children }: { children: React.ReactNode }) => children,
}));

describe('LanguageSelector', () => {
  beforeEach(() => {
    replaceMock.mockClear();
  });

  it('renders a touch-safe trigger and safe-area picker content', async () => {
    const user = userEvent.setup();

    render(<LanguageSelector />);

    const trigger = screen.getByRole('button', { name: 'Select language: English' });
    expect(trigger).toHaveClass('touch-target');
    expect(trigger).toHaveAttribute('aria-haspopup', 'dialog');

    await user.click(trigger);

    expect(screen.getByRole('dialog')).toHaveClass('safe-area-dialog');
    expect(screen.getByRole('textbox', { name: 'Search languages' })).toHaveClass(
      'mobile-form-input',
    );
  });

  it('keeps language options reachable without hover-only affordances', async () => {
    const user = userEvent.setup();

    render(<LanguageSelector />);
    await user.click(screen.getByRole('button', { name: 'Select language: English' }));

    const option = screen.getByRole('button', { name: 'Russian (Русский)' });
    expect(option).toHaveClass('touch-target');

    await user.click(option);

    expect(replaceMock).toHaveBeenCalledWith('/dashboard', { locale: 'ru-RU' });
  });
});
