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
  {
    slug: 'macos-vpn-setup',
    path: '/devices/macos-vpn-setup',
    badge: 'macOS setup',
    title: 'macOS VPN setup for CyberVPN access without waiting for a native desktop app',
    description:
      'Import the CyberVPN subscription URL, QR code, or config file into a compatible macOS client and keep the support path clear for S1 beta users.',
    readingTime: '6 min read',
    updatedAt: '2026-05-07',
    heroPoints: [
      'Works with compatible clients while the native desktop release stays out of S1.',
      'Keeps the subscription URL and QR code inside trusted user surfaces.',
      'Gives support a clean recovery path for route or credential issues.',
    ],
    sections: [
      {
        title: 'Get the access payload from a trusted surface',
        paragraphs: [
          'Start from the CyberVPN web cabinet or Telegram Mini App after login. Use the issued QR code, subscription URL, or config file only on the device you are setting up.',
          'Do not paste raw subscription URLs, QR payloads, private keys, or full config files into public chats or support messages. If a credential is exposed, support should regenerate it.',
        ],
        bullets: [
          'Use the active subscription or trial state before importing anything.',
          'Prefer the QR or copy action from the customer cabinet over manual retyping.',
          'Keep one default route and one fallback route visible to the user.',
        ],
      },
      {
        title: 'Import into a compatible macOS client',
        paragraphs: [
          'S1 does not require a CyberVPN native desktop app. The beta setup should use a compatible client that can import the generated subscription URL or config file.',
          'After import, name the default and fallback profiles clearly so support can diagnose which route is active without asking for secrets.',
        ],
      },
      {
        title: 'Verify connection and recovery',
        paragraphs: [
          'Once connected, verify the selected region and check the status page before changing profiles. If the route fails, try the fallback profile before reinstalling the client.',
          'Support requests should include the account email or Telegram ID, device type, client name, visible error text, and timestamp. They should not include raw configs or credentials.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'Download center',
        href: '/download',
        description: 'Start from the current S1 compatible-client recommendation.',
      },
      {
        label: 'Customer access',
        href: '/servers',
        description: 'Open the logged-in access screen for QR, subscription URL, and config delivery.',
      },
      {
        label: 'Help center',
        href: '/help',
        description: 'Use the recovery path if import or connection fails.',
      },
    ],
    ctaLinks: [...DEVICE_CTA_LINKS],
    applicationCategory: 'SecurityApplication',
    operatingSystems: ['macOS'],
    featureList: [
      'Compatible-client setup without a native S1 desktop promise',
      'QR, subscription URL, and config-file import path',
      'Fallback route and support escalation guidance',
    ],
    downloadPath: '/download',
    offers: [
      {
        name: 'CyberVPN access',
        description: 'Subscription access for macOS and multi-device deployments.',
        price: '9.99',
        priceCurrency: 'USD',
        url: '/pricing',
      },
    ],
  },
  {
    slug: 'linux-vpn-setup',
    path: '/devices/linux-vpn-setup',
    badge: 'Linux setup',
    title: 'Linux VPN setup for CyberVPN users who need transparent config import and support',
    description:
      'Set up Linux with a compatible client, a controlled subscription/config import path, and support-safe diagnostics for the S1 beta.',
    readingTime: '7 min read',
    updatedAt: '2026-05-07',
    heroPoints: [
      'Keeps Linux setup useful without turning it into an unsupported operator workflow.',
      'Separates user access configs from server-node or Remnawave control-plane material.',
      'Defines what support can ask for without collecting secrets.',
    ],
    sections: [
      {
        title: 'Separate user setup from operator infrastructure',
        paragraphs: [
          'Linux users may be comfortable with advanced networking, but S1 customer setup must stay separate from Remnawave, node, and infrastructure operations.',
          'The only customer-facing payload should be the CyberVPN-issued subscription URL, QR code, or config file for that account and plan.',
        ],
        bullets: [
          'Do not expose node credentials, Remnawave API data, or provider-side config.',
          'Do not ask the user to run infrastructure commands for ordinary setup.',
          'Do keep client logs and error text redacted before support review.',
        ],
      },
      {
        title: 'Import the generated access config',
        paragraphs: [
          'Use a compatible Linux client that can import the generated subscription URL or config file. If the user is on a hostile network, import the fallback route as a separate visible profile.',
          'Profile names should match the customer cabinet labels so support can reproduce the same path from the account state.',
        ],
      },
      {
        title: 'Run support-safe diagnostics',
        paragraphs: [
          'For failed connections, collect client name, distribution, visible error text, selected region, and the approximate time of failure.',
          'Do not collect raw subscription URLs, QR payloads, private keys, auth tokens, full config files, or complete packet captures in first-line support.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'Compare protocols',
        href: '/compare',
        description: 'Choose the route model that matches the Linux client constraints.',
      },
      {
        label: 'Status page',
        href: '/status',
        description: 'Check known route or node issues before rebuilding a profile.',
      },
      {
        label: 'Trust center',
        href: '/trust',
        description: 'Review what CyberVPN does and does not claim for S1.',
      },
    ],
    ctaLinks: [...DEVICE_CTA_LINKS],
    applicationCategory: 'SecurityApplication',
    operatingSystems: ['Linux'],
    featureList: [
      'Compatible-client import for subscription URL or config file',
      'User access separated from infrastructure operations',
      'Support-safe diagnostics without raw secrets',
    ],
    downloadPath: '/download',
    offers: [
      {
        name: 'CyberVPN access',
        description: 'Subscription access for Linux and multi-device deployments.',
        price: '9.99',
        priceCurrency: 'USD',
        url: '/pricing',
      },
    ],
  },
  {
    slug: 'telegram-mini-app-vpn-setup',
    path: '/devices/telegram-mini-app-vpn-setup',
    badge: 'Telegram Mini App setup',
    title: 'Telegram Mini App VPN setup from trial or payment to a working CyberVPN config',
    description:
      'Use the Telegram Bot or Mini App to sign in, start a trial or payment flow, receive VPN access, and import the issued config into a compatible client.',
    readingTime: '6 min read',
    updatedAt: '2026-05-07',
    heroPoints: [
      'Covers the S1 Telegram path without making Telegram the only account identity.',
      'Keeps paid-but-no-access and provisioning retry states visible to support.',
      'Routes users to compatible device setup after the Mini App issues access.',
    ],
    sections: [
      {
        title: 'Start from the official Telegram entry point',
        paragraphs: [
          'Open CyberVPN through the approved Telegram Bot or Mini App entry point. If the account already exists on the web, link Telegram through the explicit verified flow instead of creating a silent duplicate.',
          'After login, the user should see the same S1 product states as the web cabinet: trial, active paid access, grace, expired, payment issue, or provisioning retry.',
        ],
      },
      {
        title: 'Complete trial or payment before importing config',
        paragraphs: [
          'Trial or paid access should move to VPN ready before the user is asked to connect. If provisioning is still retrying, the Mini App should explain that access is being prepared and support can escalate if the delay breaches the S1 policy.',
          'Telegram Stars may be available only in the Telegram paid flow after evidence. Other payment rails must stay hidden until their provider evidence is approved.',
        ],
      },
      {
        title: 'Deliver config safely from Telegram to the target device',
        paragraphs: [
          'The Mini App may show QR, subscription URL, or config download actions, but the user still imports that payload into a compatible device client.',
          'Do not forward raw URLs or config files in Telegram chats. If support needs to investigate, send account identifiers, visible status, provider payment ID if available, and timestamps instead.',
        ],
        bullets: [
          'Use iOS or Android guide steps when connecting from a phone.',
          'Use Windows, macOS, or Linux guide steps when connecting from a desktop.',
          'Escalate paid-but-no-access or orphan payments before they exceed 24 hours.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'Telegram link',
        href: '/telegram-link',
        description: 'Use the explicit account-linking path for web and Telegram identities.',
      },
      {
        label: 'Customer access',
        href: '/servers',
        description: 'Use the web cabinet as the fallback access surface for config delivery.',
      },
      {
        label: 'Support',
        href: '/help',
        description: 'Escalate payment, provisioning, or connection problems without sharing secrets.',
      },
    ],
    ctaLinks: [...DEVICE_CTA_LINKS],
    applicationCategory: 'SecurityApplication',
    operatingSystems: ['Telegram Mini App', 'iOS', 'Android', 'Windows', 'macOS', 'Linux'],
    featureList: [
      'Telegram Bot and Mini App sign-in path',
      'Trial or payment to VPN-ready delivery flow',
      'Safe handoff from Telegram config delivery to compatible device clients',
    ],
    downloadPath: '/download',
    offers: [
      {
        name: 'CyberVPN access',
        description: 'Subscription access for Telegram-led onboarding and multi-device setup.',
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
  title: 'Device-specific VPN setup guides for Android, iOS, Windows, macOS, Linux, and Telegram',
  description:
    'Setup pages built to reduce support friction, align the right compatible client to the right device, and move users from trial or payment to working VPN access.',
  bullets: [
    'Device-specific setup guidance with explicit fallback and support paths.',
    'Linked to download, help, compare, pricing, trust, and status surfaces.',
    'Structured as server-rendered acquisition pages without promising native mobile or desktop releases inside S1.',
  ],
  proofPoints: ['6 S1 setup guides', 'SoftwareApplication schema', 'Support-first linking'],
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
