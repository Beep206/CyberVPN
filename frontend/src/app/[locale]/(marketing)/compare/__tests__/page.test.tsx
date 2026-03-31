import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ComparePage, { generateMetadata as generateCompareMetadata } from '../page';
import CompareDetailPage, {
  generateMetadata as generateCompareDetailMetadata,
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

describe('compare pages', () => {
  it('renders the compare hub and links into protocol comparisons for China', async () => {
    render(await ComparePage({ params: Promise.resolve({ locale: 'zh-CN' }) }));

    expect(
      screen.getByRole('heading', {
        name: /帮助用户在速度、隐蔽性与运维复杂度之间做选择的协议与客户端对比/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /打开页面/i })[0]).toHaveAttribute(
      'href',
      '/compare/vless-reality-vs-wireguard',
    );
  });

  it('renders the comparison detail page with related routes', async () => {
    const { container } = render(
      await CompareDetailPage({
        params: Promise.resolve({
          locale: 'zh-CN',
          slug: 'vless-reality-vs-wireguard',
        }),
      }),
    );

    expect(
      screen.getByRole('heading', {
        name: /VLESS Reality vs WireGuard：默认 VPN 流量应该走哪一个/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /下载中心/i })).toHaveAttribute(
      'href',
      '/download',
    );
    expect(container.querySelector('script[type="application/ld+json"]')).toBeTruthy();
  });

  it('generates indexable compare metadata for the hub and localized detail page', async () => {
    const metadata = await generateCompareMetadata({
      params: Promise.resolve({ locale: 'en-EN' }),
    });
    const detailMetadata = await generateCompareDetailMetadata({
      params: Promise.resolve({
        locale: 'zh-CN',
        slug: 'vless-reality-vs-wireguard',
      }),
    });

    expect(metadata.alternates?.canonical).toBe('https://vpn.ozoxy.ru/en-EN/compare');
    expect(metadata.robots).toBeUndefined();
    expect(detailMetadata.alternates?.canonical).toBe(
      'https://vpn.ozoxy.ru/zh-CN/compare/vless-reality-vs-wireguard',
    );
    expect(detailMetadata.robots).toBeUndefined();
  });
});
