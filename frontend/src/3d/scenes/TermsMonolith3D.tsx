'use client';

import * as THREE from 'three';
import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Bloom, ChromaticAberration, Noise } from '@react-three/postprocessing';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';
import { Float, Preload } from '@react-three/drei';
import { createDeterministicRandom, randomInRange, randomSigned } from '@/3d/lib/seeded-random';

function createExplosionVelocities(particleCount: number): Float32Array {
    const random = createDeterministicRandom(particleCount * 131);
    const velocities = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
        velocities[i * 3] = randomSigned(random, 15);
        velocities[i * 3 + 1] = randomSigned(random, 15);
        velocities[i * 3 + 2] = randomInRange(random, 0, 20);
    }

    return velocities;
}

function MonolithStructure({ isAccepted }: { isAccepted: boolean }) {
    const groupRef = useRef<THREE.Group>(null!);
    const materialRef = useRef<THREE.MeshStandardMaterial>(null!);

    // A monolithic black obelisk/server
    useFrame((state, delta) => {
        if (groupRef.current) {
            // Slow ominous rotation
            groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.1) * 0.1;

            // Float physics
            groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.5;
        }

        if (materialRef.current) {
            // Transition color from cyan/red to green when accepted
            const targetColor = isAccepted ? new THREE.Color('#00ff44') : new THREE.Color('#00ffff');
            materialRef.current.emissive.lerp(targetColor, delta * 2);
            materialRef.current.color.lerp(targetColor, delta * 2);
        }
    });

    return (
        <group ref={groupRef} position={[0, -5, -10]}>
            {/* The Main Obelisk */}
            <mesh position={[0, 10, 0]} castShadow receiveShadow>
                {/* Tall box geometry */}
                <boxGeometry args={[4, 20, 2]} />
                <meshStandardMaterial 
                    ref={materialRef}
                    color="#00ffff"
                    emissive="#00ffff"
                    emissiveIntensity={0.2}
                    roughness={0.2}
                    metalness={0.9}
                    wireframe={!isAccepted}
                />
            </mesh>
            
            {/* Wireframe inner scaffolding */}
            <mesh position={[0, 10, 0]}>
                <boxGeometry args={[3.8, 19.8, 1.8]} />
                <meshBasicMaterial color="#000000" />
            </mesh>
        </group>
    );
}

// Generates rings around the monolith
function DataRings({ isAccepted }: { isAccepted: boolean }) {
    const ringsRef = useRef<THREE.Group>(null!);

    useFrame((state, delta) => {
        if (ringsRef.current) {
            ringsRef.current.rotation.y += delta * 0.2;
            ringsRef.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.2) * 0.1;
            
            // Speed up rings on acceptance
            if (isAccepted) {
                ringsRef.current.rotation.y += delta * 1.5;
            }
        }
    });

    return (
        <group ref={ringsRef} position={[0, 5, -10]}>
            {[...Array(5)].map((_, i) => (
                <Float key={i} speed={2} rotationIntensity={0.5} floatIntensity={0.5} position={[0, (i - 2) * 2, 0]}>
                    <mesh rotation={[Math.PI / 2, 0, 0]}>
                        <torusGeometry args={[5 + i * 0.5, 0.02, 16, 100]} />
                        <meshStandardMaterial 
                            color={isAccepted ? '#00ff88' : '#ff0055'} 
                            emissive={isAccepted ? '#00ff88' : '#ff0055'} 
                            emissiveIntensity={isAccepted ? 2 : 1}
                        />
                    </mesh>
                </Float>
            ))}
        </group>
    );
}

// Generates exploding particles triggered on acceptance
function AcceptanceExplosion({ isAccepted }: { isAccepted: boolean }) {
    const particleCount = 2000;
    const positions = useMemo(() => {
        const random = createDeterministicRandom(particleCount * 127);
        const arr = new Float32Array(particleCount * 3);
        for (let i = 0; i < particleCount; i++) {
            // Start bunched up
            arr[i * 3] = randomSigned(random, 1);
            arr[i * 3 + 1] = randomSigned(random, 1) + 5;
            arr[i * 3 + 2] = randomSigned(random, 1) - 10;
        }
        return arr;
    }, [particleCount]);

    const velocitiesRef = useRef<Float32Array>(createExplosionVelocities(particleCount));

    const pointsRef = useRef<THREE.Points>(null!);

    useFrame((_, delta) => {
        if (!isAccepted || !pointsRef.current) return;

        const positionsArray = pointsRef.current.geometry.attributes.position.array as Float32Array;
        const velocities = velocitiesRef.current;
        
        // Explode outward
        for (let i = 0; i < particleCount; i++) {
            positionsArray[i * 3] += velocities[i * 3] * delta;
            positionsArray[i * 3 + 1] += velocities[i * 3 + 1] * delta;
            positionsArray[i * 3 + 2] += velocities[i * 3 + 2] * delta;
            
            // Slow down over time (drag)
            velocities[i * 3] *= 0.95;
            velocities[i * 3 + 1] *= 0.95;
            velocities[i * 3 + 2] *= 0.95;
        }
        
        pointsRef.current.geometry.attributes.position.needsUpdate = true;
    });

    return (
        <points ref={pointsRef}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    args={[positions, 3]}
                />
            </bufferGeometry>
            <pointsMaterial
                size={0.1}
                color="#00ff88"
                transparent
                opacity={isAccepted ? 1 : 0}
                blending={THREE.AdditiveBlending}
                depthWrite={false}
            />
        </points>
    );
}

// Camera controller that looks up the monolith as user scrolls
function CameraController({ scrollDepth }: { scrollDepth: number }) {
    useFrame((state) => {
        // Safe exponential interpolation
        const delta = Math.min(state.clock.getDelta(), 0.1);
        const alpha = 1 - Math.exp(-3.0 * delta);

        // Move camera up and slightly back as user scrolls
        const targetY = scrollDepth * 15; // Move up 15 units
        const targetZ = 10 + scrollDepth * 5; // Move back slightly

        state.camera.position.lerp(new THREE.Vector3(0, targetY, targetZ), alpha);
        
        // Look slightly upward as we scroll to emphasize scale
        state.camera.lookAt(0, targetY + (scrollDepth * 5), -10);
    });
    
    return null;
}

export default function TermsMonolith3D({ 
    scrollDepth, 
    isAccepted 
}: { 
    scrollDepth: number;
    isAccepted: boolean;
}) {
    const containerRef = useRef<HTMLDivElement>(null);
    // Dynamic lighting based on acceptance
    const primaryColor = isAccepted ? '#00ff88' : '#00ffff';
    const secondaryColor = isAccepted ? '#00cc66' : '#ff0055';

    return (
        <div ref={containerRef} className="h-full w-full">
            <Canvas
                eventSource={containerRef}
                camera={{ position: [0, 0, 10], fov: 60 }}
                gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
                dpr={[1, 1.5]}
            >
                <fog attach="fog" args={['#000000', 10, 40]} />
                <ambientLight intensity={0.1} />
                <directionalLight position={[10, 20, 10]} intensity={1} color={primaryColor} />
                <pointLight position={[0, -10, 0]} intensity={5} color={secondaryColor} distance={30} />
                
                <MonolithStructure isAccepted={isAccepted} />
                <DataRings isAccepted={isAccepted} />
                <AcceptanceExplosion isAccepted={isAccepted} />
                
                <CameraController scrollDepth={scrollDepth} />

                <SafeEffectComposer enableNormalPass={false} multisampling={0}>
                    <Bloom 
                        luminanceThreshold={isAccepted ? 0.3 : 0.5} 
                        mipmapBlur 
                        intensity={isAccepted ? 2.5 : 1.5} 
                    />
                    <ChromaticAberration 
                        offset={new THREE.Vector2(0.003, 0.003)}
                    />
                    <Noise opacity={0.03} />
                </SafeEffectComposer>
                <Preload all />
            </Canvas>
        </div>
    );
}
