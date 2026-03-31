import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LandingHero } from '../landing-hero';

vi.mock('next-intl/server', () => ({
  getTranslations: vi.fn(async () => (key: string) => key),
}));

vi.mock('@/widgets/3d-background/global-network-wrapper', () => ({
  GlobalNetworkWrapper: () => <div data-testid="global-network-wrapper" />,
}));

vi.mock('@/shared/ui/reveal', () => ({
  Reveal: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/shared/ui/scramble-text', () => ({
  ScrambleText: ({ text }: { text: string }) => <>{text}</>,
}));

vi.mock('@/shared/ui/status-badge-live', () => ({
  StatusBadgeLive: () => <div data-testid="status-badge-live" />,
}));

vi.mock('@/shared/ui/magnetic-button', () => ({
  MagneticButton: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('LandingHero SEO links', () => {
  async function renderHero() {
    render(await LandingHero());
  }

  it('renders both CTAs as real crawlable links', async () => {
    await renderHero();

    expect(screen.getByRole('link', { name: 'cta_telegram' })).toHaveAttribute(
      'href',
      'https://t.me/cybervpn_bot',
    );
    expect(screen.getByRole('link', { name: 'cta_telegram' })).toHaveAttribute(
      'data-seo-cta',
      'telegram',
    );
    expect(screen.getByRole('link', { name: 'cta_telegram' })).toHaveAttribute(
      'data-seo-zone',
      'landing_hero',
    );
    expect(screen.getByRole('link', { name: 'cta_app' })).toHaveAttribute(
      'href',
      '/download',
    );
    expect(screen.getByRole('link', { name: 'cta_app' })).toHaveAttribute(
      'data-seo-cta',
      'download',
    );
    expect(screen.getByRole('link', { name: 'cta_app' })).toHaveAttribute(
      'data-seo-zone',
      'landing_hero',
    );
  });
});
