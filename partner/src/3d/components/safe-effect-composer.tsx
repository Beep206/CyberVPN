'use client';

import { type ComponentProps, useEffect, useState } from 'react';
import { useThree } from '@react-three/fiber';
import { EffectComposer as PostEffectComposer } from '@react-three/postprocessing';

type SafeEffectComposerProps = ComponentProps<typeof PostEffectComposer>;

export function SafeEffectComposer(props: SafeEffectComposerProps) {
  const gl = useThree((state) => state.gl);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let frameId = 0;
    let cancelled = false;

    const checkRenderer = () => {
      if (cancelled) return;

      const hasContext = typeof gl.getContextAttributes === 'function' && gl.getContextAttributes() !== null;
      const isConnected = Boolean(gl.domElement?.isConnected);

      if (hasContext && isConnected) {
        setIsReady(true);
        return;
      }

      frameId = window.requestAnimationFrame(checkRenderer);
    };

    checkRenderer();

    return () => {
      cancelled = true;
      if (frameId) {
        window.cancelAnimationFrame(frameId);
      }
    };
  }, [gl]);

  if (!isReady) {
    return null;
  }

  return <PostEffectComposer {...props} />;
}
