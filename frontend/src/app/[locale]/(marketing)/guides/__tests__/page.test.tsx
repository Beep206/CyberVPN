import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import GuidesPage, { generateMetadata as generateGuidesMetadata } from '../page';
import GuideDetailPage, {
  generateMetadata as generateGuideDetailMetadata,
} from '../[slug]/page';

vi.mock('next/cache', () => ({
  cacheLife: vi.fn(),
  cacheTag: vi.fn(),
}));

vi.mock('next-intl/server', () => ({
  setRequestLocale: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  notFound: vi.fn(() => {
    throw new Error('NEXT_NOT_FOUND');
  }),
}));

vi.mock('next/link', async () => {
  const React = await import('react');

  return {
    default: ({
      href,
      children,
      ...props
    }: React.ComponentProps<'a'> & { href: string }) =>
      React.createElement('a', { href, ...props }, children),
  };
});

vi.mock('@/widgets/public-terminal-header', () => ({
  PublicTerminalHeader: () => <div data-testid="public-header" />,
}));

vi.mock('@/widgets/footer', () => ({
  Footer: () => <div data-testid="footer" />,
}));

describe('guides pages', () => {
  it('renders the guides hub with localized copy for priority markets', async () => {
    render(await GuidesPage({ params: Promise.resolve({ locale: 'ru-RU' }) }));

    expect(
      screen.getByRole('heading', {
        name: /VPN-гайды по настройке, скорости, обходу блокировок и доверию/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Практические сценарии/i)).toBeInTheDocument();
    expect(
      screen.getAllByRole('link', { name: /Открыть страницу/i })[0],
    ).toHaveAttribute('href', '/guides/how-to-bypass-dpi-with-vless-reality');
  });

  it('renders the guide detail page with article content and related links', async () => {
    const { container } = render(
      await GuideDetailPage({
        params: Promise.resolve({
          locale: 'ru-RU',
          slug: 'how-to-bypass-dpi-with-vless-reality',
        }),
      }),
    );

    expect(
      screen.getByRole('heading', {
        name: /Как обходить DPI с VLESS Reality без лишней задержки/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Открыть trust center/i })).toHaveAttribute(
      'href',
      '/trust',
    );
    expect(container.querySelector('script[type="application/ld+json"]')).toBeTruthy();
  });

  it('keeps hub metadata and localized detail metadata indexable for Russia', async () => {
    const hubMetadata = await generateGuidesMetadata({
      params: Promise.resolve({ locale: 'ru-RU' }),
    });
    const detailMetadata = await generateGuideDetailMetadata({
      params: Promise.resolve({
        locale: 'ru-RU',
        slug: 'how-to-bypass-dpi-with-vless-reality',
      }),
    });

    expect(hubMetadata.alternates?.canonical).toBe('https://vpn.ozoxy.ru/ru-RU/guides');
    expect(hubMetadata.robots).toBeUndefined();
    expect(detailMetadata.alternates?.canonical).toBe(
      'https://vpn.ozoxy.ru/ru-RU/guides/how-to-bypass-dpi-with-vless-reality',
    );
    expect(detailMetadata.robots).toBeUndefined();
  });
});
