export const GOVERNANCE_NAV_ITEMS = [
  { href: '/governance', labelKey: 'nav.overview' },
  { href: '/governance/audit-log', labelKey: 'nav.auditLog' },
  { href: '/governance/webhook-log', labelKey: 'nav.webhookLog' },
  { href: '/governance/admin-invites', labelKey: 'nav.adminInvites' },
  { href: '/governance/policy', labelKey: 'nav.policy' },
] as const;

export type GovernanceNavHref = (typeof GOVERNANCE_NAV_ITEMS)[number]['href'];
