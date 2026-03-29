'use client';

import type { ReactNode } from 'react';
import { useEffect, useRef, useState } from 'react';

interface LazyMountProps {
  children: ReactNode;
  className?: string;
  placeholder?: ReactNode;
  rootMargin?: string;
}

export function LazyMount({
  children,
  className,
  placeholder = null,
  rootMargin = '300px 0px',
}: LazyMountProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(
    () => typeof window !== 'undefined' && typeof IntersectionObserver === 'undefined',
  );

  useEffect(() => {
    if (isVisible) {
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
  }, [isVisible, rootMargin]);

  return <div ref={ref} className={className}>{isVisible ? children : placeholder}</div>;
}
