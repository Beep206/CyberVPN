export type PartnerSurfaceFamily = 'portal' | 'storefront';

type StorefrontSupportProfile = {
  label: string;
  email: string;
  responseWindow: string;
  helpCenterUrl: string;
};

type StorefrontCommunicationProfile = {
  senderName: string;
  senderEmail: string;
};

type StorefrontMerchantProfile = {
  profileKey: string;
  legalEntityName: string;
  billingDescriptor: string;
  refundResponsibilityModel: string;
  chargebackLiabilityModel: string;
};

type StorefrontRouteSet = {
  home: string;
  checkout: string;
  support: string;
  legal: string;
  login: string;
};

export type PortalSurfaceContext = {
  family: 'portal';
  host: string;
  brandName: string;
  brandLabel: string;
  authRealmKey: string;
  routes: Pick<StorefrontRouteSet, 'login'>;
};

export type StorefrontSurfaceContext = {
  family: 'storefront';
  host: string;
  canonicalHost: string;
  brandKey: string;
  brandName: string;
  brandLabel: string;
  brandTagline: string;
  storefrontKey: string;
  authRealmKey: string;
  saleChannel: string;
  defaultCurrency: string;
  defaultPartnerCode: string | null;
  supportProfile: StorefrontSupportProfile;
  communicationProfile: StorefrontCommunicationProfile;
  merchantProfile: StorefrontMerchantProfile;
  routes: StorefrontRouteSet;
};

export type PartnerSurfaceContext = PortalSurfaceContext | StorefrontSurfaceContext;

const PARTNER_PORTAL_PUBLIC_HOST = 'partner.ozoxy.ru';
const PARTNER_PORTAL_LOCAL_HOSTS = [
  'localhost:3002',
  '127.0.0.1:3002',
  'portal.localhost:3002',
] as const;
const DEFAULT_STOREFRONT_HOST = 'storefront.localhost:3002';
const DEFAULT_STOREFRONT_PUBLIC_HOST = 'storefront.ozoxy.ru';
const DEFAULT_STOREFRONT_KEY =
  process.env.NEXT_PUBLIC_PARTNER_DEFAULT_STOREFRONT_KEY?.trim() || 'ozoxy-storefront';
const DEFAULT_STOREFRONT_REALM_KEY =
  process.env.NEXT_PUBLIC_PARTNER_DEFAULT_STOREFRONT_REALM_KEY?.trim() || 'ozoxy-storefront';
const DEFAULT_STOREFRONT_PARTNER_CODE =
  process.env.NEXT_PUBLIC_PARTNER_DEFAULT_PARTNER_CODE?.trim() || null;

const STOREFRONT_ROUTE_SET: StorefrontRouteSet = {
  home: '/',
  checkout: '/checkout',
  support: '/support',
  legal: '/legal-docs',
  login: '/login',
};

const PORTAL_WORKSPACE_ROUTE_PREFIXES = [
  '/dashboard',
  '/analytics',
  '/application',
  '/campaigns',
  '/cases',
  '/codes',
  '/compliance',
  '/conversions',
  '/finance',
  '/integrations',
  '/legal',
  '/notifications',
  '/organization',
  '/programs',
  '/reseller',
  '/settings',
  '/team',
] as const;

const STOREFRONT_PUBLIC_ROUTE_PREFIXES = [
  STOREFRONT_ROUTE_SET.checkout,
  STOREFRONT_ROUTE_SET.support,
  STOREFRONT_ROUTE_SET.legal,
] as const;

function readCsvHosts(value: string | undefined): string[] {
  if (!value) {
    return [];
  }

  return value
    .split(',')
    .map((item) => normalizeRequestHost(item))
    .filter(Boolean);
}

function toTitleCase(value: string): string {
  return value
    .split(/[-_]/)
    .filter(Boolean)
    .map((chunk) => chunk.slice(0, 1).toUpperCase() + chunk.slice(1))
    .join(' ');
}

function stripPort(host: string): string {
  return host.replace(/:\d+$/, '');
}

function deriveBrandKey(host: string): string {
  const hostname = stripPort(host);
  const [subdomain] = hostname.split('.');
  if (!subdomain || subdomain === 'storefront' || subdomain === 'www') {
    return 'ozoxy';
  }

  return subdomain;
}

export function normalizeRequestHost(rawHost: string | null | undefined): string {
  if (!rawHost) {
    return PARTNER_PORTAL_LOCAL_HOSTS[0];
  }

  return rawHost
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/\/.*$/, '');
}

function isLocalizedPathSegment(pathname: string): boolean {
  return /^\/[a-z]{2,3}-[A-Z]{2}(?:\/|$)/.test(pathname);
}

function toInternalPathname(pathname: string): string {
  if (!isLocalizedPathSegment(pathname)) {
    return pathname || '/';
  }

  return pathname.replace(/^\/[a-z]{2,3}-[A-Z]{2}/, '') || '/';
}

function matchesPrefix(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

function buildStorefrontContext(host: string, canonicalHost: string): StorefrontSurfaceContext {
  const brandKey = deriveBrandKey(host);
  const brandName = brandKey === 'ozoxy' ? 'Ozoxy Secure Access' : `${toTitleCase(brandKey)} Secure Access`;

  return {
    family: 'storefront',
    host,
    canonicalHost,
    brandKey,
    brandName,
    brandLabel: `${brandName} Storefront`,
    brandTagline: 'Partner-branded commerce shell bound to storefront, realm, legal, and support context.',
    storefrontKey: DEFAULT_STOREFRONT_KEY,
    authRealmKey: DEFAULT_STOREFRONT_REALM_KEY,
    saleChannel: 'partner_storefront',
    defaultCurrency: 'USD',
    defaultPartnerCode: DEFAULT_STOREFRONT_PARTNER_CODE,
    supportProfile: {
      label: `${brandName} Support`,
      email: 'support@ozoxy.ru',
      responseWindow: '24h',
      helpCenterUrl: 'https://ozoxy.ru/help',
    },
    communicationProfile: {
      senderName: brandName,
      senderEmail: 'support@ozoxy.ru',
    },
    merchantProfile: {
      profileKey: 'ozoxy-merchant',
      legalEntityName: 'Ozoxy Commerce Ltd.',
      billingDescriptor: 'OZOXY*VPN',
      refundResponsibilityModel: 'merchant_of_record',
      chargebackLiabilityModel: 'merchant_of_record',
    },
    routes: STOREFRONT_ROUTE_SET,
  };
}

export function resolvePartnerSurfaceContext(rawHost: string | null | undefined): PartnerSurfaceContext {
  const host = normalizeRequestHost(rawHost);
  const portalHosts = new Set<string>([
    PARTNER_PORTAL_PUBLIC_HOST,
    ...PARTNER_PORTAL_LOCAL_HOSTS,
    ...readCsvHosts(process.env.NEXT_PUBLIC_PARTNER_PORTAL_HOSTS),
  ]);

  if (portalHosts.has(host)) {
    return {
      family: 'portal',
      host,
      brandName: 'CyberVPN Partner Portal',
      brandLabel: 'Ozoxy Partner',
      authRealmKey: 'partner',
      routes: {
        login: '/login',
      },
    };
  }

  const storefrontHosts = new Set<string>([
    DEFAULT_STOREFRONT_HOST,
    DEFAULT_STOREFRONT_PUBLIC_HOST,
    ...readCsvHosts(process.env.NEXT_PUBLIC_PARTNER_STOREFRONT_HOSTS),
  ]);

  if (storefrontHosts.has(host)) {
    return buildStorefrontContext(host, host);
  }

  return buildStorefrontContext(host, DEFAULT_STOREFRONT_PUBLIC_HOST);
}

export function isPortalWorkspacePath(pathname: string): boolean {
  const internalPathname = toInternalPathname(pathname);
  return PORTAL_WORKSPACE_ROUTE_PREFIXES.some((prefix) => matchesPrefix(internalPathname, prefix));
}

export function isStorefrontPublicPath(pathname: string): boolean {
  const internalPathname = toInternalPathname(pathname);
  return STOREFRONT_PUBLIC_ROUTE_PREFIXES.some((prefix) => matchesPrefix(internalPathname, prefix));
}

export function isLocalizedRootPath(pathname: string): boolean {
  return /^\/[a-z]{2,3}-[A-Z]{2}\/?$/.test(pathname);
}
