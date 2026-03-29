'use client';

import { Canvas } from '@react-three/fiber';
import { CrumbleEffect } from '@/components/effects/CrumbleEffect';
import { ErrorBoundary } from '@/shared/ui/error-boundary';
import type * as THREE from 'three';

interface InceptionOverlayProps {
  height: number;
  progress: number;
  texture: THREE.Texture;
  width: number;
}

export function InceptionOverlay({
  height,
  progress,
  texture,
  width,
}: InceptionOverlayProps) {
  return (
    <div
      className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none z-50"
      style={{
        width: width * 4,
        height: height * 4,
      }}
    >
      <ErrorBoundary label="Crumble Effect">
        <Canvas
          orthographic
          camera={{
            zoom: 1,
            position: [0, 0, 100],
            left: -width * 2,
            right: width * 2,
            top: height * 2,
            bottom: -height * 2,
          }}
          gl={{ alpha: true, antialias: true }}
          className="w-full h-full"
        >
          <ambientLight intensity={1} />
          <CrumbleEffect
            texture={texture}
            width={width}
            height={height}
            progress={progress}
          />
        </Canvas>
      </ErrorBoundary>
    </div>
  );
}
