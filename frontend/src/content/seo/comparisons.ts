import { cacheLife, cacheTag } from 'next/cache';
import {
  COMPARISON_DETAIL_LOCALIZATION,
  localizeArticleEntry,
} from '@/content/seo/market-detail-localization';
import {
  COMPARE_HUB_LOCALIZATION,
  formatSeoSectionCount,
  formatSeoUpdatedAt,
  localizeHubContent,
} from '@/content/seo/market-localization';
import type { SeoArticleEntry, SeoHubContent, SeoHubCard } from '@/content/seo/types';

const COMPARISON_CTA_LINKS = [
  {
    label: 'Review full docs',
    href: '/docs',
    description: 'Cross-check the protocol details before choosing a default stack.',
    seoCta: 'compare_docs',
    seoZone: 'compare_content',
  },
  {
    label: 'Check pricing',
    href: '/pricing',
    description: 'Match performance goals and device counts to a practical plan.',
    seoCta: 'compare_pricing',
    seoZone: 'compare_content',
  },
  {
    label: 'Open help center',
    href: '/help',
    description: 'See the support surfaces available after rollout.',
    seoCta: 'compare_help',
    seoZone: 'compare_content',
  },
] as const;

const COMPARISON_ENTRIES: SeoArticleEntry[] = [
  {
    slug: 'vless-reality-vs-wireguard',
    path: '/compare/vless-reality-vs-wireguard',
    badge: 'Protocol comparison',
    title: 'VLESS Reality vs WireGuard: which one should carry your default VPN traffic',
    description:
      'Choose between censorship resistance and operational simplicity by mapping each protocol to the real environments your users live in.',
    readingTime: '9 min read',
    updatedAt: '2026-03-31',
    heroPoints: [
      'WireGuard stays lean when the network is cooperative.',
      'Reality wins when DPI and traffic classification are part of the threat model.',
      'The right answer depends on route hostility, device mix, and support overhead.',
    ],
    sections: [
      {
        title: 'Where WireGuard still dominates',
        paragraphs: [
          'WireGuard is excellent when your main problem is speed, predictable roaming, and operational simplicity across many devices.',
          'Its small surface area makes it easy to document and hard for teams to misconfigure once onboarding is stable.',
        ],
      },
      {
        title: 'Where VLESS Reality changes the decision',
        paragraphs: [
          'Reality is designed for environments where ordinary VPN fingerprints are a liability. It makes the route harder to single out without adding theatrical noise.',
          'That extra resilience is valuable only if you are prepared to operate it with monitored targets, fallback paths, and documented rotation procedures.',
        ],
        bullets: [
          'Use Reality when network hostility is a constant, not an edge case.',
          'Use WireGuard when low-friction speed and device coverage matter more.',
          'Keep both when your user base spans normal and restrictive networks.',
        ],
      },
      {
        title: 'Pick the default based on support cost',
        paragraphs: [
          'A technically better tunnel is still the wrong default if it multiplies setup failures for your user base. Measure the support cost, not only the benchmark win.',
          'The cleanest stack is often a two-lane strategy: WireGuard for ordinary traffic and Reality for adversarial routes.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'Download center',
        href: '/download',
        description: 'Map the chosen protocol to available clients and installation paths.',
      },
      {
        label: 'Device guides',
        href: '/devices',
        description: 'Choose the right setup flow for the platform in hand.',
      },
      {
        label: 'Trust center',
        href: '/trust',
        description: 'Understand the operational guarantees around each route.',
      },
    ],
    ctaLinks: [...COMPARISON_CTA_LINKS],
  },
  {
    slug: 'sing-box-vs-clash-meta-for-advanced-routing',
    path: '/compare/sing-box-vs-clash-meta-for-advanced-routing',
    badge: 'Client stack comparison',
    title: 'sing-box vs Clash Meta for advanced routing and fallback control',
    description:
      'Compare the client stacks most power users consider when they need layered routing, clean profile distribution, and credible fallback behavior.',
    readingTime: '7 min read',
    updatedAt: '2026-03-31',
    heroPoints: [
      'sing-box is strong for modern VLESS and Reality-first deployments.',
      'Clash Meta remains useful when users depend on rule-heavy workflows.',
      'The wrong client stack creates invisible support debt.',
    ],
    sections: [
      {
        title: 'Decide whether your users need rule complexity',
        paragraphs: [
          'If your audience mainly needs stable direct tunnels, sing-box keeps the mental model cleaner. If they live in layered rule sets, Clash Meta still has an ecosystem advantage.',
          'The best choice is the one your support and documentation can carry without inventing new failure modes.',
        ],
      },
      {
        title: 'Route portability matters more than feature count',
        paragraphs: [
          'Teams often overvalue exotic knobs and undervalue whether the same profile logic can be moved from phone to laptop without surprises.',
          'Prefer the client stack that lets you publish fewer presets with clearer fallback behavior.',
        ],
        bullets: [
          'Optimize for reproducibility across devices.',
          'Avoid feature paths that only one support engineer understands.',
          'Document the fallback route the same way you document the default route.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'API and docs',
        href: '/api',
        description: 'See how client automation fits the chosen stack.',
      },
      {
        label: 'Status operations',
        href: '/status',
        description: 'Know where users should look when a route degrades.',
      },
      {
        label: 'Security controls',
        href: '/security',
        description: 'Review the controls that matter after deployment.',
      },
    ],
    ctaLinks: [...COMPARISON_CTA_LINKS],
  },
] as const;

const COMPARISON_HUB_BASE = {
  path: '/compare',
  badge: 'Decision support',
  title: 'Protocol and client comparisons for users deciding between speed, stealth, and operational simplicity',
  description:
    'Comparison pages built to answer buyer and operator questions before they land in support, and to channel them toward the right download, plan, or trust surface.',
  bullets: [
    'Turns protocol selection into a concrete operating decision.',
    'Links comparison outcomes to pricing, downloads, trust, and help.',
    'Keeps content server-rendered and index-ready without client-side shells.',
  ],
  proofPoints: ['2 protocol comparisons', 'Server-rendered HTML', 'Clear CTA routing'],
} as const;

function toHubCard(entry: SeoArticleEntry, locale?: string): SeoHubCard {
  return {
    slug: entry.slug,
    path: entry.path,
    eyebrow: entry.badge,
    title: entry.title,
    description: entry.description,
    stats: [
      entry.readingTime,
      formatSeoUpdatedAt(entry.updatedAt, locale),
      formatSeoSectionCount(entry.sections.length, locale),
    ],
  };
}

export async function getComparisonEntries(locale?: string): Promise<SeoArticleEntry[]> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-compare');

  return COMPARISON_ENTRIES.map((entry) =>
    localizeArticleEntry(entry, COMPARISON_DETAIL_LOCALIZATION[entry.slug] ?? {}, locale),
  );
}

export async function getComparisonEntry(
  slug: string,
  locale?: string,
): Promise<SeoArticleEntry | undefined> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-compare');

  const entry = COMPARISON_ENTRIES.find((comparisonEntry) => comparisonEntry.slug === slug);

  return entry
    ? localizeArticleEntry(entry, COMPARISON_DETAIL_LOCALIZATION[entry.slug] ?? {}, locale)
    : undefined;
}

export async function getCompareHubContent(locale?: string): Promise<SeoHubContent> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-compare');

  return localizeHubContent({
    ...COMPARISON_HUB_BASE,
    cards: COMPARISON_ENTRIES.map((entry) =>
      toHubCard(
        localizeArticleEntry(entry, COMPARISON_DETAIL_LOCALIZATION[entry.slug] ?? {}, locale),
        locale,
      ),
    ),
    ctaLinks: [...COMPARISON_CTA_LINKS],
  }, COMPARE_HUB_LOCALIZATION, locale);
}
