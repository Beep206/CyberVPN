'use client';

import { useEffect, useState } from 'react';
import {
  readReferralAttribution,
  REFERRAL_ATTRIBUTION_CHANGED_EVENT,
  type ReferralAttributionSnapshot,
} from './storage';

export function useReferralAttributionSnapshot(): ReferralAttributionSnapshot | null {
  const [snapshot, setSnapshot] = useState<ReferralAttributionSnapshot | null>(null);

  useEffect(() => {
    const refresh = () => setSnapshot(readReferralAttribution());
    refresh();
    window.addEventListener(REFERRAL_ATTRIBUTION_CHANGED_EVENT, refresh);
    window.addEventListener('storage', refresh);
    return () => {
      window.removeEventListener(REFERRAL_ATTRIBUTION_CHANGED_EVENT, refresh);
      window.removeEventListener('storage', refresh);
    };
  }, []);

  return snapshot;
}
