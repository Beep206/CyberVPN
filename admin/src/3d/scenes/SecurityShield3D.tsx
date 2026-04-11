'use client';

import * as THREE from 'three';
import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Bloom, ChromaticAberration, Noise } from '@react-three/postprocessing';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';
import { type SecurityLayerId } from '@/widgets/security/security-dashboard';
import { createDeterministicRandom, randomInRange } from '@/3d/lib/seeded-random';
import { useCanvasHost } from '@/shared/hooks/use-canvas-host';

// The Aegis Firewall Shield (Interactive Icosahedron turning into a sphere)
function AegisShield({ activeLayer }: { activeLayer: SecurityLayerId }) {
    const shieldRef = useRef<THREE.Mesh>(null!);
    const materialRef = useRef<THREE.MeshStandardMaterial>(null!);

    useFrame((state, delta) => {
        if (!shieldRef.current || !materialRef.current) return;

        // Base rotation
        shieldRef.current.rotation.y += delta * 0.1;
        shieldRef.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.2) * 0.05;

        // Determine target color and state based on layer selected
        let targetColor = new THREE.Color('#00ffff'); // Default Cyan (Client)
        let scaleTarget = 1;

        switch (activeLayer) {
            case 'bareMetal':
                targetColor = new THREE.Color('#88aadd'); // Steely bright metal
                scaleTarget = 0.8;
                break;
            case 'network':
                targetColor = new THREE.Color('#00ff88'); // Matrix Green (Routing)
                scaleTarget = 0.9;
                break;
            case 'crypto':
                targetColor = new THREE.Color('#ff00ff'); // Purple (Encryption Math)
                scaleTarget = 1.1;
                break;
            case 'client':
            default:
                targetColor = new THREE.Color('#00ffff'); // Neon Cyan (App surface)
                scaleTarget = 1;
                break;
        }

        // Smooth transition colors and scale
        materialRef.current.color.lerp(targetColor, delta * 3);
        materialRef.current.emissive.lerp(targetColor, delta * 3);

        // Smooth scale
        const currentScale = shieldRef.current.scale.x;
        const newScale = THREE.MathUtils.lerp(currentScale, scaleTarget, delta * 2);
        shieldRef.current.scale.setScalar(newScale);
    });

    return (
        <group position={[0, -2, -10]}>
            {/* The Core Geometric Shield */}
            <mesh ref={shieldRef}>
                <icosahedronGeometry args={[5, 4]} />
                <meshStandardMaterial 
                    ref={materialRef}
                    color="#00ffff"
                    emissive="#00ffff"
                    emissiveIntensity={0.2}
                    transparent
                    opacity={0.3}
                    roughness={0.1}
                    metalness={0.8}
                    wireframe={true}
                />
            </mesh>

            {/* Inner Core Light */}
            <pointLight position={[0, 0, 0]} intensity={2} color="#ffffff" distance={10} />
        </group>
    );
}

// Threat Particles bombarding the shield
function ThreatBombardment({ activeLayer }: { activeLayer: SecurityLayerId }) {
    const particleCount = 1000;
    
    // Initial particle positions far outside the shield
    const positions = useMemo(() => {
        const random = createDeterministicRandom(particleCount * 83);
        const arr = new Float32Array(particleCount * 3);
        for (let i = 0; i < particleCount; i++) {
            // Random points on a large sphere surface
            const theta = randomInRange(random, 0, Math.PI * 2);
            const phi = Math.acos(randomInRange(random, -1, 1));
            const radius = randomInRange(random, 15, 25);

            arr[i * 3] = radius * Math.sin(phi) * Math.cos(theta); // x
            arr[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta); // y
            arr[i * 3 + 2] = radius * Math.cos(phi); // z
        }
        return arr;
    }, []);

    // Individual particle velocities aiming roughly toward center (0,0,-10)
    const velocities = useMemo(() => {
        const random = createDeterministicRandom(particleCount * 89);
        const arr = new Float32Array(particleCount);
        for (let i = 0; i < particleCount; i++) {
            const speed = randomInRange(random, 2, 7);
            arr[i] = speed;
        }
        return arr;
    }, []);

    const pointsRef = useRef<THREE.Points>(null!);
    const materialRef = useRef<THREE.PointsMaterial>(null!);

    useFrame((state, delta) => {
        if (!pointsRef.current || !materialRef.current) return;

        const posArray = pointsRef.current.geometry.attributes.position.array as Float32Array;
        const shieldRadius = activeLayer === 'crypto' ? 5.5 : 5; // Approximate shield radius

        // Color intensity changes based on layer (Network shows more threats)
        const threatIntensity = activeLayer === 'network' ? 1 : 0.4;
        materialRef.current.opacity = THREE.MathUtils.lerp(materialRef.current.opacity, threatIntensity, delta);

        for (let i = 0; i < particleCount; i++) {
            // Current position relative to shield center (0, -2, -10)
            const cx = posArray[i * 3];
            const cy = posArray[i * 3 + 1] + 2;
            const cz = posArray[i * 3 + 2] + 10;
            
            const distanceToCenter = Math.sqrt(cx*cx + cy*cy + cz*cz);

            // If hit shield, "deflect" by resetting far away
            if (distanceToCenter <= shieldRadius + 0.5) {
                // Reset positions far away
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.acos((Math.random() * 2) - 1);
                const radius = 25;

                posArray[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
                posArray[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta) - 2;
                posArray[i * 3 + 2] = radius * Math.cos(phi) - 10;
            } else {
                // Move towards center
                const speed = velocities[i] * delta;
                
                // Normalize vector to center
                const nx = -cx / distanceToCenter;
                const ny = -cy / distanceToCenter;
                const nz = -cz / distanceToCenter;

                posArray[i * 3] += nx * speed;
                posArray[i * 3 + 1] += ny * speed;
                posArray[i * 3 + 2] += nz * speed;
            }
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
                ref={materialRef}
                size={0.15}
                color="#ff0055" // Threat Red
                transparent
                opacity={0.4}
                blending={THREE.AdditiveBlending}
                depthWrite={false}
            />
        </points>
    );
}

export default function SecurityShield3D({ activeLayer }: { activeLayer: SecurityLayerId }) {
    const { host, setHostRef } = useCanvasHost<HTMLDivElement>();

    return (
        <div ref={setHostRef} className="h-full w-full">
            {host ? (
                <Canvas
                    eventSource={host}
                    camera={{ position: [0, 0, 10], fov: 60 }}
                    gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
                >
                    <fog attach="fog" args={['#000000', 5, 30]} />
                    <ambientLight intensity={0.2} />
                    <directionalLight position={[5, 10, 5]} intensity={1.5} color="#00ffff" />
                    
                    <AegisShield activeLayer={activeLayer} />
                    <ThreatBombardment activeLayer={activeLayer} />

                    <SafeEffectComposer multisampling={0}>
                        <Bloom luminanceThreshold={0.2} mipmapBlur intensity={1.5} />
                        <ChromaticAberration offset={new THREE.Vector2(0.002, 0.002)} />
                        <Noise opacity={0.04} />
                    </SafeEffectComposer>
                </Canvas>
            ) : null}
        </div>
    );
}
