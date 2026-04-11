'use client';

import { useCallback, useRef, useState } from 'react';

// R3F resolves event targets during async canvas setup.
// Keep a stable mounted host element so Canvas never tries to connect to null.
export function useCanvasHost<T extends HTMLElement>() {
  const containerRef = useRef<T | null>(null);
  const [host, setHost] = useState<T | null>(null);

  const setHostRef = useCallback((node: T | null) => {
    containerRef.current = node;
    setHost(node);
  }, []);

  return {
    containerRef,
    host,
    setHostRef,
  };
}
