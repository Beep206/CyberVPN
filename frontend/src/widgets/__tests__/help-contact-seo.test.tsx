import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { HelpContact } from '../help-contact';

vi.mock('next-intl/server', () => ({
  getTranslations: vi.fn(async () => (key: string) => key),
}));

vi.mock('@/shared/ui/reveal', () => ({
  Reveal: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/shared/ui/scramble-text', () => ({
  ScrambleText: ({ text }: { text: string }) => <>{text}</>,
}));

describe('HelpContact SEO links', () => {
  async function renderHelpContact() {
    render(await HelpContact());
  }

  it('uses real support links with attribution hooks', async () => {
    await renderHelpContact();

    expect(screen.getByRole('link', { name: 'contact_button_ticket' })).toHaveAttribute(
      'href',
      '/contact',
    );
    expect(screen.getByRole('link', { name: 'contact_button_ticket' })).toHaveAttribute(
      'data-seo-cta',
      'contact',
    );
    expect(screen.getByRole('link', { name: 'contact_button_ticket' })).toHaveAttribute(
      'data-seo-zone',
      'help_contact',
    );
    expect(screen.getByRole('link', { name: 'contact_button_telegram' })).toHaveAttribute(
      'href',
      'https://t.me/cybervpn_bot',
    );
    expect(screen.getByRole('link', { name: 'contact_button_telegram' })).toHaveAttribute(
      'data-seo-cta',
      'telegram',
    );
    expect(screen.getByRole('link', { name: 'contact_button_telegram' })).toHaveAttribute(
      'data-seo-zone',
      'help_contact',
    );
  });
});
