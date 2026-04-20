'use client';

import dynamic from 'next/dynamic';
import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { useMotionCapability } from '@/shared/hooks/use-motion-capability';

const InceptionOverlay = dynamic(
  () => import('./inception-overlay').then((mod) => mod.InceptionOverlay),
  { ssr: false },
);

interface InceptionButtonProps {
  children: React.ReactNode;
  onClick?: React.MouseEventHandler;
  className?: string;
}

export function InceptionButton({ children, onClick, className = '', wrapperClassName = '' }: InceptionButtonProps & { wrapperClassName?: string }) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mountedRef = useRef(true);
  const { allowPointerEffects } = useMotionCapability();
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [isExploding, setIsExploding] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
    };
  }, []);

  const handleCapture = async () => {
    const element = elementRef.current;

    if (
      !element ||
      !allowPointerEffects ||
      !element.isConnected ||
      !element.ownerDocument
    ) {
      return;
    }

    try {
      const { toPng } = await import('html-to-image');
      if (!mountedRef.current || !element.isConnected || !element.ownerDocument) {
        return;
      }

      const width = element.offsetWidth;
      const height = element.offsetHeight;
      const dataUrl = await toPng(element, {
        cacheBust: true,
        pixelRatio: 1,
        skipAutoScale: true,
      });
      if (!mountedRef.current) {
        return;
      }

      const loader = new THREE.TextureLoader();

      loader.load(dataUrl, (loadedTexture) => {
        if (!mountedRef.current) {
          return;
        }

        loadedTexture.colorSpace = THREE.SRGBColorSpace;
        setDimensions({ width, height });
        setTexture(loadedTexture);
        setIsExploding(true);
      });
    } catch (error) {
      console.error('Failed to capture element:', error);
    }
  };

  const handleClick = (event: React.MouseEvent) => {
    const target = event.target as HTMLElement;
    const isSubmitButton = target.closest('button[type="submit"]');

    if (!isSubmitButton) {
      event.preventDefault();
    }

    if (isExploding) {
      return;
    }

    onClick?.(event);

    if (allowPointerEffects) {
      void handleCapture();
    }
  };

  useEffect(() => {
    if (!isExploding) {
      return;
    }

    let start = 0;
    let animId = 0;
    const duration = 2000;

    const animate = (timestamp: number) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const t = Math.min(elapsed / duration, 1);

      let nextProgress = 0;

      if (t < 0.4) {
        nextProgress = t / 0.4;
      } else if (t < 0.6) {
        nextProgress = 1;
      } else {
        nextProgress = 1 - (t - 0.6) / 0.4;
      }

      setProgress(nextProgress);

      if (t < 1) {
        animId = requestAnimationFrame(animate);
      } else {
        setIsExploding(false);
        setTexture(null);
        setProgress(0);
      }
    };

    animId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animId);
  }, [isExploding]);

  return (
    <div className={`relative inline-block group ${wrapperClassName}`}>
      <div
        ref={elementRef}
        onClick={handleClick}
        className={`${className} ${isExploding ? 'opacity-0 pointer-events-none' : 'opacity-100'} transition-opacity duration-0`}
      >
        {children}
      </div>

      {isExploding && texture ? (
        <InceptionOverlay
          texture={texture}
          width={dimensions.width}
          height={dimensions.height}
          progress={progress}
        />
      ) : null}
    </div>
  );
}
