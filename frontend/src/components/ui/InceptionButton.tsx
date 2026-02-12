"use client";

import React, { useRef, useState, useEffect } from "react";
import { toPng } from "html-to-image";
import { Canvas } from "@react-three/fiber";
import * as THREE from "three";
import { CrumbleEffect } from "@/components/effects/CrumbleEffect";
import { ErrorBoundary } from "@/shared/ui/error-boundary";

interface InceptionButtonProps {
  children: React.ReactNode;
  onClick?: React.MouseEventHandler;
  className?: string;
}

export function InceptionButton({ children, onClick, className = "", wrapperClassName = "" }: InceptionButtonProps & { wrapperClassName?: string }) {
  const elementRef = useRef<HTMLDivElement>(null);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [isExploding, setIsExploding] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [progress, setProgress] = useState(0);

  const handleCapture = async () => {
    if (!elementRef.current) return;

    // Capture the element
    try {
      // html-to-image is much better at modern CSS (like oklch/lab)
      const dataUrl = await toPng(elementRef.current, {
        cacheBust: true,
        pixelRatio: 1, // Keep it light
        skipAutoScale: true,
      });

      const loader = new THREE.TextureLoader();

      loader.load(dataUrl, (loadedTexture) => {
        // Correct color space
        loadedTexture.colorSpace = THREE.SRGBColorSpace;

        setDimensions({
          width: elementRef.current?.offsetWidth || 0,
          height: elementRef.current?.offsetHeight || 0
        });
        setTexture(loadedTexture);
        setIsExploding(true);
      });

    } catch (err) {
      console.error("Failed to capture element:", err);
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    // Don't prevent default for submit buttons - they need to trigger form submission
    const target = e.target as HTMLElement;
    const isSubmitButton = target.closest('button[type="submit"]');

    if (!isSubmitButton) {
      e.preventDefault();
    }

    if (isExploding) return; // Prevent double click

    // Trigger user onClick first
    onClick?.(e);

    // Start effect
    handleCapture();
  };

  // Animation loop logic (drive the progress prop)
  useEffect(() => {
    if (!isExploding) return;

    let start: number;
    let animId: number;
    const duration = 2000; // 2 seconds total for out and back

    const animate = (timestamp: number) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const t = Math.min(elapsed / duration, 1);

      // Phases: 
      // 0 -> 0.4 : Explode (0 to 1)
      // 0.4 -> 0.6 : Hang/Slow move
      // 0.6 -> 1.0 : Assemble (1 to 0)

      let p = 0;
      if (t < 0.4) {
        // Explode
        p = t / 0.4; // 0 to 1
      } else if (t < 0.6) {
        // Hang
        p = 1.0;
      } else {
        // Return
        const tRet = (t - 0.6) / 0.4;
        p = 1.0 - tRet; // 1 to 0
      }

      setProgress(p);

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
      {/* Original Element */}
      <div
        ref={elementRef}
        onClick={handleClick}
        className={`${className} ${isExploding ? 'opacity-0 pointer-events-none' : 'opacity-100'} transition-opacity duration-0`}
      >
        {children}
      </div>

      {/* 3D Overlay */}
      {isExploding && texture && (
        <div
          className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none z-50"
          style={{
            width: dimensions.width * 4, // Make canvas bigger to allow particles to fly out
            height: dimensions.height * 4
          }}
        >
          <ErrorBoundary label="Crumble Effect">
            <Canvas
              orthographic
              camera={{
                zoom: 1,
                position: [0, 0, 100],
                left: -dimensions.width * 2,
                right: dimensions.width * 2,
                top: dimensions.height * 2,
                bottom: -dimensions.height * 2
              }}
              gl={{ alpha: true, antialias: true }}
              className="w-full h-full"
            >
              <ambientLight intensity={1} />
              <CrumbleEffect
                texture={texture}
                width={dimensions.width}
                height={dimensions.height}
                progress={progress}
              />
            </Canvas>
          </ErrorBoundary>
        </div>
      )}
    </div>
  );
}
