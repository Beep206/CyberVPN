import { cacheLife, cacheTag } from 'next/cache';
import {
  DEVICE_DETAIL_LOCALIZATION,
  localizeDeviceEntry,
} from '@/content/seo/market-detail-localization';
import {
  DEVICES_HUB_LOCALIZATION,
  formatSeoUpdatedAt,
  localizeHubContent,
} from '@/content/seo/market-localization';
import type { SeoDeviceEntry, SeoHubCard, SeoHubContent } from '@/content/seo/types';

const DEVICE_CTA_LINKS = [
  {
    label: 'Open download center',
    href: '/download',
    description: 'Get the right client bundle before you start manual setup.',
    seoCta: 'device_download',
    seoZone: 'devices_content',
  },
  {
    label: 'Review help center',
    href: '/help',
    description: 'Use support docs when onboarding users or replacing a device.',
    seoCta: 'device_help',
    seoZone: 'devices_content',
  },
  {
    label: 'Compare protocols',
    href: '/compare',
    description: 'Choose the tunnel model that matches the device constraints.',
    seoCta: 'device_compare',
    seoZone: 'devices_content',
  },
] as const;

const DEVICE_ENTRIES: SeoDeviceEntry[] = [
  {
    slug: 'android-vpn-setup',
    path: '/devices/android-vpn-setup',
    badge: 'Android setup',
    title: 'Android VPN setup with CyberVPN for restrictive Wi-Fi and mobile data',
    description:
      'Set up Android clients with a stable default route, a restrictive-network fallback, and a clean handoff from onboarding to day-two support.',
    readingTime: '6 min read',
    updatedAt: '2026-03-31',
    heroPoints: [
      'Works for both normal mobile links and hostile public Wi-Fi.',
      'Keeps fallback routing explicit instead of buried in hidden toggles.',
      'Maps directly to download, support, and trust surfaces.',
    ],
    sections: [
      {
        title: 'Install the right client first',
        paragraphs: [
          'Android setups go wrong when users are handed three different client options and told to improvise. Start with one recommended client and one fallback.',
          'If the user is likely to roam onto filtered networks, preload both a default route and a restrictive-network route from the start.',
        ],
      },
      {
        title: 'Package setup as two clean presets',
        paragraphs: [
          'The first preset should optimize for speed and battery life on normal links. The second should prioritize reachability when the network becomes aggressive.',
          'Label both profiles clearly so support can diagnose problems without guessing which tunnel is active.',
        ],
        bullets: [
          'Default preset for ordinary LTE and home broadband.',
          'Fallback preset for captive portals, campus networks, and filtered ISPs.',
          'One link back to trust, one link back to help, and one link to status.',
        ],
      },
      {
        title: 'Prepare for day-two support',
        paragraphs: [
          'Android support gets expensive when reinstall is the only playbook. Publish a recovery flow for stale credentials, route degradation, and app-specific issues.',
          'If your team can explain the next step in one sentence, the setup is mature enough to scale.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'Trust center',
        href: '/trust',
        description: 'Give users the operator context behind the setup.',
      },
      {
        label: 'Status page',
        href: '/status',
        description: 'Check whether the problem is already known before changing profiles.',
      },
      {
        label: 'Pricing',
        href: '/pricing',
        description: 'Confirm device slots before rolling out to a household or team.',
      },
    ],
    ctaLinks: [...DEVICE_CTA_LINKS],
    applicationCategory: 'SecurityApplication',
    operatingSystems: ['Android'],
    featureList: [
      'Restrictive-network fallback profile',
      'Mobile-data and Wi-Fi route presets',
      'Support path to help, status, and trust surfaces',
    ],
    downloadPath: '/download',
    offers: [
      {
        name: 'CyberVPN access',
        description: 'Subscription access for Android and multi-device routing.',
        price: '9.99',
        priceCurrency: 'USD',
        url: '/pricing',
      },
    ],
  },
  {
    slug: 'ios-vpn-setup',
    path: '/devices/ios-vpn-setup',
    badge: 'iPhone and iPad setup',
    title: 'iOS VPN setup for stable roaming between home, work, and public hotspots',
    description:
      'Configure a clean iOS VPN path that survives network switching, minimizes support churn, and gives the user an obvious fallback when a route degrades.',
    readingTime: '6 min read',
    updatedAt: '2026-03-31',
    heroPoints: [
      'Prioritizes reliability across Wi-Fi and cellular transitions.',
      'Keeps fallback flows obvious for support and self-serve users.',
      'Pairs setup instructions with trust and status context.',
    ],
    sections: [
      {
        title: 'Keep onboarding short enough to finish on a phone',
        paragraphs: [
          'Mobile onboarding fails when it assumes desktop patience. Present one recommended client, one route, and one fallback instead of a full matrix.',
          'If your instructions require constant app switching, the flow is not ready for broad rollout.',
        ],
      },
      {
        title: 'Plan for route degradation before it happens',
        paragraphs: [
          'iOS users will blame the app long before they blame the network. Give them a status page and a backup route so the next step is obvious.',
          'A good setup guide is also a triage guide.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'Download center',
        href: '/download',
        description: 'Start with the currently recommended client package.',
      },
      {
        label: 'Help center',
        href: '/help',
        description: 'Use the recovery flow if the route stops working.',
      },
      {
        label: 'Audits',
        href: '/audits',
        description: 'Review what evidence matters before deploying widely.',
      },
    ],
    ctaLinks: [...DEVICE_CTA_LINKS],
    applicationCategory: 'SecurityApplication',
    operatingSystems: ['iOS', 'iPadOS'],
    featureList: [
      'Roaming-aware route setup',
      'Status and support escalation paths',
      'Fallback profile planning for filtered networks',
    ],
    downloadPath: '/download',
    offers: [
      {
        name: 'CyberVPN access',
        description: 'Subscription access for iPhone, iPad, and other device classes.',
        price: '9.99',
        priceCurrency: 'USD',
        url: '/pricing',
      },
    ],
  },
  {
    slug: 'windows-vpn-setup',
    path: '/devices/windows-vpn-setup',
    badge: 'Desktop setup',
    title: 'Windows VPN setup for workstations that need speed, fallback, and support clarity',
    description:
      'Deploy a Windows client path that covers normal work traffic, hostile networks, and quick recovery when a route or profile changes.',
    readingTime: '7 min read',
    updatedAt: '2026-03-31',
    heroPoints: [
      'Clean desktop onboarding for daily work and travel.',
      'Easy handoff between default and fallback routes.',
      'Designed for fewer support escalations after rollout.',
    ],
    sections: [
      {
        title: 'Standardize the client and profile pack',
        paragraphs: [
          'Windows is where profile sprawl becomes expensive. Publish one blessed client and a profile pack with strict names instead of letting users import random configs.',
          'If a user cannot tell which profile is the fallback, your packaging is too loose.',
        ],
      },
      {
        title: 'Treat workstation rollout as an operating surface',
        paragraphs: [
          'Workstations often expose route issues faster because they carry heavier traffic, more apps, and stricter expectations.',
          'Pair the setup with docs, status visibility, and trust context so users do not invent their own troubleshooting path.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'API docs',
        href: '/api',
        description: 'Automate route distribution if you manage multiple seats.',
      },
      {
        label: 'Network map',
        href: '/network',
        description: 'Choose the closest region before finalizing the profile pack.',
      },
      {
        label: 'Trust center',
        href: '/trust',
        description: 'Review the controls behind the client rollout.',
      },
    ],
    ctaLinks: [...DEVICE_CTA_LINKS],
    applicationCategory: 'SecurityApplication',
    operatingSystems: ['Windows'],
    featureList: [
      'Default and fallback workstation profiles',
      'Operational links to docs, status, and trust surfaces',
      'Clean route selection for teams and heavy desktop traffic',
    ],
    downloadPath: '/download',
    offers: [
      {
        name: 'CyberVPN access',
        description: 'Subscription access for Windows and multi-device deployments.',
        price: '9.99',
        priceCurrency: 'USD',
        url: '/pricing',
      },
    ],
  },
] as const;

const DEVICES_HUB_BASE = {
  path: '/devices',
  badge: 'Setup playbooks',
  title: 'Device-specific VPN setup guides for Android, iPhone, iPad, and desktop clients',
  description:
    'Setup pages built to reduce support friction, align the right client to the right device, and move users toward working installs instead of generic troubleshooting loops.',
  bullets: [
    'Device-specific setup guidance with explicit fallback paths.',
    'Linked to download, help, compare, pricing, trust, and status surfaces.',
    'Structured as server-rendered acquisition pages instead of app-only flows.',
  ],
  proofPoints: ['3 setup guides', 'SoftwareApplication schema', 'Support-first linking'],
} as const;

function toHubCard(entry: SeoDeviceEntry, locale?: string): SeoHubCard {
  return {
    slug: entry.slug,
    path: entry.path,
    eyebrow: entry.badge,
    title: entry.title,
    description: entry.description,
    stats: [
      entry.readingTime,
      formatSeoUpdatedAt(entry.updatedAt, locale),
      entry.operatingSystems.join(', '),
    ],
  };
}

export async function getDeviceEntries(locale?: string): Promise<SeoDeviceEntry[]> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-devices');

  return DEVICE_ENTRIES.map((entry) =>
    localizeDeviceEntry(entry, DEVICE_DETAIL_LOCALIZATION[entry.slug] ?? {}, locale),
  );
}

export async function getDeviceEntry(
  slug: string,
  locale?: string,
): Promise<SeoDeviceEntry | undefined> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-devices');

  const entry = DEVICE_ENTRIES.find((deviceEntry) => deviceEntry.slug === slug);

  return entry
    ? localizeDeviceEntry(entry, DEVICE_DETAIL_LOCALIZATION[entry.slug] ?? {}, locale)
    : undefined;
}

export async function getDevicesHubContent(locale?: string): Promise<SeoHubContent> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-devices');

  return localizeHubContent({
    ...DEVICES_HUB_BASE,
    cards: DEVICE_ENTRIES.map((entry) =>
      toHubCard(localizeDeviceEntry(entry, DEVICE_DETAIL_LOCALIZATION[entry.slug] ?? {}, locale), locale),
    ),
    ctaLinks: [...DEVICE_CTA_LINKS],
  }, DEVICES_HUB_LOCALIZATION, locale);
}
