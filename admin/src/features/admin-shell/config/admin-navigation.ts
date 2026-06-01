import type { LucideIcon } from 'lucide-react';
import {
    Activity,
    BadgeDollarSign,
    BellRing,
    Bot,
    ChartColumnIncreasing,
    CircleDollarSign,
    ClipboardCheck,
    CreditCard,
    FileCog,
    Fingerprint,
    Gift,
    Globe2,
    Handshake,
    HardDrive,
    KeyRound,
    Landmark,
    LifeBuoy,
    LockKeyhole,
    MessageSquareText,
    Network,
    PackageOpen,
    PlugZap,
    RadioTower,
    ReceiptText,
    Route,
    ScrollText,
    Server,
    Settings2,
    Shield,
    ShieldAlert,
    ShieldCheck,
    SlidersHorizontal,
    TicketPercent,
    UserCog,
    UserPlus,
    Users,
    WalletCards,
    Waypoints,
    Webhook,
} from 'lucide-react';
import type { AdminPermission, AdminRole } from '@/shared/lib/admin-rbac';
import { hasAdminPermission } from '@/shared/lib/admin-rbac';

export const ADMIN_NAV_LABEL_FALLBACKS = {
    adminConsole: 'ADMIN CONSOLE',
    closeMenu: 'Close menu',
    commerce: 'COMMERCE',
    commerceHint: 'Plans, payments, wallets',
    customers: 'CUSTOMERS',
    customersHint: 'Lifecycle, support, accounts',
    dashboard: 'DASHBOARD',
    dashboardHint: 'Health, queues, incidents',
    governance: 'GOVERNANCE',
    governanceHint: 'Audit, webhooks, staff access',
    growth: 'GROWTH',
    growthHint: 'Promo, invites, referrals',
    infrastructure: 'INFRASTRUCTURE',
    infrastructureHint: 'Servers, nodes, rollouts',
    integrations: 'INTEGRATIONS',
    integrationsHint: 'Telegram, push, realtime',
    mainNavigation: 'Main navigation',
    messaging: 'MESSAGING',
    messagingHint: 'Private dialogs, notes, presence',
    openMenu: 'Open menu',
    secureSession: 'SECURE SESSION',
    secondaryNavigation: 'Section navigation',
    security: 'SECURITY',
    securityHint: 'Sessions, 2FA, trust',
    sidebar: 'Sidebar',
    support: 'SUPPORT',
    supportHint: 'Inbox, replies, internal notes',
    unavailableForRole: 'Unavailable for the current role',
    'commandPalette.close': 'Close command palette',
    'commandPalette.currentRoute': 'Current',
    'commandPalette.empty': 'No matching destinations',
    'commandPalette.entityKind': 'Workspace',
    'commandPalette.open': 'Open command palette',
    'commandPalette.results': 'Command palette results',
    'commandPalette.routeKind': 'Route',
    'commandPalette.searchPlaceholder': 'Search destinations',
    'commandPalette.sensitiveRoute': 'Review flow',
    'commandPalette.title': 'Command palette',
    'group.operations': 'Operations',
    'group.operationsHint': 'Health, queues, incidents',
    'group.customers': 'Customers',
    'group.customersHint': 'Accounts, support, dialogs',
    'group.commerce': 'Finance and plans',
    'group.commerceHint': 'Catalog, payments, wallets',
    'group.growth': 'Growth',
    'group.growthHint': 'Codes, partners, referrals',
    'group.infrastructure': 'VPN infrastructure',
    'group.infrastructureHint': 'Servers, profiles, Xray',
    'group.security': 'Security',
    'group.securityHint': 'Review, sessions, posture',
    'group.governance': 'Control',
    'group.governanceHint': 'Audit, webhooks, policies',
    'group.integrations': 'Integrations',
    'group.integrationsHint': 'Telegram, push, realtime',
    'item.dashboard': 'Operations center',
    'item.dashboardHint': 'Health, queues, incidents',
    'item.customers': 'Customers',
    'item.customersHint': 'Lifecycle and account lookup',
    'item.support': 'Support',
    'item.supportHint': 'Inbox and internal notes',
    'item.messaging': 'Messages',
    'item.messagingHint': 'Dialogs, notes, presence',
    'item.commerceOverview': 'Commerce overview',
    'item.commerceOverviewHint': 'Plans, payments, wallets',
    'item.plans': 'Plans',
    'item.plansHint': 'Tariffs and catalog',
    'item.addons': 'Add-ons',
    'item.addonsHint': 'Paid add-ons',
    'item.pricebooks': 'Pricebooks',
    'item.pricebooksHint': 'Versioned pricing records',
    'item.catalogPreview': 'Catalog preview',
    'item.catalogPreviewHint': 'Customer-facing catalog resolver',
    'item.subscriptionTemplates': 'Subscription templates',
    'item.subscriptionTemplatesHint': 'VPN entitlement presets',
    'item.payments': 'Payments',
    'item.paymentsHint': 'Payment operations',
    'item.wallets': 'Wallets',
    'item.walletsHint': 'Balances and adjustments',
    'item.withdrawals': 'Withdrawals',
    'item.withdrawalsHint': 'Payout approval queue',
    'item.growthOverview': 'Growth overview',
    'item.growthOverviewHint': 'Campaign and risk snapshot',
    'item.reporting': 'Reporting',
    'item.reportingHint': 'Rollups, subscriptions, exports',
    'item.notifications': 'Notifications',
    'item.notificationsHint': 'Delivery feed and manual notices',
    'item.promoCodes': 'Promo codes',
    'item.promoCodesHint': 'Promotions and discounts',
    'item.inviteCodes': 'Invite codes',
    'item.inviteCodesHint': 'Invite inventory',
    'item.giftCodes': 'Gift codes',
    'item.giftCodesHint': 'Gift activation control',
    'item.partners': 'Partners',
    'item.partnersHint': 'Partner operations',
    'item.risk': 'Risk signals',
    'item.riskHint': 'Abuse queue and blocked rewards',
    'item.infrastructureOverview': 'Infrastructure overview',
    'item.infrastructureOverviewHint': 'VPN fleet snapshot',
    'item.servers': 'Servers',
    'item.serversHint': 'Server matrix and capacity',
    'item.hosts': 'Hosts',
    'item.hostsHint': 'Remnawave hosts',
    'item.configProfiles': 'Config profiles',
    'item.configProfilesHint': 'Routing profiles',
    'item.nodePlugins': 'Node plugins',
    'item.nodePluginsHint': 'Plugin readiness',
    'item.xray': 'Xray',
    'item.xrayHint': 'Xray runtime visibility',
    'item.helix': 'Helix',
    'item.helixHint': 'Helix rollout checks',
    'item.inbounds': 'Inbounds',
    'item.inboundsHint': 'Inbound routing',
    'item.squads': 'Squads',
    'item.squadsHint': 'Node squads',
    'item.snippets': 'Snippets',
    'item.snippetsHint': 'Operational snippets',
    'item.securityOverview': 'Security overview',
    'item.securityOverviewHint': 'Security posture summary',
    'item.reviewQueue': 'Review queue',
    'item.reviewQueueHint': 'Security review workload',
    'item.sessions': 'Admin sessions',
    'item.sessionsHint': 'Session visibility',
    'item.twoFactor': '2FA',
    'item.twoFactorHint': 'Two-factor controls',
    'item.antiPhishing': 'Anti-phishing',
    'item.antiPhishingHint': 'Operator trust controls',
    'item.posture': 'Security posture',
    'item.postureHint': 'Risk and hardening',
    'item.governanceOverview': 'Governance overview',
    'item.governanceOverviewHint': 'Audit and policy summary',
    'item.auditLog': 'Audit log',
    'item.auditLogHint': 'Admin activity trail',
    'item.webhookLog': 'Webhook log',
    'item.webhookLogHint': 'Delivery and failure log',
    'item.adminInvites': 'Admin invites',
    'item.adminInvitesHint': 'Staff access invitations',
    'item.policy': 'Policies',
    'item.policyHint': 'Policy visibility',
    'item.integrationsOverview': 'Integrations overview',
    'item.integrationsOverviewHint': 'Integration health',
    'item.telegram': 'Telegram',
    'item.telegramHint': 'Telegram bot operations',
    'item.push': 'Push',
    'item.pushHint': 'Push delivery operations',
    'item.realtime': 'Realtime',
    'item.realtimeHint': 'Realtime topics and tickets',
} as const;

export type AdminNavigationMessageKey =
    keyof typeof ADMIN_NAV_LABEL_FALLBACKS;

export type AdminNavGroupId =
    | 'operations'
    | 'customers'
    | 'commerce'
    | 'growth'
    | 'infrastructure'
    | 'security'
    | 'governance'
    | 'integrations';

export type AdminNavItemRisk = 'read' | 'write' | 'danger';
export type AdminNavAccessState = 'enabled' | 'disabled' | 'hidden';
export type AdminNavPermissionMode = 'all' | 'any';
export type AdminNavHref = `/${string}`;

export interface AdminNavItem {
    id: string;
    href: AdminNavHref;
    aliases?: readonly AdminNavHref[];
    icon: LucideIcon;
    labelKey: AdminNavigationMessageKey;
    hintKey: AdminNavigationMessageKey;
    requiredPermissions?: readonly AdminPermission[];
    permissionMode?: AdminNavPermissionMode;
    unauthorizedState?: Exclude<AdminNavAccessState, 'enabled'>;
    risk?: AdminNavItemRisk;
}

export interface AdminNavGroup {
    id: AdminNavGroupId;
    labelKey: AdminNavigationMessageKey;
    hintKey: AdminNavigationMessageKey;
    items: readonly AdminNavItem[];
}

export interface ResolvedAdminNavItem extends AdminNavItem {
    accessState: Exclude<AdminNavAccessState, 'hidden'>;
}

export interface ResolvedAdminNavGroup extends Omit<AdminNavGroup, 'items'> {
    items: readonly ResolvedAdminNavItem[];
}

export const ADMIN_NAV_GROUPS: readonly AdminNavGroup[] = [
    {
        id: 'operations',
        labelKey: 'group.operations',
        hintKey: 'group.operationsHint',
        items: [
            {
                id: 'dashboard',
                href: '/dashboard',
                icon: Activity,
                labelKey: 'item.dashboard',
                hintKey: 'item.dashboardHint',
                requiredPermissions: ['monitoring_read', 'view_analytics'],
                permissionMode: 'any',
            },
        ],
    },
    {
        id: 'customers',
        labelKey: 'group.customers',
        hintKey: 'group.customersHint',
        items: [
            {
                id: 'customers',
                href: '/customers',
                icon: Users,
                labelKey: 'item.customers',
                hintKey: 'item.customersHint',
                requiredPermissions: ['user_read'],
            },
            {
                id: 'support',
                href: '/support',
                icon: LifeBuoy,
                labelKey: 'item.support',
                hintKey: 'item.supportHint',
                requiredPermissions: ['support_ticket_read'],
            },
            {
                id: 'messaging',
                href: '/messaging',
                icon: MessageSquareText,
                labelKey: 'item.messaging',
                hintKey: 'item.messagingHint',
                requiredPermissions: ['messaging_conversation_read'],
            },
        ],
    },
    {
        id: 'commerce',
        labelKey: 'group.commerce',
        hintKey: 'group.commerceHint',
        items: [
            {
                id: 'commerce-overview',
                href: '/commerce',
                icon: Landmark,
                labelKey: 'item.commerceOverview',
                hintKey: 'item.commerceOverviewHint',
                requiredPermissions: ['payment_read', 'manage_plans'],
                permissionMode: 'any',
            },
            {
                id: 'commerce-plans',
                href: '/commerce/plans',
                icon: BadgeDollarSign,
                labelKey: 'item.plans',
                hintKey: 'item.plansHint',
                requiredPermissions: ['manage_plans'],
                risk: 'write',
            },
            {
                id: 'commerce-addons',
                href: '/commerce/addons',
                icon: PackageOpen,
                labelKey: 'item.addons',
                hintKey: 'item.addonsHint',
                requiredPermissions: ['manage_plans'],
                risk: 'write',
            },
            {
                id: 'commerce-pricebooks',
                href: '/commerce/pricebooks',
                icon: ScrollText,
                labelKey: 'item.pricebooks',
                hintKey: 'item.pricebooksHint',
                requiredPermissions: ['manage_plans'],
                risk: 'write',
            },
            {
                id: 'commerce-catalog-preview',
                href: '/commerce/catalog-preview',
                icon: FileCog,
                labelKey: 'item.catalogPreview',
                hintKey: 'item.catalogPreviewHint',
                requiredPermissions: ['manage_plans'],
            },
            {
                id: 'commerce-subscription-templates',
                href: '/commerce/subscription-templates',
                icon: ReceiptText,
                labelKey: 'item.subscriptionTemplates',
                hintKey: 'item.subscriptionTemplatesHint',
                requiredPermissions: ['manage_plans', 'subscription_create'],
                permissionMode: 'any',
                risk: 'write',
            },
            {
                id: 'commerce-payments',
                href: '/commerce/payments',
                icon: CreditCard,
                labelKey: 'item.payments',
                hintKey: 'item.paymentsHint',
                requiredPermissions: ['payment_read'],
            },
            {
                id: 'commerce-wallets',
                href: '/commerce/wallets',
                icon: WalletCards,
                labelKey: 'item.wallets',
                hintKey: 'item.walletsHint',
                requiredPermissions: ['payment_read'],
            },
            {
                id: 'commerce-withdrawals',
                href: '/commerce/withdrawals',
                icon: CircleDollarSign,
                labelKey: 'item.withdrawals',
                hintKey: 'item.withdrawalsHint',
                requiredPermissions: ['payment_read'],
                risk: 'write',
            },
        ],
    },
    {
        id: 'growth',
        labelKey: 'group.growth',
        hintKey: 'group.growthHint',
        items: [
            {
                id: 'growth-overview',
                href: '/growth',
                icon: ChartColumnIncreasing,
                labelKey: 'item.growthOverview',
                hintKey: 'item.growthOverviewHint',
                requiredPermissions: ['view_analytics', 'manage_invites'],
                permissionMode: 'any',
            },
            {
                id: 'growth-reporting',
                href: '/growth/reporting',
                icon: ChartColumnIncreasing,
                labelKey: 'item.reporting',
                hintKey: 'item.reportingHint',
                requiredPermissions: ['view_analytics'],
            },
            {
                id: 'growth-notifications',
                href: '/growth/notifications',
                icon: BellRing,
                labelKey: 'item.notifications',
                hintKey: 'item.notificationsHint',
                requiredPermissions: ['view_analytics', 'manage_invites'],
                permissionMode: 'any',
                risk: 'write',
            },
            {
                id: 'growth-promo-codes',
                href: '/growth/promo-codes',
                icon: TicketPercent,
                labelKey: 'item.promoCodes',
                hintKey: 'item.promoCodesHint',
                requiredPermissions: ['manage_invites'],
                risk: 'write',
            },
            {
                id: 'growth-invite-codes',
                href: '/growth/invite-codes',
                icon: UserPlus,
                labelKey: 'item.inviteCodes',
                hintKey: 'item.inviteCodesHint',
                requiredPermissions: ['manage_invites'],
                risk: 'write',
            },
            {
                id: 'growth-gift-codes',
                href: '/growth/gift-codes',
                icon: Gift,
                labelKey: 'item.giftCodes',
                hintKey: 'item.giftCodesHint',
                requiredPermissions: ['manage_invites'],
                risk: 'write',
            },
            {
                id: 'growth-partners',
                href: '/growth/partners',
                icon: Handshake,
                labelKey: 'item.partners',
                hintKey: 'item.partnersHint',
                requiredPermissions: ['view_analytics', 'manage_invites'],
                permissionMode: 'any',
            },
            {
                id: 'growth-risk',
                href: '/growth/risk',
                aliases: ['/growth/referrals'],
                icon: ShieldAlert,
                labelKey: 'item.risk',
                hintKey: 'item.riskHint',
                requiredPermissions: ['view_analytics', 'manage_invites'],
                permissionMode: 'any',
                risk: 'write',
            },
        ],
    },
    {
        id: 'infrastructure',
        labelKey: 'group.infrastructure',
        hintKey: 'group.infrastructureHint',
        items: [
            {
                id: 'infrastructure-overview',
                href: '/infrastructure',
                icon: Waypoints,
                labelKey: 'item.infrastructureOverview',
                hintKey: 'item.infrastructureOverviewHint',
                requiredPermissions: ['server_read', 'monitoring_read'],
                permissionMode: 'any',
            },
            {
                id: 'infrastructure-servers',
                href: '/infrastructure/servers',
                icon: Server,
                labelKey: 'item.servers',
                hintKey: 'item.serversHint',
                requiredPermissions: ['server_read'],
            },
            {
                id: 'infrastructure-hosts',
                href: '/infrastructure/hosts',
                icon: HardDrive,
                labelKey: 'item.hosts',
                hintKey: 'item.hostsHint',
                requiredPermissions: ['server_read'],
            },
            {
                id: 'infrastructure-config-profiles',
                href: '/infrastructure/config-profiles',
                icon: SlidersHorizontal,
                labelKey: 'item.configProfiles',
                hintKey: 'item.configProfilesHint',
                requiredPermissions: ['server_read'],
            },
            {
                id: 'infrastructure-node-plugins',
                href: '/infrastructure/node-plugins',
                icon: PlugZap,
                labelKey: 'item.nodePlugins',
                hintKey: 'item.nodePluginsHint',
                requiredPermissions: ['server_read'],
            },
            {
                id: 'infrastructure-xray',
                href: '/infrastructure/xray',
                icon: Network,
                labelKey: 'item.xray',
                hintKey: 'item.xrayHint',
                requiredPermissions: ['server_read'],
            },
            {
                id: 'infrastructure-helix',
                href: '/infrastructure/helix',
                icon: Route,
                labelKey: 'item.helix',
                hintKey: 'item.helixHint',
                requiredPermissions: ['server_read'],
            },
            {
                id: 'infrastructure-inbounds',
                href: '/infrastructure/inbounds',
                icon: RadioTower,
                labelKey: 'item.inbounds',
                hintKey: 'item.inboundsHint',
                requiredPermissions: ['server_read'],
            },
            {
                id: 'infrastructure-squads',
                href: '/infrastructure/squads',
                icon: Globe2,
                labelKey: 'item.squads',
                hintKey: 'item.squadsHint',
                requiredPermissions: ['server_read'],
            },
            {
                id: 'infrastructure-snippets',
                href: '/infrastructure/snippets',
                icon: FileCog,
                labelKey: 'item.snippets',
                hintKey: 'item.snippetsHint',
                requiredPermissions: ['server_read'],
            },
        ],
    },
    {
        id: 'security',
        labelKey: 'group.security',
        hintKey: 'group.securityHint',
        items: [
            {
                id: 'security-overview',
                href: '/security',
                icon: Shield,
                labelKey: 'item.securityOverview',
                hintKey: 'item.securityOverviewHint',
                requiredPermissions: ['audit_read', 'monitoring_read'],
                permissionMode: 'any',
            },
            {
                id: 'security-review-queue',
                href: '/security/review-queue',
                icon: ShieldAlert,
                labelKey: 'item.reviewQueue',
                hintKey: 'item.reviewQueueHint',
                requiredPermissions: ['audit_read'],
            },
            {
                id: 'security-sessions',
                href: '/security/sessions',
                icon: Fingerprint,
                labelKey: 'item.sessions',
                hintKey: 'item.sessionsHint',
                requiredPermissions: ['audit_read', 'manage_admins'],
                permissionMode: 'any',
            },
            {
                id: 'security-two-factor',
                href: '/security/two-factor',
                icon: LockKeyhole,
                labelKey: 'item.twoFactor',
                hintKey: 'item.twoFactorHint',
                requiredPermissions: ['audit_read', 'manage_admins'],
                permissionMode: 'any',
            },
            {
                id: 'security-anti-phishing',
                href: '/security/anti-phishing',
                icon: KeyRound,
                labelKey: 'item.antiPhishing',
                hintKey: 'item.antiPhishingHint',
                requiredPermissions: ['audit_read', 'manage_admins'],
                permissionMode: 'any',
            },
            {
                id: 'security-posture',
                href: '/security/posture',
                icon: ShieldCheck,
                labelKey: 'item.posture',
                hintKey: 'item.postureHint',
                requiredPermissions: ['audit_read', 'monitoring_read'],
                permissionMode: 'any',
            },
        ],
    },
    {
        id: 'governance',
        labelKey: 'group.governance',
        hintKey: 'group.governanceHint',
        items: [
            {
                id: 'governance-overview',
                href: '/governance',
                icon: ScrollText,
                labelKey: 'item.governanceOverview',
                hintKey: 'item.governanceOverviewHint',
                requiredPermissions: ['audit_read', 'webhook_read'],
                permissionMode: 'any',
            },
            {
                id: 'governance-audit-log',
                href: '/governance/audit-log',
                icon: ClipboardCheck,
                labelKey: 'item.auditLog',
                hintKey: 'item.auditLogHint',
                requiredPermissions: ['audit_read'],
            },
            {
                id: 'governance-webhook-log',
                href: '/governance/webhook-log',
                icon: Webhook,
                labelKey: 'item.webhookLog',
                hintKey: 'item.webhookLogHint',
                requiredPermissions: ['webhook_read'],
            },
            {
                id: 'governance-admin-invites',
                href: '/governance/admin-invites',
                icon: UserCog,
                labelKey: 'item.adminInvites',
                hintKey: 'item.adminInvitesHint',
                requiredPermissions: ['manage_admins'],
                unauthorizedState: 'hidden',
                risk: 'write',
            },
            {
                id: 'governance-policy',
                href: '/governance/policy',
                icon: Settings2,
                labelKey: 'item.policy',
                hintKey: 'item.policyHint',
                requiredPermissions: ['audit_read', 'manage_admins'],
                permissionMode: 'any',
            },
        ],
    },
    {
        id: 'integrations',
        labelKey: 'group.integrations',
        hintKey: 'group.integrationsHint',
        items: [
            {
                id: 'integrations-overview',
                href: '/integrations',
                icon: Bot,
                labelKey: 'item.integrationsOverview',
                hintKey: 'item.integrationsOverviewHint',
                requiredPermissions: ['webhook_read', 'monitoring_read'],
                permissionMode: 'any',
            },
            {
                id: 'integrations-telegram',
                href: '/integrations/telegram',
                icon: Bot,
                labelKey: 'item.telegram',
                hintKey: 'item.telegramHint',
                requiredPermissions: ['webhook_read', 'monitoring_read'],
                permissionMode: 'any',
            },
            {
                id: 'integrations-push',
                href: '/integrations/push',
                icon: BellRing,
                labelKey: 'item.push',
                hintKey: 'item.pushHint',
                requiredPermissions: ['webhook_read', 'monitoring_read'],
                permissionMode: 'any',
            },
            {
                id: 'integrations-realtime',
                href: '/integrations/realtime',
                icon: PlugZap,
                labelKey: 'item.realtime',
                hintKey: 'item.realtimeHint',
                requiredPermissions: ['webhook_read', 'monitoring_read'],
                permissionMode: 'any',
            },
        ],
    },
] as const;

export const ADMIN_NAV_ITEMS = flattenAdminNavigationItems();

export function flattenAdminNavigationItems(
    groups: readonly AdminNavGroup[] = ADMIN_NAV_GROUPS,
): AdminNavItem[] {
    const items: AdminNavItem[] = [];

    for (const group of groups) {
        items.push(...group.items);
    }

    return items;
}

export function isAdminRouteActive(
    pathname: string | null | undefined,
    href: AdminNavHref,
): boolean {
    if (!pathname) {
        return false;
    }

    return pathname === href || pathname.startsWith(`${href}/`);
}

export function isAdminNavItemActive(
    pathname: string | null | undefined,
    item: AdminNavItem,
): boolean {
    return [item.href, ...(item.aliases ?? [])].some((href) =>
        isAdminRouteActive(pathname, href),
    );
}

export function isAdminNavGroupActive(
    pathname: string | null | undefined,
    group: AdminNavGroup | ResolvedAdminNavGroup,
): boolean {
    return group.items.some((item) => isAdminNavItemActive(pathname, item));
}

export function getAdminActiveNavItem(
    pathname: string | null | undefined,
    groups: readonly AdminNavGroup[] | readonly ResolvedAdminNavGroup[] =
        ADMIN_NAV_GROUPS,
): AdminNavItem | ResolvedAdminNavItem | null {
    const activeItems = flattenAdminNavigationItems(groups).filter((item) =>
        isAdminNavItemActive(pathname, item),
    );

    activeItems.sort((left, right) => right.href.length - left.href.length);

    return activeItems[0] ?? null;
}

export function getAdminNavItemAccessState(
    item: AdminNavItem,
    role: AdminRole | string | null | undefined,
): AdminNavAccessState {
    const requiredPermissions = item.requiredPermissions ?? [];

    if (requiredPermissions.length === 0) {
        return 'enabled';
    }

    const hasAccess =
        item.permissionMode === 'any'
            ? requiredPermissions.some((permission) =>
                  hasAdminPermission(role, permission),
              )
            : requiredPermissions.every((permission) =>
                  hasAdminPermission(role, permission),
              );

    if (hasAccess) {
        return 'enabled';
    }

    return item.unauthorizedState ?? 'disabled';
}

export function resolveAdminNavigationGroups(
    role: AdminRole | string | null | undefined,
    groups: readonly AdminNavGroup[] = ADMIN_NAV_GROUPS,
): ResolvedAdminNavGroup[] {
    const resolvedGroups: ResolvedAdminNavGroup[] = [];

    for (const group of groups) {
        const resolvedItems: ResolvedAdminNavItem[] = [];

        for (const item of group.items) {
            const accessState = getAdminNavItemAccessState(item, role);

            if (accessState !== 'hidden') {
                resolvedItems.push({
                    ...item,
                    accessState,
                });
            }
        }

        if (resolvedItems.length > 0) {
            resolvedGroups.push({
                ...group,
                items: resolvedItems,
            });
        }
    }

    return resolvedGroups;
}
