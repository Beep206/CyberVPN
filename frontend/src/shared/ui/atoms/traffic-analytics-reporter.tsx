'use client';

import { usePathname } from 'next/navigation';
import { useEffect, useEffectEvent, useRef } from 'react';
import { seoAnalytics } from '@/lib/analytics';
import {
  classifyAcquisitionSource,
  classifyCtaHref,
  getLocaleFromPathname,
  isAiAcquisitionSource,
  isAcquisitionRoute,
  pickUtmParams,
  resolveSeoCtaEventName,
  type AcquisitionPayload,
} from '@/shared/lib/ai-seo-analytics';
import { getMobileTelemetryContext } from '@/shared/lib/mobile-device-bucket';

const ANALYTICS_ENDPOINT = '/api/analytics/traffic';
const PAGE_VIEW_KEY_STORAGE = '__CYBERVPN_LAST_ANALYTICS_PAGE_VIEW__';

declare global {
  interface Window {
    __CYBERVPN_LAST_ANALYTICS_PAGE_VIEW__?: string;
  }
}

function sendAcquisitionEvent(payload: AcquisitionPayload): void {
  const body = JSON.stringify(payload);

  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    navigator.sendBeacon(ANALYTICS_ENDPOINT, new Blob([body], { type: 'application/json' }));
    return;
  }

  void fetch(ANALYTICS_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
    credentials: 'same-origin',
    keepalive: true,
  });
}

export function TrafficAnalyticsReporter() {
  const pathname = usePathname();
  const lastPageViewKeyRef = useRef<string>('');

  const handlePageView = useEffectEvent((nextPathname: string) => {
    if (!isAcquisitionRoute(nextPathname)) {
      return;
    }

    const searchParams = new URLSearchParams(window.location.search);
    const pageViewKey = `${nextPathname}?${searchParams.toString()}`;
    const previouslyTrackedPageView = window[PAGE_VIEW_KEY_STORAGE];

    if (lastPageViewKeyRef.current === pageViewKey || previouslyTrackedPageView === pageViewKey) {
      return;
    }

    lastPageViewKeyRef.current = pageViewKey;
    window[PAGE_VIEW_KEY_STORAGE] = pageViewKey;

    const source = classifyAcquisitionSource(document.referrer);
    const telemetry = getMobileTelemetryContext(nextPathname);
    const utmParams = pickUtmParams(searchParams);
    const locale = getLocaleFromPathname(nextPathname);
    const pageTitle = document.title;

    sendAcquisitionEvent({
      ...utmParams,
      ...source,
      connectionType: telemetry.connectionType,
      deviceBucket: telemetry.deviceBucket,
      event: 'page_view',
      locale,
      pageTitle,
      path: nextPathname,
      reducedMotion: telemetry.reducedMotion,
      routeGroup: telemetry.routeGroup,
      saveData: telemetry.saveData,
      viewportBucket: telemetry.viewportBucket,
    });

    if (isAiAcquisitionSource(source)) {
      seoAnalytics.aiReferralSession({
        ...utmParams,
        locale,
        pageTitle,
        path: nextPathname,
        referrerHost: source.referrerHost,
        routeGroup: telemetry.routeGroup,
        sourceName: source.sourceName,
        sourceType: source.sourceType,
      });
    }
  });

  const handleDocumentClick = useEffectEvent((event: MouseEvent) => {
    if (!pathname || !isAcquisitionRoute(pathname)) {
      return;
    }

    const target = event.target as HTMLElement | null;
    const anchor = target?.closest<HTMLAnchorElement>('a[href]');

    if (!anchor) {
      return;
    }

    const datasetCtaId = anchor.dataset.seoCta
      ? (anchor.dataset.seoCta as ReturnType<typeof classifyCtaHref>)
      : undefined;
    const ctaId = datasetCtaId ?? classifyCtaHref(anchor.href, window.location.origin);

    if (!ctaId) {
      return;
    }

    const source = classifyAcquisitionSource(document.referrer);
    const telemetry = getMobileTelemetryContext(pathname);
    const utmParams = pickUtmParams(new URLSearchParams(window.location.search));
    const locale = getLocaleFromPathname(pathname);
    const pageTitle = document.title;
    const ctaZone = anchor.dataset.seoZone;

    sendAcquisitionEvent({
      ...utmParams,
      ...source,
      connectionType: telemetry.connectionType,
      ctaHref: anchor.pathname,
      ctaId,
      ctaZone,
      deviceBucket: telemetry.deviceBucket,
      event: 'cta_click',
      locale,
      pageTitle,
      path: pathname,
      reducedMotion: telemetry.reducedMotion,
      routeGroup: telemetry.routeGroup,
      saveData: telemetry.saveData,
      viewportBucket: telemetry.viewportBucket,
    });

    const seoEventName = resolveSeoCtaEventName({
      pathname,
      ctaId,
      ctaZone,
    });
    const seoProperties = {
      ...utmParams,
      ctaId,
      ctaZone,
      locale,
      pageTitle,
      path: pathname,
      referrerHost: source.referrerHost,
      sourceName: source.sourceName,
      sourceType: source.sourceType,
    };

    if (seoEventName === 'seo.landing_cta_click') {
      seoAnalytics.landingCtaClick(seoProperties);
    }

    if (seoEventName === 'seo.download_cta_click') {
      seoAnalytics.downloadCtaClick(seoProperties);
    }

    if (seoEventName === 'seo.help_contact_click') {
      seoAnalytics.helpContactClick(seoProperties);
    }
  });

  useEffect(() => {
    if (!pathname) {
      return;
    }

    const run = () => handlePageView(pathname);

    if ('requestIdleCallback' in window) {
      const idleId = window.requestIdleCallback(run, { timeout: 1500 });
      return () => window.cancelIdleCallback(idleId);
    }

    const timeoutId = setTimeout(run, 0);
    return () => clearTimeout(timeoutId);
  }, [pathname]);

  useEffect(() => {
    document.addEventListener('click', handleDocumentClick, { capture: true });
    return () => document.removeEventListener('click', handleDocumentClick, { capture: true });
  }, []);

  return null;
}
