'use client';

import { useLayoutEffect, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { measurePerformance, markPerformance, PerformanceMarks } from '@/shared/lib/web-vitals';

interface ScenePerformanceMetricsProps {
  sceneName: string;
}

function getReadyMark(sceneName: string) {
  return `${PerformanceMarks.THREE_SCENE_READY}:${sceneName}`;
}

function getFirstFrameMark(sceneName: string) {
  return `${PerformanceMarks.THREE_FIRST_FRAME}:${sceneName}`;
}

export function ScenePerformanceMetrics({ sceneName }: ScenePerformanceMetricsProps) {
  const didMarkFirstFrame = useRef(false);
  const didMarkReady = useRef(false);

  useLayoutEffect(() => {
    if (didMarkReady.current) {
      return;
    }

    didMarkReady.current = true;
    markPerformance(getReadyMark(sceneName), { scene: sceneName });
  }, [sceneName]);

  useFrame(() => {
    if (didMarkFirstFrame.current) {
      return;
    }

    if (!didMarkReady.current) {
      didMarkReady.current = true;
      markPerformance(getReadyMark(sceneName), { scene: sceneName });
    }

    didMarkFirstFrame.current = true;

    const readyMark = getReadyMark(sceneName);
    const firstFrameMark = getFirstFrameMark(sceneName);

    markPerformance(firstFrameMark, { scene: sceneName });

    try {
      measurePerformance(`${sceneName}-first-frame-latency`, readyMark, firstFrameMark);
    } catch {
      // Ignore duplicate/late mark races in development.
    }
  });

  return null;
}
