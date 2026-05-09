import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DevicesPage from '../page';
import DeviceDetailPage, {
  generateMetadata as generateDeviceDetailMetadata,
} from '../[slug]/page';
import { getDeviceEntries } from '@/content/seo/devices';

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
        name: /Гайды по настройке VPN для Android, iOS, Windows, macOS, Linux и Telegram/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /Открыть страницу/i })[0]).toHaveAttribute(
      'href',
      '/devices/android-vpn-setup',
    );
  });

  it('keeps every S1 platform guide available and avoids unsupported native-app promises', async () => {
    const entries = await getDeviceEntries('en-EN');
    const slugs = entries.map((entry) => entry.slug);
    const renderedCopy = entries
      .flatMap((entry) => [
        entry.title,
        entry.description,
        ...entry.heroPoints,
        ...entry.sections.flatMap((section) => [
          section.title,
          ...section.paragraphs,
          ...(section.bullets ?? []),
        ]),
      ])
      .join('\n');

    expect(slugs).toEqual([
      'android-vpn-setup',
      'ios-vpn-setup',
      'windows-vpn-setup',
      'macos-vpn-setup',
      'linux-vpn-setup',
      'telegram-mini-app-vpn-setup',
    ]);
    expect(renderedCopy).toMatch(/subscription URL/i);
    expect(renderedCopy).toMatch(/Do not paste raw subscription URLs/i);
    expect(renderedCopy).toMatch(/S1 does not require a CyberVPN native desktop app/i);
    expect(renderedCopy).not.toMatch(/download CyberVPN from the App Store/i);
    expect(renderedCopy).not.toMatch(/download CyberVPN from Google Play/i);
    expect(renderedCopy).not.toMatch(/automatic renewal/i);
  });

  it('renders the Russian macOS platform guide with safe config-delivery wording', async () => {
    render(
      await DeviceDetailPage({
        params: Promise.resolve({
          locale: 'ru-RU',
          slug: 'macos-vpn-setup',
        }),
      }),
    );

    expect(
      screen.getByRole('heading', {
        name: /Настройка VPN на macOS без ожидания native desktop app/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Не отправляйте raw subscription URL/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Открыть download center/i })).toHaveAttribute(
      'href',
      '/download',
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
      'https://cyber-vpn.net/zh-CN/devices/android-vpn-setup',
    );
    expect(metadata.robots).toBeUndefined();
    expect(blockedMetadata.alternates?.canonical).toBe(
      'https://cyber-vpn.net/en-EN/devices/android-vpn-setup',
    );
    expect(blockedMetadata.robots).toMatchObject({ index: false, follow: false });
  });
});
