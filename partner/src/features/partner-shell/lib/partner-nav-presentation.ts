import type { PartnerNavItem } from '@/features/partner-shell/config/section-registry';
import {
  getPartnerNavItemByRoute,
  getPartnerRouteFromNavItem,
  PARTNER_NAV_GROUPS,
  type PartnerNavGroupConfig,
} from '@/features/partner-shell/config/nav-groups';
import {
  getPartnerRoleRouteAccess,
  type PartnerRouteAccessLevel,
} from '@/features/partner-portal-state/lib/portal-access';
import type { PartnerPortalState } from '@/features/partner-portal-state/lib/portal-state';
import {
  getPartnerRouteBlockReason,
  getPartnerRouteVisibility,
  type PartnerRouteBlockReason,
  type PartnerRouteKey,
  type PartnerSectionVisibility,
} from '@/features/partner-portal-state/lib/portal-visibility';

export type PartnerNavPresentationState =
  | 'available'
  | 'task'
  | 'limited'
  | 'readOnly'
  | 'locked'
  | 'hidden';

export type PartnerNavPresentationBadgeKey =
  | 'badgeTask'
  | 'badgeLimited'
  | 'badgeReadOnly'
  | 'badgeLocked';

type PartnerNavPresentationAccessState = PartnerPortalState & {
  currentPermissionKeys?: readonly string[];
};

export type PartnerNavPresentation = {
  route: PartnerRouteKey;
  state: PartnerNavPresentationState;
  badgeKey: PartnerNavPresentationBadgeKey | null;
  access: PartnerRouteAccessLevel;
  visibility: PartnerSectionVisibility;
  blockReason: PartnerRouteBlockReason;
};

export type PartnerNavGroupItem = {
  item: PartnerNavItem;
  presentation: PartnerNavPresentation;
};

export type PartnerNavGroup = Omit<PartnerNavGroupConfig, 'routes'> & {
  items: readonly PartnerNavGroupItem[];
};

export function getPartnerNavPresentation(
  route: PartnerRouteKey,
  state: PartnerNavPresentationAccessState,
): PartnerNavPresentation {
  const blockReason = getPartnerRouteBlockReason(route, state);
  const visibility = getPartnerRouteVisibility(route, state);
  const access = getPartnerRoleRouteAccess(route, state);

  if (access === 'none' || visibility === 'hidden' || blockReason !== null) {
    return {
      route,
      state: 'hidden',
      badgeKey: null,
      access,
      visibility,
      blockReason,
    };
  }

  if (visibility === 'task') {
    return {
      route,
      state: 'task',
      badgeKey: 'badgeTask',
      access,
      visibility,
      blockReason,
    };
  }

  if (visibility === 'limited') {
    return {
      route,
      state: 'limited',
      badgeKey: 'badgeLimited',
      access,
      visibility,
      blockReason,
    };
  }

  if (visibility === 'read' || (route !== 'dashboard' && access === 'read')) {
    return {
      route,
      state: 'readOnly',
      badgeKey: 'badgeReadOnly',
      access,
      visibility,
      blockReason,
    };
  }

  return {
    route,
    state: 'available',
    badgeKey: null,
    access,
    visibility,
    blockReason,
  };
}

export function getPartnerNavItemPresentation(
  item: PartnerNavItem,
  state: PartnerNavPresentationAccessState,
): PartnerNavPresentation {
  return getPartnerNavPresentation(getPartnerRouteFromNavItem(item), state);
}

export function getPartnerNavGroups(
  state: PartnerNavPresentationAccessState,
): readonly PartnerNavGroup[] {
  return PARTNER_NAV_GROUPS.map((group) => {
    const items = group.routes
      .map((route) => {
        const item = getPartnerNavItemByRoute(route);
        const presentation = getPartnerNavPresentation(route, state);

        return presentation.state === 'hidden'
          ? null
          : { item, presentation };
      })
      .filter((item): item is PartnerNavGroupItem => item !== null);

    return {
      id: group.id,
      labelKey: group.labelKey,
      hintKey: group.hintKey,
      items,
    };
  }).filter((group) => group.items.length > 0);
}

export function doesPartnerNavGroupNeedAttention(group: PartnerNavGroup): boolean {
  return group.items.some(({ presentation }) => (
    presentation.state === 'task'
    || presentation.state === 'limited'
  ));
}
