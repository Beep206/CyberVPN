'use client';

import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom, Noise, ChromaticAberration } from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import * as THREE from 'three';
import { TierLevel } from '@/widgets/pricing/pricing-dashboard';
import { Vector2 } from 'three';

// --- CONFIGURATION ---
const TIER_COLORS = {
    none: new THREE.Color('#00ffff').multiplyScalar(0.5), // Subtle blue
    basic: new THREE.Color('#00ffff'), // Bright blue
    pro: new THREE.Color('#00ff88'), // Matrix green
    elite: new THREE.Color('#ff00ff'), // Neon purple
};

const TIER_SPEEDS = {
    none: 0.2,
    basic: 0.5,
    pro: 1.5,
    elite: 3.5,
};

// --- DATA CRYSTAL COMPONENT ---
function DataCrystal({ hoveredTier }: { hoveredTier: TierLevel }) {
    const groupRef = useRef<THREE.Group>(null);
    const coreMaterialRef = useRef<THREE.MeshPhysicalMaterial>(null);
    const wireframeMaterialRef = useRef<THREE.MeshBasicMaterial>(null);

    useFrame((state, delta) => {
        if (!groupRef.current || !coreMaterialRef.current || !wireframeMaterialRef.current) return;

        const targetColor = TIER_COLORS[hoveredTier];
        const targetSpeed = TIER_SPEEDS[hoveredTier];
        
        // Smoothly interpolate color
        coreMaterialRef.current.emissive.lerp(targetColor, delta * 3);
        wireframeMaterialRef.current.color.lerp(targetColor, delta * 3);

        // Smoothly adjust rotation based on speed and tier
        groupRef.current.rotation.y += delta * targetSpeed;
        
        // Floating animation
        groupRef.current.position.y = Math.sin(state.clock.elapsedTime * targetSpeed) * 0.2;
        
        // Dynamic scale
        const targetScale = hoveredTier === 'elite' ? 1.2 : (hoveredTier === 'pro' ? 1.1 : 1.0);
        groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), delta * 2);
    });

    return (
        <group ref={groupRef} position={[0, 0, 0]}>
            {/* Inner Core Solid */}
            <mesh>
                <octahedronGeometry args={[2, 0]} />
                <meshPhysicalMaterial 
                    ref={coreMaterialRef}
                    color="#000000"
                    emissive={TIER_COLORS.none}
                    emissiveIntensity={2}
                    transparent
                    opacity={0.8}
                    roughness={0.1}
                    metalness={0.9}
                />
            </mesh>
            
            {/* Outer Wireframe Enclosure */}
            <mesh scale={[1.15, 1.15, 1.15]}>
                <icosahedronGeometry args={[2, 1]} />
                <meshBasicMaterial 
                    ref={wireframeMaterialRef}
                    color={TIER_COLORS.none}
                    wireframe
                    transparent
                    opacity={0.3}
                />
            </mesh>
        </group>
    );
}

// --- PARTICLE DATA STREAMS ---
function DataStreams({ hoveredTier }: { hoveredTier: TierLevel }) {
    const pointsRef = useRef<THREE.Points>(null);
    const materialRef = useRef<THREE.PointsMaterial>(null);
    
    // Generate static particle positions
    const particlesCount = 2000;
    const positions = new Float32Array(particlesCount * 3);
    const speeds = new Float32Array(particlesCount);
    
    for (let i = 0; i < particlesCount; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 20; // x
        positions[i * 3 + 1] = (Math.random() - 0.5) * 20 - 10; // y
        positions[i * 3 + 2] = (Math.random() - 0.5) * 20; // z
        speeds[i] = Math.random() * 0.5 + 0.1;
    }

    useFrame((state, delta) => {
        if (!pointsRef.current || !materialRef.current) return;
        
        const positionsAttr = pointsRef.current.geometry.attributes.position;
        const targetSpeed = TIER_SPEEDS[hoveredTier] * 2;
        
        // Move particles upwards based on tier speed
        for (let i = 0; i < particlesCount; i++) {
            let y = positionsAttr.array[i * 3 + 1] as number;
            y += speeds[i] * targetSpeed * delta;
            
            // Loop particles back to bottom
            if (y > 10) y = -10;
            
            positionsAttr.array[i * 3 + 1] = y;
        }
        positionsAttr.needsUpdate = true;
        
        // Interpolate particle color
        materialRef.current.color.lerp(TIER_COLORS[hoveredTier], delta * 3);
    });

    return (
        <points ref={pointsRef}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={particlesCount}
                    args={[positions, 3]}
                />
            </bufferGeometry>
            <pointsMaterial
                ref={materialRef}
                size={0.05}
                color={TIER_COLORS.none}
                transparent
                opacity={0.6}
                blending={THREE.AdditiveBlending}
            />
        </points>
    );
}

// --- MAIN CANVAS COMPONENT ---
export function PricingCore3D({ hoveredTier }: { hoveredTier: TierLevel }) {
    return (
        <Canvas camera={{ position: [0, 2, 8], fov: 45 }}>
            <color attach="background" args={['#000000']} />
            <fog attach="fog" args={['#000000', 5, 15]} />
            
            <ambientLight intensity={0.5} />
            
            <DataCrystal hoveredTier={hoveredTier} />
            <DataStreams hoveredTier={hoveredTier} />

            <EffectComposer>
                <Bloom 
                    luminanceThreshold={0.2}
                    mipmapBlur
                    intensity={1.5}
                />
                <ChromaticAberration
                    blendFunction={BlendFunction.NORMAL}
                    offset={new Vector2(0.002, 0.002)}
                />
                <Noise opacity={0.035} />
            </EffectComposer>
        </Canvas>
    );
}
