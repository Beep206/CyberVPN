'use client';

import { useCallback, useMemo, useState } from 'react';

export const MARKETING_SCENE_CANVAS_PERFORMANCE = {
  min: 0.5,
  max: 1,
  debounce: 200,
} as const;

export const MARKETING_SCENE_GL = {
  antialias: false,
  alpha: true,
  powerPreference: 'high-performance' as const,
  stencil: false,
  depth: true,
} as const;

interface AdaptiveSceneDprOptions {
  initial?: number;
  max?: number;
  min?: number;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function roundDpr(value: number) {
  return Math.round(value * 100) / 100;
}

export function useAdaptiveSceneDpr({
  initial = 1,
  max = 1.25,
  min = 0.75,
}: AdaptiveSceneDprOptions = {}) {
  const clampedInitial = clamp(initial, min, max);
  const [dpr, setDpr] = useState(clampedInitial);

  const factor = useMemo(() => {
    if (max === min) {
      return 1;
    }

    return (clampedInitial - min) / (max - min);
  }, [clampedInitial, max, min]);

  const onChange = useCallback(
    ({ factor: nextFactor }: { factor: number }) => {
      const nextDpr = roundDpr(min + (max - min) * nextFactor);

      setDpr((current) => (current === nextDpr ? current : nextDpr));
    },
    [max, min],
  );

  const onFallback = useCallback(() => {
    setDpr(min);
  }, [min]);

  return {
    dpr,
    monitorProps: {
      factor,
      flipflops: 3,
      onChange,
      onFallback,
    },
  };
}
