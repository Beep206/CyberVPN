'use client';

import { useSyncExternalStore } from 'react';
import { useReducedMotion } from 'motion/react';

interface NavigatorConnectionLike {
  addEventListener?: (type: string, listener: EventListenerOrEventListenerObject | null) => void;
  removeEventListener?: (type: string, listener: EventListenerOrEventListenerObject | null) => void;
  effectiveType?: string;
  saveData?: boolean;
}

interface NavigatorWithPerformanceHints extends Navigator {
  connection?: NavigatorConnectionLike;
  deviceMemory?: number;
}

interface MotionCapabilitySnapshot {
  allowAmbientAnimations: boolean;
  allowPointerEffects: boolean;
  isLowPowerDevice: boolean;
}

const SSR_SNAPSHOT: MotionCapabilitySnapshot = {
  allowAmbientAnimations: false,
  allowPointerEffects: false,
  isLowPowerDevice: true,
};

let lastSnapshot: MotionCapabilitySnapshot = SSR_SNAPSHOT;

const MIN_CPU_CORES = 4;
const MIN_DEVICE_MEMORY_GB = 4;

function getSnapshot(prefersReducedMotion: boolean): MotionCapabilitySnapshot {
  if (typeof window === 'undefined') {
    return SSR_SNAPSHOT;
  }

  const nav = navigator as NavigatorWithPerformanceHints;
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  const saveDataEnabled = nav.connection?.saveData ?? false;
  const lowBandwidth = ['slow-2g', '2g'].includes(nav.connection?.effectiveType ?? '');
  const lowCoreCount = (nav.hardwareConcurrency ?? MIN_CPU_CORES) < MIN_CPU_CORES;
  const lowMemory = typeof nav.deviceMemory === 'number' && nav.deviceMemory < MIN_DEVICE_MEMORY_GB;
  const isLowPowerDevice = prefersReducedMotion || saveDataEnabled || lowBandwidth || lowCoreCount || lowMemory;

  const nextSnapshot = {
    allowAmbientAnimations: !isLowPowerDevice,
    allowPointerEffects: !isLowPowerDevice && finePointer,
    isLowPowerDevice,
  };

  if (
    lastSnapshot.allowAmbientAnimations === nextSnapshot.allowAmbientAnimations &&
    lastSnapshot.allowPointerEffects === nextSnapshot.allowPointerEffects &&
    lastSnapshot.isLowPowerDevice === nextSnapshot.isLowPowerDevice
  ) {
    return lastSnapshot;
  };

  lastSnapshot = nextSnapshot;

  return nextSnapshot;
}

function subscribe(callback: () => void) {
  if (typeof window === 'undefined') {
    return () => {};
  }

  const finePointerQuery = window.matchMedia('(hover: hover) and (pointer: fine)');
  const connection = (navigator as NavigatorWithPerformanceHints).connection;

  const notify = () => callback();

  finePointerQuery.addEventListener?.('change', notify);
  connection?.addEventListener?.('change', notify);

  return () => {
    finePointerQuery.removeEventListener?.('change', notify);
    connection?.removeEventListener?.('change', notify);
  };
}

export function useMotionCapability() {
  const prefersReducedMotion = useReducedMotion();

  return useSyncExternalStore(
    subscribe,
    () => getSnapshot(Boolean(prefersReducedMotion)),
    () => SSR_SNAPSHOT,
  );
}
