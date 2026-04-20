'use client';

import { useEffect, useState } from 'react';
import { meetsVisualTier, type VisualTier, useVisualTier } from './use-visual-tier';

type EnhancementDeferMode = 'immediate' | 'idle';

interface UseEnhancementReadyOptions {
  defer?: EnhancementDeferMode;
  enabled?: boolean;
  idleTimeoutMs?: number;
  minimumTier?: VisualTier;
}

const DEFAULT_IDLE_TIMEOUT_MS = 200;

function scheduleOnIdle(callback: () => void, timeout: number) {
  if (typeof window === 'undefined') {
    return () => {};
  }

  if (typeof window.requestIdleCallback === 'function') {
    const idleCallbackId = window.requestIdleCallback(callback, { timeout });

    return () => {
      window.cancelIdleCallback?.(idleCallbackId);
    };
  }

  const timeoutId = window.setTimeout(callback, timeout);

  return () => {
    window.clearTimeout(timeoutId);
  };
}

export function useEnhancementReady({
  defer = 'idle',
  enabled = true,
  idleTimeoutMs = DEFAULT_IDLE_TIMEOUT_MS,
  minimumTier = 'full',
}: UseEnhancementReadyOptions = {}) {
  const { tier } = useVisualTier();
  const canEnhance = enabled && meetsVisualTier(tier, minimumTier);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!canEnhance) {
      const timeoutId = window.setTimeout(() => {
        setIsReady(false);
      }, 0);

      return () => {
        window.clearTimeout(timeoutId);
      };
    }

    if (defer === 'immediate') {
      const timeoutId = window.setTimeout(() => {
        setIsReady(true);
      }, 0);

      return () => {
        window.clearTimeout(timeoutId);
      };
    }

    const resetTimeoutId = window.setTimeout(() => {
      setIsReady(false);
    }, 0);
    const cancelIdleSchedule = scheduleOnIdle(() => {
      setIsReady(true);
    }, idleTimeoutMs);

    return () => {
      window.clearTimeout(resetTimeoutId);
      cancelIdleSchedule();
    };
  }, [canEnhance, defer, idleTimeoutMs]);

  return {
    canEnhance,
    isReady,
    tier,
  };
}
