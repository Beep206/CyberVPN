import { getRouteGroup } from '@/shared/lib/mobile-device-bucket';
import { getLocalizedPathInfo } from '@/shared/lib/seo-route-policy';

const AI_REFERRERS = {
  chatgpt: ['chatgpt.com', 'chat.openai.com'],
  claude: ['claude.ai'],
  copilot: ['copilot.microsoft.com'],
  gemini: ['gemini.google.com'],
  grok: ['grok.com'],
  meta_ai: ['meta.ai'],
  openai: ['openai.com'],
  perplexity: ['perplexity.ai'],
  phind: ['phind.com'],
  you: ['you.com'],
} as const;

const SEARCH_REFERRERS = {
  baidu: ['baidu.com'],
  bing: ['bing.com'],
  brave: ['search.brave.com'],
  duckduckgo: ['duckduckgo.com'],
  ecosia: ['ecosia.org'],
  google: ['google.'],
  yahoo: ['search.yahoo.com', 'yahoo.com'],
  yandex: ['yandex.'],
} as const;

const SOCIAL_REFERRERS = {
  facebook: ['facebook.com', 'm.facebook.com'],
  instagram: ['instagram.com'],
  linkedin: ['linkedin.com'],
  reddit: ['reddit.com'],
  telegram: ['t.me', 'telegram.me', 'telegram.org'],
  x: ['x.com', 'twitter.com'],
  youtube: ['youtube.com', 'youtu.be'],
} as const;

const CTA_PATHS = {
  contact: '/contact',
  docs: '/docs',
  download: '/download',
  help: '/help',
  login: '/login',
  pricing: '/pricing',
  register: '/register',
} as const;

const ALLOWED_ROUTE_GROUPS = new Set(['auth', 'dashboard', 'marketing', 'miniapp']);
const ALLOWED_SOURCE_TYPES = new Set<AcquisitionSourceType>([
  'ai',
  'direct',
  'referral',
  'search',
  'social',
]);
const ALLOWED_SOURCE_NAMES = new Set<AcquisitionSourceName>([
  ...Object.keys(AI_REFERRERS),
  ...Object.keys(SEARCH_REFERRERS),
  ...Object.keys(SOCIAL_REFERRERS),
  'direct',
  'referral',
] as AcquisitionSourceName[]);
const ALLOWED_CTA_IDS = new Set<AcquisitionCtaId>([
  ...Object.keys(CTA_PATHS),
  'telegram',
] as AcquisitionCtaId[]);

export type AcquisitionEventName = 'page_view' | 'cta_click';
export type AcquisitionSourceType = 'ai' | 'direct' | 'referral' | 'search' | 'social';
export type SeoAcquisitionEventName =
  | 'seo.ai_referral_session'
  | 'seo.download_cta_click'
  | 'seo.help_contact_click'
  | 'seo.landing_cta_click';
export type AcquisitionSourceName =
  | keyof typeof AI_REFERRERS
  | keyof typeof SEARCH_REFERRERS
  | keyof typeof SOCIAL_REFERRERS
  | 'direct'
  | 'referral';
export type AcquisitionCtaId = keyof typeof CTA_PATHS | 'telegram';

export type AcquisitionSource = {
  referrerHost?: string;
  sourceName: AcquisitionSourceName;
  sourceType: AcquisitionSourceType;
};

export type AcquisitionPayload = {
  connectionType: string;
  deviceBucket: string;
  event: AcquisitionEventName;
  locale?: string;
  pageTitle?: string;
  path: string;
  reducedMotion: string;
  routeGroup: string;
  saveData: string;
  sourceName: AcquisitionSourceName;
  sourceType: AcquisitionSourceType;
  utmCampaign?: string;
  utmContent?: string;
  utmMedium?: string;
  utmSource?: string;
  utmTerm?: string;
  viewportBucket: string;
  ctaHref?: string;
  ctaId?: AcquisitionCtaId;
  ctaZone?: string;
  referrerHost?: string;
};

type ReferrerMatcher = Record<string, readonly string[]>;

function matchesKnownReferrer(hostname: string, matchers: ReferrerMatcher): string | undefined {
  const normalizedHost = hostname.toLowerCase();

  return Object.entries(matchers).find(([, hosts]) =>
    hosts.some((host) => {
      if (host.endsWith('.')) {
        return normalizedHost.startsWith(host) || normalizedHost.includes(`.${host}`);
      }

      return normalizedHost === host || normalizedHost.endsWith(`.${host}`);
    }),
  )?.[0];
}

function sanitizeText(value: string | null | undefined, maxLength: number): string | undefined {
  if (!value) {
    return undefined;
  }

  const normalized = value.replace(/\s+/g, ' ').trim().slice(0, maxLength);
  return normalized || undefined;
}

export function classifyAcquisitionSource(referrer: string | null | undefined): AcquisitionSource {
  const referrerValue = sanitizeText(referrer, 2048);

  if (!referrerValue) {
    return {
      sourceName: 'direct',
      sourceType: 'direct',
    };
  }

  try {
    const referrerUrl = new URL(referrerValue);
    const referrerHost = referrerUrl.hostname.toLowerCase();
    const aiSource = matchesKnownReferrer(referrerHost, AI_REFERRERS);

    if (aiSource) {
      return {
        referrerHost,
        sourceName: aiSource as AcquisitionSourceName,
        sourceType: 'ai',
      };
    }

    const searchSource = matchesKnownReferrer(referrerHost, SEARCH_REFERRERS);

    if (searchSource) {
      return {
        referrerHost,
        sourceName: searchSource as AcquisitionSourceName,
        sourceType: 'search',
      };
    }

    const socialSource = matchesKnownReferrer(referrerHost, SOCIAL_REFERRERS);

    if (socialSource) {
      return {
        referrerHost,
        sourceName: socialSource as AcquisitionSourceName,
        sourceType: 'social',
      };
    }

    return {
      referrerHost,
      sourceName: 'referral',
      sourceType: 'referral',
    };
  } catch {
    return {
      sourceName: 'direct',
      sourceType: 'direct',
    };
  }
}

export function getLocaleFromPathname(pathname: string): string | undefined {
  return getLocalizedPathInfo(pathname).locale;
}

export function isAiAcquisitionSource(source: AcquisitionSource): boolean {
  return source.sourceType === 'ai';
}

export function isAcquisitionRoute(pathname: string): boolean {
  const routeGroup = getRouteGroup(pathname);
  return routeGroup === 'marketing' || routeGroup === 'auth';
}

export function classifyCtaHref(href: string, origin: string): AcquisitionCtaId | undefined {
  const normalizedHref = sanitizeText(href, 2048);

  if (!normalizedHref) {
    return undefined;
  }

  try {
    const url = new URL(normalizedHref, origin);
    const pathnameInfo = getLocalizedPathInfo(url.pathname);

    if (
      url.hostname === 't.me' ||
      url.hostname === 'telegram.me' ||
      url.hostname === 'telegram.org' ||
      url.hostname.endsWith('.telegram.org')
    ) {
      return 'telegram';
    }

    return Object.entries(CTA_PATHS).find(([, path]) => pathnameInfo.pathname === path)?.[0] as
      | AcquisitionCtaId
      | undefined;
  } catch {
    return undefined;
  }
}

export function resolveSeoCtaEventName({
  pathname,
  ctaId,
  ctaZone,
}: {
  pathname: string;
  ctaId?: AcquisitionCtaId;
  ctaZone?: string;
}): SeoAcquisitionEventName | undefined {
  const pathnameInfo = getLocalizedPathInfo(pathname);

  if (pathnameInfo.pathname === '/' && ctaZone === 'landing_hero') {
    return 'seo.landing_cta_click';
  }

  if (pathnameInfo.pathname === '/download' || ctaId === 'download') {
    return 'seo.download_cta_click';
  }

  if (
    pathnameInfo.pathname === '/help' &&
    (ctaId === 'contact' || ctaId === 'telegram') &&
    ctaZone === 'help_contact'
  ) {
    return 'seo.help_contact_click';
  }

  return undefined;
}

export function pickUtmParams(searchParams: URLSearchParams): Pick<
  AcquisitionPayload,
  'utmCampaign' | 'utmContent' | 'utmMedium' | 'utmSource' | 'utmTerm'
> {
  return {
    utmCampaign: sanitizeText(searchParams.get('utm_campaign'), 120),
    utmContent: sanitizeText(searchParams.get('utm_content'), 120),
    utmMedium: sanitizeText(searchParams.get('utm_medium'), 120),
    utmSource: sanitizeText(searchParams.get('utm_source'), 120),
    utmTerm: sanitizeText(searchParams.get('utm_term'), 120),
  };
}

export function sanitizeAcquisitionPayload(payload: AcquisitionPayload): AcquisitionPayload {
  const normalizedRouteGroup = sanitizeText(payload.routeGroup, 32);
  const normalizedSourceType = ALLOWED_SOURCE_TYPES.has(payload.sourceType)
    ? payload.sourceType
    : 'referral';
  const normalizedSourceName = ALLOWED_SOURCE_NAMES.has(payload.sourceName)
    ? payload.sourceName
    : 'referral';
  const normalizedCtaId =
    payload.ctaId && ALLOWED_CTA_IDS.has(payload.ctaId) ? payload.ctaId : undefined;

  return {
    connectionType: sanitizeText(payload.connectionType, 32) ?? 'unknown',
    deviceBucket: sanitizeText(payload.deviceBucket, 32) ?? 'unknown',
    event: payload.event,
    locale: sanitizeText(payload.locale, 16),
    pageTitle: sanitizeText(payload.pageTitle, 240),
    path: sanitizeText(payload.path, 256) ?? '/',
    reducedMotion: sanitizeText(payload.reducedMotion, 32) ?? 'unknown',
    routeGroup:
      normalizedRouteGroup && ALLOWED_ROUTE_GROUPS.has(normalizedRouteGroup)
        ? normalizedRouteGroup
        : 'unknown',
    saveData: sanitizeText(payload.saveData, 8) ?? 'off',
    sourceName: normalizedSourceName,
    sourceType: normalizedSourceType,
    utmCampaign: sanitizeText(payload.utmCampaign, 120),
    utmContent: sanitizeText(payload.utmContent, 120),
    utmMedium: sanitizeText(payload.utmMedium, 120),
    utmSource: sanitizeText(payload.utmSource, 120),
    utmTerm: sanitizeText(payload.utmTerm, 120),
    viewportBucket: sanitizeText(payload.viewportBucket, 32) ?? 'unknown',
    ctaHref: sanitizeText(payload.ctaHref, 256),
    ctaId: normalizedCtaId,
    ctaZone: sanitizeText(payload.ctaZone, 64),
    referrerHost: sanitizeText(payload.referrerHost, 255),
  };
}
