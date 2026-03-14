'use client';

import React, { useRef, useMemo, useState } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { useInView } from 'motion/react';
import { EffectComposer, Bloom, ChromaticAberration, Noise } from '@react-three/postprocessing';
import { PerformanceMonitor, Line } from '@react-three/drei';

// Import Custom Shaders
import '@/3d/shaders/FastTrackShader';

// Parallax Group
function ParallaxGroup({ children }: { children: React.ReactNode }) {
    const group = useRef<THREE.Group>(null!);
    useFrame((state) => {
        const { pointer } = state;
        group.current.rotation.y = THREE.MathUtils.lerp(group.current.rotation.y, pointer.x * 0.1, 0.1);
        group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, -pointer.y * 0.1, 0.1);
    });
    return <group ref={group}>{children}</group>;
}

// Data Trails Instanced Mesh
const NUM_PATHS = 12;
const INSTANCES_PER_PATH = 40;
const TOTAL_INSTANCES = NUM_PATHS * INSTANCES_PER_PATH;
const HUB_POS = new THREE.Vector3(0, 0, -5);

function DataTrails() {
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    const materialRef = useRef<any>(null!);

    const { aP0, aP1, aP2, aP3, aParams, aColorMix, pathLines } = useMemo(() => {
        const p0Array = new Float32Array(TOTAL_INSTANCES * 3);
        const p1Array = new Float32Array(TOTAL_INSTANCES * 3);
        const p2Array = new Float32Array(TOTAL_INSTANCES * 3);
        const p3Array = new Float32Array(TOTAL_INSTANCES * 3);
        const paramsArray = new Float32Array(TOTAL_INSTANCES * 4);
        const colorMixArray = new Float32Array(TOTAL_INSTANCES * 3);

        const lines: THREE.Vector3[][] = [];

        for (let p = 0; p < NUM_PATHS; p++) {
            // Generate Path Control Points
            const angle = (p / NUM_PATHS) * Math.PI * 2;
            const radius = 6 + Math.random() * 4;
            // Start from far away, wide spread
            const p0 = new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 10);
            
            // Curve towards center with a swirl effect
            const swirl1 = angle + Math.PI / 4;
            const p1 = new THREE.Vector3(Math.cos(swirl1) * radius * 0.8, Math.sin(swirl1) * radius * 0.8, 5);
            
            const swirl2 = angle + Math.PI / 2;
            const p2 = new THREE.Vector3(Math.cos(swirl2) * radius * 0.4, Math.sin(swirl2) * radius * 0.4, 0);
            
            const p3 = HUB_POS.clone();

            const curve = new THREE.CubicBezierCurve3(p0, p1, p2, p3);
            lines.push(curve.getPoints(20));

            for (let i = 0; i < INSTANCES_PER_PATH; i++) {
                const idx = p * INSTANCES_PER_PATH + i;
                const i3 = idx * 3;
                const i4 = idx * 4;

                p0Array.set([p0.x, p0.y, p0.z], i3);
                p1Array.set([p1.x, p1.y, p1.z], i3);
                p2Array.set([p2.x, p2.y, p2.z], i3);
                p3Array.set([p3.x, p3.y, p3.z], i3);

                // Speed, Offset, Scale Radius, Scale Length
                const speed = 0.2 + Math.random() * 0.3;
                const offset = Math.random();
                const scaleRadius = 0.3 + Math.random() * 0.7; // Thick/thin trails
                const scaleLength = 4.0 + Math.random() * 6.0;

                paramsArray.set([speed, offset, scaleRadius, scaleLength], i4);

                // Mix values for coloring
                // r = secondary vs primary mix
                // g = white mix
                colorMixArray.set([Math.random(), Math.random() > 0.8 ? 0.5 : 0.0, 0], i3);
            }
        }

        return { aP0: p0Array, aP1: p1Array, aP2: p2Array, aP3: p3Array, aParams: paramsArray, aColorMix: colorMixArray, pathLines: lines };
    }, []);

    useFrame((state) => {
        if (materialRef.current) {
            materialRef.current.time = state.clock.getElapsedTime();
        }
    });

    return (
        <group>
            {/* The Invisible Paths structure for background vibe */}
            {pathLines.map((points, i) => (
                <Line
                    key={i}
                    points={points}
                    color="#00ffff"
                    transparent
                    opacity={0.05}
                    lineWidth={1}
                />
            ))}

            <instancedMesh ref={meshRef} args={[undefined, undefined, TOTAL_INSTANCES]}>
                <cylinderGeometry args={[0.015, 0.015, 1, 8]}>
                    <instancedBufferAttribute attach="attributes-aP0" args={[aP0, 3]} />
                    <instancedBufferAttribute attach="attributes-aP1" args={[aP1, 3]} />
                    <instancedBufferAttribute attach="attributes-aP2" args={[aP2, 3]} />
                    <instancedBufferAttribute attach="attributes-aP3" args={[aP3, 3]} />
                    <instancedBufferAttribute attach="attributes-aParams" args={[aParams, 4]} />
                    <instancedBufferAttribute attach="attributes-aColorMix" args={[aColorMix, 3]} />
                </cylinderGeometry>
                {/* @ts-ignore - custom shader material */}
                <fastTrackShader 
                    ref={materialRef} 
                    transparent 
                    depthWrite={false} 
                    blending={THREE.AdditiveBlending} 
                    side={THREE.DoubleSide} 
                />
            </instancedMesh>
        </group>
    );
}

// Convergence Hub
function Hub() {
    const materialRef = useRef<any>(null!);
    
    useFrame((state) => {
        if (materialRef.current) {
            materialRef.current.time = state.clock.getElapsedTime();
        }
    });

    return (
        <group position={[0, 0, -5]}>
            <mesh>
                <sphereGeometry args={[0.5, 32, 32]} />
                {/* @ts-ignore */}
                <hubShader ref={materialRef} transparent depthWrite={false} blending={THREE.AdditiveBlending} />
            </mesh>
            <pointLight distance={10} intensity={2} color="#00ff41" />
        </group>
    );
}

export default function FastTrackScene3D() {
    const containerRef = useRef<HTMLDivElement>(null);
    const isInView = useInView(containerRef, { margin: "100px" });
    const [dpr, setDpr] = useState(1);
    const CHROMATIC_ABERRATION_OFFSET = new THREE.Vector2(0.003, 0.003);

    return (
        <div ref={containerRef} className="absolute inset-0 -z-10 bg-terminal-bg border-grid-line overflow-hidden">
            <Canvas
                frameloop={isInView ? 'always' : 'never'}
                performance={{ min: 0.5 }}
                camera={{ position: [0, 0, 8], fov: 60 }} // Looking down the Z axis
                gl={{
                    antialias: false,
                    alpha: true,
                    powerPreference: "high-performance",
                    stencil: false,
                    depth: true
                }}
                dpr={dpr}
            >
                <PerformanceMonitor 
                    onDecline={() => setDpr(0.75)} 
                    onIncline={() => setDpr(1.5)} 
                />
                
                <fog attach="fog" args={['#050510', 5, 20]} />
                <ambientLight intensity={0.2} />

                <ParallaxGroup>
                    <DataTrails />
                    <Hub />
                </ParallaxGroup>

                <EffectComposer enableNormalPass={false} multisampling={0}>
                    <Bloom luminanceThreshold={0.2} mipmapBlur intensity={1.2} radius={0.4} />
                    <Noise opacity={0.03} />
                    <ChromaticAberration offset={CHROMATIC_ABERRATION_OFFSET} radialModulation={true} modulationOffset={0.5} />
                </EffectComposer>
            </Canvas>
        </div>
    );
}
