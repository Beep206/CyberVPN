'use client';

import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { PerformanceMonitor } from '@react-three/drei';
import { useInView } from 'motion/react';
import { Bloom, Noise } from '@react-three/postprocessing';
import { ScenePerformanceMetrics } from '@/3d/components/scene-performance-metrics';
import '@/3d/shaders/AntiDPIShader';
import {
    MARKETING_SCENE_CANVAS_PERFORMANCE,
    MARKETING_SCENE_GL,
    useAdaptiveSceneDpr,
} from '@/3d/lib/scene-performance';
import { createDeterministicRandom, randomInRange, randomSigned } from '@/3d/lib/seeded-random';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';

const SCANNER_POS = 0.0;
const BOUND_MIN_X = -5.0;
const BOUND_MAX_X = 5.0;

type AntiDPIShaderMaterial = THREE.ShaderMaterial & {
    uniforms: {
        time: { value: number };
    };
};

function InstancedPackets({ count = 800 }: { count?: number }) {
    const mesh = useRef<THREE.InstancedMesh>(null!);
    const materialRef = useRef<AntiDPIShaderMaterial>(null!);

    const [offsets, speeds] = useMemo(() => {
        const random = createDeterministicRandom(count * 17 + 13);
        const off = new Float32Array(count * 3);
        const spd = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            off[i * 3 + 0] = randomInRange(random, BOUND_MIN_X, BOUND_MAX_X);
            off[i * 3 + 1] = randomSigned(random, 1.1);
            off[i * 3 + 2] = randomSigned(random, 0.75);

            spd[i * 3 + 0] = randomInRange(random, 0.8, 2.3);
            spd[i * 3 + 1] = randomInRange(random, 0.4, 0.8);
            spd[i * 3 + 2] = randomInRange(random, 0, Math.PI * 2);
        }
        return [off, spd];
    }, [count]);

    useFrame((state) => {
        if (materialRef.current) {
            materialRef.current.uniforms.time.value = state.clock.getElapsedTime();
        }
    });

    return (
        <instancedMesh 
            ref={mesh} 
            args={[undefined, undefined, count]} 
            renderOrder={5} 
            frustumCulled={false}
        >
            <sphereGeometry args={[0.04, 16, 16]}>
                <instancedBufferAttribute attach="attributes-aOffset" args={[offsets, 3]} />
                <instancedBufferAttribute attach="attributes-aSpeed" args={[speeds, 3]} />
            </sphereGeometry>
            {/* @ts-expect-error Custom R3F shader node */}
            <antiDPIShader 
                ref={materialRef} 
                transparent 
                depthWrite={false}
                uScannerPos={SCANNER_POS}
                uBoundMinX={BOUND_MIN_X}
                uBoundMaxX={BOUND_MAX_X}
                displacementRaw={0.06} // Subtle organic wobble
            />
        </instancedMesh>
    );
}

function ScannerAndShield() {
    const scannerRef = useRef<THREE.Mesh>(null!);

    useFrame((state) => {
        const t = state.clock.getElapsedTime();
        if (scannerRef.current) {
            const mat = scannerRef.current.material as THREE.MeshBasicMaterial;
            mat.opacity = 0.3 + Math.sin(t * 8) * 0.1;
        }
    });

    return (
        <group>
            {/* Scanner Line */}
            <mesh ref={scannerRef} position={[SCANNER_POS, 0, 0]} renderOrder={10}>
                <planeGeometry args={[0.06, 5]} />
                <meshBasicMaterial color="#00ffff" transparent opacity={0.4} blending={THREE.AdditiveBlending} depthWrite={false} />
            </mesh>
            
            {/* The Shield Tunnel */}
            <group position={[2.8, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
                <mesh renderOrder={1}>
                    <cylinderGeometry args={[1.5, 1.5, 6, 32, 1, true]} />
                    <meshStandardMaterial
                        color="#002222"
                        emissive="#004444"
                        emissiveIntensity={0.6}
                        transparent
                        opacity={0.15}
                        side={THREE.DoubleSide}
                        depthWrite={false}
                    />
                </mesh>
                
                <mesh renderOrder={2}>
                   <cylinderGeometry args={[1.52, 1.52, 6, 16, 8, true]} />
                   <meshBasicMaterial 
                        color="#00ffff" 
                        wireframe 
                        transparent 
                        opacity={0.1} 
                        blending={THREE.AdditiveBlending}
                        depthWrite={false}
                   />
                </mesh>
            </group>
        </group>
    );
}

export default function AntiDPIScene3D() {
    const containerRef = useRef<HTMLDivElement>(null);
    const isInView = useInView(containerRef, { margin: "200px" });
    const { dpr, monitorProps } = useAdaptiveSceneDpr({ initial: 1, min: 0.75, max: 1.2 });

    return (
        <div ref={containerRef} className="absolute inset-0 w-full h-full pointer-events-none">
            <Canvas
                frameloop={isInView ? 'always' : 'never'}
                performance={MARKETING_SCENE_CANVAS_PERFORMANCE}
                camera={{ position: [0, 0, 8], fov: 40 }}
                gl={MARKETING_SCENE_GL}
                dpr={dpr}
            >
                <ScenePerformanceMetrics sceneName="anti-dpi" />
                <PerformanceMonitor {...monitorProps} />
                
                <ambientLight intensity={0.5} />
                <pointLight position={[-4, 2, 4]} intensity={1.5} color="#ff0088" />
                <pointLight position={[4, -2, 4]} intensity={1.5} color="#00ffff" />

                <InstancedPackets count={800} />
                <ScannerAndShield />

                <SafeEffectComposer multisampling={0}>
                    <Bloom luminanceThreshold={0.2} intensity={1.2} radius={0.4} />
                    <Noise opacity={0.05} />
                </SafeEffectComposer>
            </Canvas>
        </div>
    );
}
