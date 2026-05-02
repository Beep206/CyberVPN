'use client';

import { TrafficAnalyticsReporter } from '@/shared/ui/atoms/traffic-analytics-reporter';
import { FrontendRuntimeReporter } from '@/shared/ui/atoms/frontend-runtime-reporter';
import { WebVitalsReporter } from '@/shared/ui/atoms/web-vitals-reporter';

export function AnalyticsReportersClient() {
  return (
    <>
      <FrontendRuntimeReporter surface="partner_portal" />
      <WebVitalsReporter />
      <TrafficAnalyticsReporter />
    </>
  );
}
