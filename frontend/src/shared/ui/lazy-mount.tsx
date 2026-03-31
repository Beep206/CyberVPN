'use client';

import type { ReactNode } from 'react';
import { useEffect, useRef, useState } from 'react';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import type { VisualTier } from '@/shared/hooks/use-visual-tier';

interface LazyMountProps {
  children: ReactNode;
  className?: string;
  defer?: 'immediate' | 'idle';
  enabled?: boolean;
  minimumTier?: VisualTier;
  placeholder?: ReactNode;
  rootMargin?: string;
}

export function LazyMount({
  children,
  className,
  defer = 'immediate',
  enabled = true,
  minimumTier = 'minimal',
  placeholder = null,
  rootMargin = '300px 0px',
}: LazyMountProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(
    () => enabled && typeof window !== 'undefined' && typeof IntersectionObserver === 'undefined',
  );
  const { isReady } = useEnhancementReady({
    minimumTier,
    defer,
    enabled: enabled && isVisible,
  });

  useEffect(() => {
    if (!enabled || isVisible) {
      return;
    }

    const element = ref.current;

    if (!element || typeof IntersectionObserver === 'undefined') {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [enabled, isVisible, rootMargin]);

  return <div ref={ref} className={className}>{isReady ? children : placeholder}</div>;
}
