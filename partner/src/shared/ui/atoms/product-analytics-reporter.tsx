'use client';

import { useLocale } from 'next-intl';
import { usePathname } from 'next/navigation';
import { useEffect, useEffectEvent, useRef } from 'react';
import { useProductIntelligenceBootstrap } from '@/app/providers/product-intelligence-provider';
import { sendProductAnalyticsEvent } from '@/lib/product-intelligence/client';
import { useAuthStore } from '@/stores/auth-store';

export function ProductAnalyticsReporter() {
  const locale = useLocale();
  const pathname = usePathname();
  const userId = useAuthStore((state) => state.user?.id ?? null);
  const bootstrap = useProductIntelligenceBootstrap();
  const lastDashboardViewRef = useRef<string>('');
  const lastFlagEvaluationRef = useRef<string>('');

  const reportDashboardView = useEffectEvent((nextPathname: string, nextUserId: string | null) => {
    if (!nextUserId || !nextPathname) {
      return;
    }

    const dashboardViewKey = `${nextUserId}:${nextPathname}`;
    if (lastDashboardViewRef.current === dashboardViewKey) {
      return;
    }

    lastDashboardViewRef.current = dashboardViewKey;

    sendProductAnalyticsEvent({
      distinctId: nextUserId,
      event: 'partner_dashboard_viewed',
      properties: {
        locale,
        path: nextPathname,
        route_group: 'dashboard',
        surface: 'partner_portal',
      },
    });
  });

  const reportEvaluatedFlags = useEffectEvent((nextPathname: string, nextUserId: string | null) => {
    if (!nextUserId || !nextPathname || bootstrap.evaluationSource !== 'server_evaluated') {
      return;
    }

    const evaluationKey = `${nextUserId}:${nextPathname}:${bootstrap.evaluatedAt}`;
    if (lastFlagEvaluationRef.current === evaluationKey) {
      return;
    }

    lastFlagEvaluationRef.current = evaluationKey;

    Object.entries(bootstrap.flags).forEach(([flagKey, enabled]) => {
      sendProductAnalyticsEvent({
        distinctId: nextUserId,
        event: 'feature_flag_evaluated',
        properties: {
          evaluation_source: bootstrap.evaluationSource,
          flag_key: flagKey,
          flag_value: enabled ? 'on' : 'off',
          locale,
          path: nextPathname,
          route_group: 'dashboard',
        },
      });
    });
  });

  useEffect(() => {
    reportDashboardView(pathname, userId);
    reportEvaluatedFlags(pathname, userId);
  }, [pathname, userId]);

  return null;
}
