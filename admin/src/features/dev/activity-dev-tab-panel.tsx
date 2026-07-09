'use client';

import { Activity, useEffect, type ReactNode } from 'react';

const DEV_ACTIVITY_MARK_PREFIX = 'cybervpn.dev_panel.activity_tab';
const SAFE_TAB_ID = /^[a-z0-9-]+$/;

export function buildDevActivityMarkName(tabId: string): string {
  const safeTabId = SAFE_TAB_ID.test(tabId) ? tabId : 'unknown';
  return `${DEV_ACTIVITY_MARK_PREFIX}.${safeTabId}.visible`;
}

export function markDevActivityTabVisible(tabId: string): void {
  if (typeof performance === 'undefined' || typeof performance.mark !== 'function') {
    return;
  }

  performance.mark(buildDevActivityMarkName(tabId));
}

interface ActivityDevTabPanelProps {
  active: boolean;
  children: ReactNode;
  tabId: string;
}

export function ActivityDevTabPanel({ active, children, tabId }: ActivityDevTabPanelProps) {
  useEffect(() => {
    if (active) {
      markDevActivityTabVisible(tabId);
    }
  }, [active, tabId]);

  return (
    <Activity mode={active ? 'visible' : 'hidden'}>
      {children}
    </Activity>
  );
}
