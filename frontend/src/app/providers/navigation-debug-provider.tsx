'use client';

import { useEffect } from 'react';
import { installNavigationDebugLogger } from '@/shared/debug/navigation-debug';

export function NavigationDebugProvider() {
  useEffect(() => installNavigationDebugLogger(), []);

  return null;
}
