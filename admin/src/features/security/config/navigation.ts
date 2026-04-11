export const SECURITY_NAV_ITEMS = [
  { href: '/security', labelKey: 'nav.overview' },
  { href: '/security/sessions', labelKey: 'nav.sessions' },
  { href: '/security/two-factor', labelKey: 'nav.twoFactor' },
  { href: '/security/anti-phishing', labelKey: 'nav.antiPhishing' },
  { href: '/security/posture', labelKey: 'nav.posture' },
] as const;

export type SecurityNavHref = (typeof SECURITY_NAV_ITEMS)[number]['href'];
