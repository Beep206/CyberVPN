'use client';

import * as THREE from 'three';
import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Bloom, ChromaticAberration } from '@react-three/postprocessing';
import { PrivacySectionId } from '@/widgets/privacy/privacy-dashboard';
import { Float, Points, PointMaterial } from '@react-three/drei';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';

// Generate random points for the data cloud
function generateDataCloud(count: number, radius: number) {
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos((Math.random() * 2) - 1);
        const r = radius + (Math.random() - 0.5);

        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta); // x
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta); // y
        positions[i * 3 + 2] = r * Math.cos(phi); // z
    }
    return positions;
}

// Inner rotating rings representing the "Vault Core"
function VaultCore({ scrollDepth }: { scrollDepth: number }) {
    const ring1 = useRef<THREE.Mesh>(null!);
    const ring2 = useRef<THREE.Mesh>(null!);
    const ring3 = useRef<THREE.Mesh>(null!);
    
    // Dynamic particles
    const particleCount = 2000;
    const particlePositions = useMemo(() => generateDataCloud(particleCount, 3), []);

    useFrame((state, delta) => {
        // Vault rings rotation
        if (ring1.current) ring1.current.rotation.y += delta * 0.2;
        if (ring2.current) {
            ring2.current.rotation.x += delta * 0.15;
            ring2.current.rotation.z += delta * 0.1;
        }
        if (ring3.current) {
            ring3.current.rotation.y -= delta * 0.3;
            ring3.current.rotation.x -= delta * 0.05;
        }

        // Parallax effect based on scroll depth
        // As user scrolls down, the vault expands and moves closer
        const expandedScale = 1 + (scrollDepth * 0.5);
        if (ring1.current) ring1.current.scale.setScalar(THREE.MathUtils.lerp(ring1.current.scale.x, expandedScale, 0.1));
        if (ring2.current) ring2.current.scale.setScalar(THREE.MathUtils.lerp(ring2.current.scale.x, expandedScale * 1.2, 0.1));
        if (ring3.current) ring3.current.scale.setScalar(THREE.MathUtils.lerp(ring3.current.scale.x, expandedScale * 1.5, 0.1));
    });

    return (
        <group>
            <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
                
                {/* Core Sphere (The protected data) */}
                <mesh>
                    <sphereGeometry args={[1, 32, 32]} />
                    <meshStandardMaterial 
                        color="#00ffff" 
                        emissive="#00ffff" 
                        emissiveIntensity={2} 
                        wireframe 
                        transparent 
                        opacity={0.3} 
                    />
                </mesh>

                {/* Cryptographic Ring 1 */}
                <mesh ref={ring1}>
                    <torusGeometry args={[2, 0.05, 16, 100]} />
                    <meshStandardMaterial color="#00ff88" emissive="#00ff88" emissiveIntensity={1} />
                </mesh>

                {/* Cryptographic Ring 2 */}
                <mesh ref={ring2}>
                    <torusGeometry args={[2.8, 0.02, 16, 100]} />
                    <meshStandardMaterial color="#ff00ff" emissive="#ff00ff" emissiveIntensity={0.5} wireframe />
                </mesh>

                {/* Cryptographic Ring 3 (Dashed/Dotted illusion via TorusKnot) */}
                <mesh ref={ring3}>
                    <torusKnotGeometry args={[3.5, 0.01, 128, 8, 2, 3]} />
                    <meshStandardMaterial color="#00ffff" emissive="#00ffff" emissiveIntensity={1.5} />
                </mesh>

                {/* Protective Particle Cloud */}
                <Points positions={particlePositions}>
                    <PointMaterial
                        transparent
                        color="#ffffff"
                        size={0.05}
                        sizeAttenuation={true}
                        depthWrite={false}
                        blending={THREE.AdditiveBlending}
                    />
                </Points>

            </Float>
        </group>
    );
}

// Camera controller that reacts to scroll depth
function CameraController({ scrollDepth }: { scrollDepth: number }) {
    useFrame((state) => {
        // Safe exponential lerping
        const delta = Math.min(state.clock.getDelta(), 0.1);
        const alpha = 1 - Math.exp(-3.0 * delta);

        // Move camera closer as user scrolls down
        const targetZ = 8 - (scrollDepth * 3);
        const targetY = scrollDepth * 2;
        
        state.camera.position.lerp(new THREE.Vector3(0, targetY, targetZ), alpha);
        state.camera.lookAt(0, 0, 0);
    });
    
    return null;
}

export default function PrivacyVault3D({ 
    activeSection, 
    scrollDepth 
}: { 
    activeSection: PrivacySectionId;
    scrollDepth: number;
}) {
    const containerRef = useRef<HTMLDivElement>(null);

    // Determine primary color of the 3D scene based on the active topic
    const getVaultColor = () => {
        switch (activeSection) {
            case 'introduction': return '#00ffff'; // Neon Cyan
            case 'dataCollection': return '#ff0055'; // Warning Red/Pink
            case 'noLogs': return '#00ff88'; // Matrix Green (Safe)
            case 'encryption': return '#ff00ff'; // Cryptography Purple
            case 'thirdParties': return '#00aaeb'; // Blue
            default: return '#00ffff';
        }
    };

    return (
        <div ref={containerRef} className="w-full h-full absolute inset-0 z-0 pointer-events-none opacity-50">
            <Canvas
                eventSource={containerRef}
                camera={{ position: [0, 0, 8], fov: 45 }}
                gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
            >
                <ambientLight intensity={0.2} />
                <pointLight position={[0, 0, 0]} intensity={2} color={getVaultColor()} />
                
                <VaultCore scrollDepth={scrollDepth} />
                <CameraController scrollDepth={scrollDepth} />

                <SafeEffectComposer enableNormalPass={false} multisampling={0}>
                    <Bloom 
                        luminanceThreshold={0.2} 
                        mipmapBlur 
                        intensity={1.5} 
                        radius={0.8} 
                    />
                    <ChromaticAberration 
                        offset={new THREE.Vector2(0.002, 0.002)}
                    />
                </SafeEffectComposer>
            </Canvas>
        </div>
    );
}
