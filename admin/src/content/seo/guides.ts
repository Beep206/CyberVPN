import { cacheLife, cacheTag } from 'next/cache';
import {
  GUIDE_DETAIL_LOCALIZATION,
  localizeArticleEntry,
} from '@/content/seo/market-detail-localization';
import {
  formatSeoSectionCount,
  formatSeoUpdatedAt,
  GUIDES_HUB_LOCALIZATION,
  localizeHubContent,
} from '@/content/seo/market-localization';
import type { SeoArticleEntry, SeoHubContent, SeoHubCard } from '@/content/seo/types';

const GUIDE_CTA_LINKS = [
  {
    label: 'Compare plans',
    href: '/pricing',
    description: 'Choose a plan with enough throughput and device slots.',
    seoCta: 'guide_pricing',
    seoZone: 'guides_content',
  },
  {
    label: 'Download clients',
    href: '/download',
    description: 'Get clients for Android, iOS, desktop, and sing-box based stacks.',
    seoCta: 'guide_download',
    seoZone: 'guides_content',
  },
  {
    label: 'Open trust center',
    href: '/trust',
    description: 'Review logging stance, infrastructure controls, and abuse handling.',
    seoCta: 'guide_trust',
    seoZone: 'guides_content',
  },
] as const;

const GUIDE_ENTRIES: SeoArticleEntry[] = [
  {
    slug: 'how-to-bypass-dpi-with-vless-reality',
    path: '/guides/how-to-bypass-dpi-with-vless-reality',
    badge: 'Censorship resistance',
    title: 'How to bypass DPI with VLESS Reality without wrecking latency',
    description:
      'Deploy a Reality-backed profile that survives hostile ISPs, keeps handshake entropy low, and stays practical for everyday browsing and streaming.',
    readingTime: '8 min read',
    updatedAt: '2026-03-31',
    heroPoints: [
      'Looks like ordinary TLS traffic to restrictive middleboxes.',
      'Keeps packet overhead low enough for mobile and roaming links.',
      'Avoids brittle obfuscation chains that collapse after one policy update.',
    ],
    sections: [
      {
        title: 'Start with a clean transport target',
        paragraphs: [
          'Pick a Reality target that already has stable certificate rotation and broad public trust. The goal is camouflage, not novelty.',
          'Use one entry point per region so you can measure which path is being throttled before you rotate anything.',
        ],
        bullets: [
          'Keep SNI, fingerprint, and flow settings consistent across the client fleet.',
          'Separate high-risk censorship routes from your normal performance routes.',
          'Document a fallback profile before pushing changes to shared device groups.',
        ],
      },
      {
        title: 'Tune the profile for restrictive consumer networks',
        paragraphs: [
          'Reality works best when the rest of the profile is boring. Avoid layering extra gimmicks unless you have packet captures proving they help.',
          'If a region starts degrading, test hop-by-hop changes so you can isolate whether the block is DNS, TLS fingerprinting, or traffic shaping.',
        ],
        bullets: [
          'Prefer direct resolver paths that match the chosen region.',
          'Keep MTU conservative on mobile carriers that aggressively fragment traffic.',
          'Record connection success rate after each rollout instead of trusting anecdotes.',
        ],
      },
      {
        title: 'Operate the route like an incident response surface',
        paragraphs: [
          'Censorship evasion is an operations problem. Treat each blocked route as a repeatable incident with a rollback plan, not as a one-off tweak.',
          'Feed support data, user device mix, and packet-loss observations into one operating loop so you can retire weak routes fast.',
        ],
        bullets: [
          'Monitor handshake failure spikes per ASN.',
          'Keep a clean backup path in the download bundle.',
          'Publish status updates fast when a route is being rotated.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'Protocol docs',
        href: '/docs',
        description: 'Reference the baseline transport model before changing client presets.',
      },
      {
        label: 'Security posture',
        href: '/security',
        description: 'Review the hardening assumptions behind the route.',
      },
      {
        label: 'Independent audits',
        href: '/audits',
        description: 'See what evidence should exist before you trust a new route.',
      },
    ],
    ctaLinks: [...GUIDE_CTA_LINKS],
  },
  {
    slug: 'vpn-speed-optimization-for-streaming-and-gaming',
    path: '/guides/vpn-speed-optimization-for-streaming-and-gaming',
    badge: 'Performance operations',
    title: 'VPN speed optimization for streaming and gaming sessions',
    description:
      'Trim avoidable latency by aligning protocol choice, endpoint geography, and device-level routing with the traffic you actually care about.',
    readingTime: '7 min read',
    updatedAt: '2026-03-31',
    heroPoints: [
      'Reduce jitter before chasing raw bandwidth charts.',
      'Separate gaming and bulk-download routes instead of forcing one preset everywhere.',
      'Use region-aware server choices that track your real destination, not your home city.',
    ],
    sections: [
      {
        title: 'Measure the right bottleneck first',
        paragraphs: [
          'A fast VPN for streaming is not always the fastest VPN for competitive games. Streaming tolerates buffering; games punish jitter and queue delay.',
          'Use baseline latency, packet-loss, and route distance to pick the right profile before changing any client feature.',
        ],
      },
      {
        title: 'Map protocol choice to workload',
        paragraphs: [
          'WireGuard remains excellent for low-friction speed, while Reality-backed profiles are stronger when evasion matters more than raw simplicity.',
          'Keep one stable preset for consoles and another for devices that roam between hostile Wi-Fi and mobile data.',
        ],
        bullets: [
          'Use split routing for patch downloads and launcher traffic when possible.',
          'Pin the game route to the closest stable egress with low evening congestion.',
          'Do not run every household device through the same high-priority tunnel.',
        ],
      },
      {
        title: 'Turn support signals into preset updates',
        paragraphs: [
          'If support keeps seeing complaints from the same carrier or region, that is routing data. Convert it into profile defaults and download recommendations.',
          'A good speed guide is operational knowledge encoded into client choices, not a random list of cache-clearing steps.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'Network map',
        href: '/network',
        description: 'Choose the right region before changing anything in the client.',
      },
      {
        label: 'Status page',
        href: '/status',
        description: 'Check if a route issue is local or already known.',
      },
      {
        label: 'Device setups',
        href: '/devices',
        description: 'Match the route choice to the client platform.',
      },
    ],
    ctaLinks: [...GUIDE_CTA_LINKS],
  },
  {
    slug: 'zero-log-vpn-rollout-checklist-for-teams',
    path: '/guides/zero-log-vpn-rollout-checklist-for-teams',
    badge: 'Trust operations',
    title: 'Zero-log VPN rollout checklist for distributed teams',
    description:
      'Ship a VPN stack to a team without creating shadow IT, unclear logging assumptions, or weak device onboarding paths.',
    readingTime: '6 min read',
    updatedAt: '2026-03-31',
    heroPoints: [
      'Translate privacy claims into onboarding controls.',
      'Make device setup predictable before rollout day.',
      'Treat audit evidence and support playbooks as launch requirements.',
    ],
    sections: [
      {
        title: 'Align policy, onboarding, and incident response',
        paragraphs: [
          'A zero-log claim means little if your support or billing workflows still leak unnecessary metadata. Team rollouts fail when operational surfaces disagree.',
          'Write down who can rotate keys, who can see device history, and how lost-device events are handled before the first user signs in.',
        ],
      },
      {
        title: 'Package the rollout by role, not by raw protocol names',
        paragraphs: [
          'Engineers, executives, and field operators do not need the same profile pack. Give each group the minimum number of clean presets that fit their risk.',
          'The fewer decisions each team makes during setup, the fewer support tickets you absorb after launch.',
        ],
        bullets: [
          'Prepare one default route, one restricted-network fallback, and one emergency status link.',
          'Pair every client bundle with a trust summary and a support escalation path.',
          'Review renewal, downgrade, and device-slot policies before the pilot starts.',
        ],
      },
    ],
    relatedLinks: [
      {
        label: 'Trust center',
        href: '/trust',
        description: 'Use this as the operator-facing summary of guarantees and limits.',
      },
      {
        label: 'Help center',
        href: '/help',
        description: 'Support knowledge base for end-user setup and recovery.',
      },
      {
        label: 'Pricing',
        href: '/pricing',
        description: 'Confirm seat and device economics before scaling the rollout.',
      },
    ],
    ctaLinks: [...GUIDE_CTA_LINKS],
  },
] as const;

const GUIDES_HUB_BASE = {
  path: '/guides',
  badge: 'Operational playbooks',
  title: 'VPN guides that answer setup, speed, censorship, and trust questions with usable detail',
  description:
    'Server-rendered knowledge assets for users comparing VPN architectures, fixing hostile-network issues, and evaluating whether CyberVPN can be trusted in production.',
  bullets: [
    'Written to answer real search intent instead of vanity keyword lists.',
    'Focused on setup, performance, censorship resistance, and trust operations.',
    'Internally linked to pricing, devices, docs, trust, and audit evidence.',
  ],
  proofPoints: ['3 launch-ready guides', 'SSR HTML', 'Actionable internal CTAs'],
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

export async function getGuideEntries(locale?: string): Promise<SeoArticleEntry[]> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-guides');

  return GUIDE_ENTRIES.map((entry) =>
    localizeArticleEntry(entry, GUIDE_DETAIL_LOCALIZATION[entry.slug] ?? {}, locale),
  );
}

export async function getGuideEntry(
  slug: string,
  locale?: string,
): Promise<SeoArticleEntry | undefined> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-guides');

  const entry = GUIDE_ENTRIES.find((guideEntry) => guideEntry.slug === slug);

  return entry
    ? localizeArticleEntry(entry, GUIDE_DETAIL_LOCALIZATION[entry.slug] ?? {}, locale)
    : undefined;
}

export async function getGuidesHubContent(locale?: string): Promise<SeoHubContent> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-guides');

  return localizeHubContent({
    ...GUIDES_HUB_BASE,
    cards: GUIDE_ENTRIES.map((entry) =>
      toHubCard(localizeArticleEntry(entry, GUIDE_DETAIL_LOCALIZATION[entry.slug] ?? {}, locale), locale),
    ),
    ctaLinks: [...GUIDE_CTA_LINKS],
  }, GUIDES_HUB_LOCALIZATION, locale);
}
