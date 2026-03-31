import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Footer } from '../footer';

vi.mock('next-intl/server', () => ({
  getTranslations: vi.fn(async () => (key: string) => key),
}));

vi.mock('@/widgets/footer-live-strip', () => ({
  FooterLiveStrip: () => <div data-testid="footer-live-strip" />,
}));

vi.mock('@/shared/ui/magnetic-button', () => ({
  MagneticButton: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('Footer SEO links', () => {
  async function renderFooter() {
    render(await Footer());
  }

  it('uses trustworthy entity links instead of placeholders and keeps internal navigation present', async () => {
    await renderFooter();

    expect(screen.getByRole('link', { name: 'Telegram community' })).toHaveAttribute(
      'href',
      'https://t.me/cybervpn',
    );
    expect(screen.getByRole('link', { name: 'Telegram community' })).toHaveAttribute(
      'data-seo-zone',
      'footer_entity',
    );
    expect(screen.getByRole('link', { name: 'Telegram bot' })).toHaveAttribute(
      'href',
      'https://t.me/cybervpn_bot',
    );
    expect(screen.getByRole('link', { name: 'Telegram bot' })).toHaveAttribute(
      'data-seo-cta',
      'telegram',
    );
    expect(screen.getByRole('link', { name: 'Status page' })).toHaveAttribute(
      'href',
      '/status',
    );
    expect(screen.getByRole('link', { name: 'Documentation' })).toHaveAttribute(
      'href',
      '/docs',
    );
    expect(screen.getByRole('link', { name: 'Documentation' })).toHaveAttribute(
      'data-seo-zone',
      'footer_entity',
    );
    expect(screen.getByRole('link', { name: 'Trust center' })).toHaveAttribute(
      'href',
      '/trust',
    );
    expect(screen.getByRole('link', { name: 'Audits' })).toHaveAttribute(
      'href',
      '/audits',
    );

    expect(screen.getByRole('link', { name: 'links.privacy' })).toHaveAttribute(
      'href',
      '/privacy',
    );
    expect(screen.getByRole('link', { name: 'links.terms' })).toHaveAttribute(
      'href',
      '/terms',
    );
    expect(screen.getByRole('link', { name: 'links.security' })).toHaveAttribute(
      'href',
      '/security',
    );

    const hrefs = screen
      .getAllByRole('link')
      .map((link) => link.getAttribute('href'));

    expect(hrefs).not.toContain('#');
  });
});
