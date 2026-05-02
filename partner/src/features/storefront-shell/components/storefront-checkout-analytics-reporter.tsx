'use client';

import { useLocale } from 'next-intl';
import { usePathname } from 'next/navigation';
import { useEffect, useEffectEvent, useRef } from 'react';
import { sendProductAnalyticsEvent } from '@/lib/product-intelligence/client';
import {
  buildCheckoutStartedCapture,
  buildCheckoutStepViewedCapture,
} from '@/lib/product-intelligence/event-builders';

export function StorefrontCheckoutAnalyticsReporter({
  distinctId,
  pricebookKey,
  saleChannel,
  storefrontKey,
}: {
  distinctId: string | null;
  pricebookKey: string | null;
  saleChannel: string;
  storefrontKey: string;
}) {
  const locale = useLocale();
  const pathname = usePathname();
  const lastStartedRef = useRef('');
  const lastViewedRef = useRef('');

  const reportCheckoutEntry = useEffectEvent((nextDistinctId: string | null, nextPathname: string) => {
    if (!nextDistinctId || !nextPathname) {
      return;
    }

    const startedKey = `${nextDistinctId}:${storefrontKey}:${pricebookKey ?? 'none'}`;
    if (lastStartedRef.current !== startedKey) {
      lastStartedRef.current = startedKey;
      sendProductAnalyticsEvent(buildCheckoutStartedCapture({
        distinctId: nextDistinctId,
        locale,
        path: nextPathname,
        pricebookKey,
        saleChannel,
        storefrontKey,
      }));
    }

    const viewedKey = `${nextDistinctId}:${storefrontKey}:${nextPathname}:catalog`;
    if (lastViewedRef.current !== viewedKey) {
      lastViewedRef.current = viewedKey;
      sendProductAnalyticsEvent(buildCheckoutStepViewedCapture({
        distinctId: nextDistinctId,
        locale,
        path: nextPathname,
        step: 'catalog',
        storefrontKey,
      }));
    }
  });

  useEffect(() => {
    reportCheckoutEntry(distinctId, pathname);
  }, [distinctId, locale, pathname, pricebookKey, saleChannel, storefrontKey]);

  return null;
}
