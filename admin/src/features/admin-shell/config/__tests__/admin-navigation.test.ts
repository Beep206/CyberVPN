import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
    ADMIN_NAV_GROUPS,
    ADMIN_NAV_ITEMS,
    ADMIN_NAV_LABEL_FALLBACKS,
    flattenAdminNavigationItems,
    getAdminActiveNavItem,
    isAdminRouteActive,
    resolveAdminNavigationGroups,
} from '../admin-navigation';
import type { AdminNavGroup } from '../admin-navigation';

function getStaticDashboardRoutes(): string[] {
    const dashboardRoot = path.join(
        process.cwd(),
        'src/app/[locale]/(dashboard)',
    );
    const routes: string[] = [];

    function visit(directory: string, routeSegments: string[]) {
        const entries = fs.readdirSync(directory, { withFileTypes: true });

        for (const entry of entries) {
            if (entry.name === 'page.tsx') {
                routes.push(`/${routeSegments.join('/')}`);
                continue;
            }

            if (!entry.isDirectory() || entry.name.startsWith('[')) {
                continue;
            }

            visit(path.join(directory, entry.name), [
                ...routeSegments,
                entry.name,
            ]);
        }
    }

    visit(dashboardRoot, []);

    return routes.sort();
}

function getResolvedItem(
    role: string,
    itemId: string,
) {
    return resolveAdminNavigationGroups(role)
        .flatMap((group) => group.items)
        .find((item) => item.id === itemId);
}

function getMessageByPath(
    messages: Record<string, unknown>,
    messagePath: string,
): unknown {
    return messagePath.split('.').reduce<unknown>((currentValue, pathPart) => {
        if (
            currentValue &&
            typeof currentValue === 'object' &&
            !Array.isArray(currentValue)
        ) {
            return (currentValue as Record<string, unknown>)[pathPart];
        }

        return undefined;
    }, messages);
}

describe('admin-navigation registry', () => {
    it('covers every static dashboard route with a navigation entry', () => {
        const navRoutes = ADMIN_NAV_ITEMS.flatMap((item) => [
            item.href,
            ...(item.aliases ?? []),
        ]).sort();

        expect(navRoutes).toEqual(getStaticDashboardRoutes());
    });

    it('chooses the most specific active item for nested routes', () => {
        expect(isAdminRouteActive('/commerce/payments/failed', '/commerce/payments')).toBe(true);
        expect(isAdminRouteActive('/commerce-payments', '/commerce')).toBe(false);
        expect(getAdminActiveNavItem('/commerce/payments')?.id).toBe(
            'commerce-payments',
        );
        expect(getAdminActiveNavItem('/commerce/payments/refunds')?.id).toBe(
            'commerce-payments',
        );
        expect(getAdminActiveNavItem('/growth/referrals')?.id).toBe(
            'growth-risk',
        );
    });

    it('keeps growth split consoles and the legacy referrals alias reachable', () => {
        const growthRoutes = ADMIN_NAV_GROUPS
            .find((group) => group.id === 'growth')
            ?.items.flatMap((item) => [item.href, ...(item.aliases ?? [])]);

        expect(growthRoutes).toEqual(
            expect.arrayContaining([
                '/growth',
                '/growth/reporting',
                '/growth/notifications',
                '/growth/risk',
                '/growth/referrals',
            ]),
        );
    });

    it('removes empty groups after hidden permission filtering', () => {
        const hiddenOnlyGroups: AdminNavGroup[] = [
            {
                id: 'governance',
                labelKey: 'group.governance',
                hintKey: 'group.governanceHint',
                items: [
                    {
                        id: 'admin-only',
                        href: '/governance/admin-invites',
                        icon: ADMIN_NAV_GROUPS[0].items[0].icon,
                        labelKey: 'item.adminInvites',
                        hintKey: 'item.adminInvitesHint',
                        requiredPermissions: ['manage_admins'],
                        unauthorizedState: 'hidden',
                    },
                ],
            },
        ];

        expect(resolveAdminNavigationGroups('viewer', hiddenOnlyGroups)).toEqual([]);
    });

    it('exposes enabled, disabled, and hidden states from existing admin-rbac permissions', () => {
        expect(getResolvedItem('finance', 'commerce-payments')?.accessState).toBe(
            'enabled',
        );
        expect(getResolvedItem('finance', 'commerce-plans')?.accessState).toBe(
            'disabled',
        );
        expect(getResolvedItem('finance', 'governance-admin-invites')).toBeUndefined();
        expect(getResolvedItem('support', 'messaging')?.accessState).toBe(
            'enabled',
        );
    });

    it('keeps visible groups populated for each admin role', () => {
        for (const role of ['viewer', 'support', 'operator', 'finance', 'admin']) {
            const groups = resolveAdminNavigationGroups(role);

            expect(groups.length).toBeGreaterThan(0);
            expect(groups.every((group) => group.items.length > 0)).toBe(true);
        }
    });

    it('has RU and EN labels for every registry label key', () => {
        const enMessages = JSON.parse(
            fs.readFileSync(
                path.join(process.cwd(), 'messages/en-EN/navigation.json'),
                'utf8',
            ),
        ) as Record<string, unknown>;
        const ruMessages = JSON.parse(
            fs.readFileSync(
                path.join(process.cwd(), 'messages/ru-RU/navigation.json'),
                'utf8',
            ),
        ) as Record<string, unknown>;
        const registryKeys = new Set<string>([
            ...Object.keys(ADMIN_NAV_LABEL_FALLBACKS),
            ...ADMIN_NAV_GROUPS.flatMap((group) => [group.labelKey, group.hintKey]),
            ...flattenAdminNavigationItems().flatMap((item) => [
                item.labelKey,
                item.hintKey,
            ]),
        ]);

        expect(Object.keys(enMessages).filter((key) => key.includes('.'))).toEqual([]);
        expect(Object.keys(ruMessages).filter((key) => key.includes('.'))).toEqual([]);

        for (const key of registryKeys) {
            expect(
                getMessageByPath(enMessages, key),
                `missing en-EN Navigation.${key}`,
            ).toBeTypeOf('string');
            expect(
                getMessageByPath(ruMessages, key),
                `missing ru-RU Navigation.${key}`,
            ).toBeTypeOf('string');
        }
    });
});
