'use client';

import { TrafficAnalyticsReporter } from '@/shared/ui/atoms/traffic-analytics-reporter';
import { WebVitalsReporter } from '@/shared/ui/atoms/web-vitals-reporter';

export function AnalyticsReportersClient() {
  return (
    <>
      <WebVitalsReporter />
      <TrafficAnalyticsReporter />
    </>
  );
}
