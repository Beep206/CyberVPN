'use client';

import { useEffect } from 'react';
import { reportWebVitals } from '@/shared/lib/web-vitals';

/**
 * Web Vitals Reporter Component
 *
 * Client component that initializes Web Vitals tracking.
 * Should be mounted in the root layout.
 */
export function WebVitalsReporter() {
  useEffect(() => {
    // Initialize Web Vitals reporting
    reportWebVitals();
  }, []);

  // This component doesn't render anything
  return null;
}
