'use client';

import { useSyncExternalStore } from 'react';
import { MOBILE_BREAKPOINTS } from '@/shared/config/mobile-standards';
import { type MotionCapabilitySnapshot, useMotionCapability } from './use-motion-capability';

export type VisualTier = 'minimal' | 'reduced' | 'full';
const VISUAL_TIER_RANK: Record<VisualTier, number> = {
  minimal: 0,
  reduced: 1,
  full: 2,
};

export const FULL_VISUAL_MIN_WIDTH = MOBILE_BREAKPOINTS.tabletMax + 1;
const SSR_VIEWPORT_WIDTH = 0;

function subscribeToViewport(callback: () => void) {
  if (typeof window === 'undefined') {
    return () => {};
  }

  window.addEventListener('resize', callback, { passive: true });
  window.addEventListener('orientationchange', callback, { passive: true });

  return () => {
    window.removeEventListener('resize', callback);
    window.removeEventListener('orientationchange', callback);
  };
}

function getViewportWidth() {
  if (typeof window === 'undefined') {
    return SSR_VIEWPORT_WIDTH;
  }

  return window.innerWidth;
}

export function resolveVisualTier(
  capability: Pick<MotionCapabilitySnapshot, 'allowPointerEffects' | 'hasFinePointer' | 'isLowPowerDevice'>,
  viewportWidth: number,
): VisualTier {
  if (capability.isLowPowerDevice) {
    return 'minimal';
  }

  if (viewportWidth < FULL_VISUAL_MIN_WIDTH || !capability.hasFinePointer || !capability.allowPointerEffects) {
    return 'reduced';
  }

  return 'full';
}

export function meetsVisualTier(currentTier: VisualTier, minimumTier: VisualTier) {
  return VISUAL_TIER_RANK[currentTier] >= VISUAL_TIER_RANK[minimumTier];
}

export function useVisualTier() {
  const motionCapability = useMotionCapability();
  const viewportWidth = useSyncExternalStore(
    subscribeToViewport,
    getViewportWidth,
    () => SSR_VIEWPORT_WIDTH,
  );
  const tier = resolveVisualTier(motionCapability, viewportWidth);

  return {
    tier,
    viewportWidth,
    isMinimal: tier === 'minimal',
    isReduced: tier === 'reduced',
    isFull: tier === 'full',
  };
}
