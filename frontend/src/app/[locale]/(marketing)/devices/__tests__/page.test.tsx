import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DevicesPage from '../page';
import DeviceDetailPage, {
  generateMetadata as generateDeviceDetailMetadata,
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

describe('devices pages', () => {
  it('renders the devices hub and setup entry cards', async () => {
    render(await DevicesPage({ params: Promise.resolve({ locale: 'ru-RU' }) }));

    expect(
      screen.getByRole('heading', {
        name: /Гайды по настройке VPN для Android, iPhone, iPad и desktop-клиентов/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /Открыть страницу/i })[0]).toHaveAttribute(
      'href',
      '/devices/android-vpn-setup',
    );
  });

  it('renders the device detail page with application schema output', async () => {
    const { container } = render(
      await DeviceDetailPage({
        params: Promise.resolve({
          locale: 'zh-CN',
          slug: 'android-vpn-setup',
        }),
      }),
    );

    expect(
      screen.getByRole('heading', {
        name: /面向受限 Wi-Fi 与移动网络的 Android VPN 配置/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /打开下载中心/i })).toHaveAttribute(
      'href',
      '/download',
    );
    expect(container.querySelector('script[type="application/ld+json"]')).toBeTruthy();
  });

  it('keeps device setup pages indexable for priority locales but noindex outside the rollout', async () => {
    const metadata = await generateDeviceDetailMetadata({
      params: Promise.resolve({
        locale: 'zh-CN',
        slug: 'android-vpn-setup',
      }),
    });
    const blockedMetadata = await generateDeviceDetailMetadata({
      params: Promise.resolve({
        locale: 'fa-IR',
        slug: 'android-vpn-setup',
      }),
    });

    expect(metadata.alternates?.canonical).toBe(
      'https://vpn.ozoxy.ru/zh-CN/devices/android-vpn-setup',
    );
    expect(metadata.robots).toBeUndefined();
    expect(blockedMetadata.alternates?.canonical).toBe(
      'https://vpn.ozoxy.ru/en-EN/devices/android-vpn-setup',
    );
    expect(blockedMetadata.robots).toMatchObject({ index: false, follow: false });
  });
});
