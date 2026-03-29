'use client';

import { Canvas, useFrame } from '@react-three/fiber';
import { PerformanceMonitor } from '@react-three/drei';
import { Bloom } from '@react-three/postprocessing';
import { useInView } from 'motion/react';
import { usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { ScenePerformanceMetrics } from '@/3d/components/scene-performance-metrics';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';
import {
  MARKETING_SCENE_CANVAS_PERFORMANCE,
  MARKETING_SCENE_GL,
  useAdaptiveSceneDpr,
} from '@/3d/lib/scene-performance';
import { useMotionCapability } from '@/shared/hooks/use-motion-capability';
import { ErrorBoundary } from '@/shared/ui/error-boundary';

const SPEED_TUNNEL_VERTEX_SHADER = `
  uniform float uTime;
  uniform float uSpeedMultiplier;
  attribute float aSpeed;

  varying float vAlpha;

  void main() {
    vec3 transformed = position;
    transformed.z = mod(position.z + uTime * aSpeed * uSpeedMultiplier * 10.0, 100.0) - 80.0;

    vec4 mvPosition = modelViewMatrix * vec4(transformed, 1.0);
    float depthFactor = clamp((20.0 - transformed.z) / 100.0, 0.15, 1.0);

    vAlpha = depthFactor;
    gl_PointSize = mix(1.4, 4.6, depthFactor);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const SPEED_TUNNEL_FRAGMENT_SHADER = `
  uniform vec3 uColor;
  varying float vAlpha;

  void main() {
    vec2 uv = gl_PointCoord - vec2(0.5);
    float distanceToCenter = length(uv);
    float glow = smoothstep(0.5, 0.0, distanceToCenter);

    gl_FragColor = vec4(uColor, glow * vAlpha * 0.95);
  }
`;

function generateStarfieldData(count: number) {
  const positions = new Float32Array(count * 3);
  const speeds = new Float32Array(count);

  for (let i = 0; i < count; i += 1) {
    positions[i * 3] = (Math.random() - 0.5) * 50;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 50;
    positions[i * 3 + 2] = Math.random() * 100;
    speeds[i] = 0.85 + Math.random() * 0.3;
  }

  return { positions, speeds };
}

function WarpStarfield({
  color = '#00ffff',
  count,
  speed = 2,
}: {
  color?: string;
  count: number;
  speed?: number;
}) {
  const points = useRef<THREE.Points>(null!);
  const materialRef = useRef<THREE.ShaderMaterial>(null!);
  const { positions, speeds } = useMemo(() => generateStarfieldData(count), [count]);

  useFrame((state, delta) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.getElapsedTime();
    }

    if (points.current) {
      points.current.rotation.z += delta * 0.1;
    }
  });

  return (
    <points ref={points} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} args={[positions, 3]} />
        <bufferAttribute attach="attributes-aSpeed" count={count} args={[speeds, 1]} />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        vertexShader={SPEED_TUNNEL_VERTEX_SHADER}
        fragmentShader={SPEED_TUNNEL_FRAGMENT_SHADER}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        uniforms={{
          uColor: { value: new THREE.Color(color) },
          uSpeedMultiplier: { value: speed },
          uTime: { value: 0 },
        }}
      />
    </points>
  );
}

export function SpeedTunnelScene() {
  const pathname = usePathname();
  const { resolvedTheme } = useTheme();
  const { allowAmbientAnimations, isLowPowerDevice } = useMotionCapability();
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { margin: '100px' });
  const { dpr, monitorProps } = useAdaptiveSceneDpr({ initial: 1, min: 0.75, max: 1.5 });

  const isDark = resolvedTheme === 'dark';
  const bgColor = isDark ? '#000000' : '#a1a1aa';
  const fogColor = isDark ? '#000000' : '#a1a1aa';
  const starColor1 = isDark ? '#00ffff' : '#0891b2';
  const starColor2 = isDark ? '#ff00ff' : '#9333ea';
  const starCount = isLowPowerDevice ? 1800 : 3000;
  const bloomIntensity = isDark ? (isLowPowerDevice ? 1.2 : 2) : 0.5;
  const shouldAnimate = allowAmbientAnimations && isInView;

  return (
    <div ref={containerRef} className="w-full h-full absolute inset-0 bg-background transition-colors duration-500">
      <ErrorBoundary fallback={<div className="w-full h-full bg-background flex items-center justify-center text-xs text-muted-foreground">Speed Tunnel Disabled (Extension Conflict)</div>}>
        <Canvas
          key={pathname}
          frameloop={shouldAnimate ? 'always' : 'never'}
          performance={MARKETING_SCENE_CANVAS_PERFORMANCE}
          camera={{ position: [0, 0, 5], fov: 60 }}
          gl={MARKETING_SCENE_GL}
          dpr={dpr}
        >
          <ScenePerformanceMetrics sceneName="speed-tunnel" />
          <PerformanceMonitor {...monitorProps} />
          <color attach="background" args={[bgColor]} />
          <fog attach="fog" args={[fogColor, 5, 20]} />

          <WarpStarfield count={starCount} speed={3} color={starColor1} />
          <WarpStarfield count={starCount} speed={4} color={starColor2} />

          <SafeEffectComposer multisampling={0} enableNormalPass={false}>
            <Bloom
              luminanceThreshold={isDark ? 0.5 : 1.1}
              radius={isDark ? 0.8 : 0.5}
              intensity={bloomIntensity}
              resolutionScale={0.5}
            />
          </SafeEffectComposer>
        </Canvas>
      </ErrorBoundary>
    </div>
  );
}
