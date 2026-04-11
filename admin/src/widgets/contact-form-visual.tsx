'use client';

import { Canvas } from '@react-three/fiber';
import { Bloom, Glitch, Noise } from '@react-three/postprocessing';
import * as THREE from 'three';
import { ContactGlobe3D } from '@/3d/scenes/ContactGlobe3D';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';
import { useCanvasHost } from '@/shared/hooks/use-canvas-host';

interface ContactFormVisualProps {
  isTyping: boolean;
  isEncrypting: boolean;
  isSuccess: boolean;
  isHoveringSubmit: boolean;
}

export function ContactFormVisual({
  isTyping,
  isEncrypting,
  isSuccess,
  isHoveringSubmit,
}: ContactFormVisualProps) {
  const { host, setHostRef } = useCanvasHost<HTMLDivElement>();

  return (
    <div ref={setHostRef} className="h-full w-full">
      {host ? (
        <Canvas eventSource={host} camera={{ position: [0, 0, 8], fov: 45 }}>
          <ContactGlobe3D
            isTyping={isTyping}
            isEncrypting={isEncrypting}
            isSuccess={isSuccess}
            isHoveringSubmit={isHoveringSubmit}
          />

          <SafeEffectComposer autoClear={false}>
            <Bloom
              luminanceThreshold={0.2}
              mipmapBlur
              intensity={isEncrypting ? 2.5 : isSuccess ? 3.0 : 1.5}
            />
            <Noise opacity={0.035} />
            <Glitch
              delay={new THREE.Vector2(0.5, 1.5)}
              duration={new THREE.Vector2(0.1, 0.3)}
              active={isEncrypting}
            />
          </SafeEffectComposer>
        </Canvas>
      ) : null}
    </div>
  );
}
