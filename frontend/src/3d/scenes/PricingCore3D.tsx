'use client';

import { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom, Noise, ChromaticAberration } from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import * as THREE from 'three';
import { TierLevel } from '@/widgets/pricing/pricing-dashboard';
import { Vector2 } from 'three';
import { PerformanceMonitor } from '@react-three/drei';
import { useInView } from 'motion/react';

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
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    const materialRef = useRef<THREE.MeshBasicMaterial>(null!);
    const dummy = useMemo(() => new THREE.Object3D(), []);
    
    // Significantly reduced point count but better aesthetics via scaling
    const count = 150;
    const particles = useMemo(() => {
        return new Array(count).fill(0).map(() => ({
            x: (Math.random() - 0.5) * 15,
            y: (Math.random() - 0.5) * 20 - 10,
            z: (Math.random() - 0.5) * 15,
            speed: Math.random() * 0.5 + 0.1,
            scaleY: Math.random() * 2 + 0.5
        }));
    }, []);

    useFrame((state, delta) => {
        if (!meshRef.current || !materialRef.current) return;
        
        const targetSpeed = TIER_SPEEDS[hoveredTier] * 3;
        
        particles.forEach((p, i) => {
            p.y += p.speed * targetSpeed * delta;
            
            // Loop particles back to bottom
            if (p.y > 10) p.y = -10;
            
            dummy.position.set(p.x, p.y, p.z);
            dummy.scale.set(1, p.scaleY, 1); // Elongate to look like stream rays
            dummy.updateMatrix();
            meshRef.current.setMatrixAt(i, dummy.matrix);
        });
        meshRef.current.instanceMatrix.needsUpdate = true;
        
        // Interpolate particle color globally
        materialRef.current.color.lerp(TIER_COLORS[hoveredTier], delta * 3);
    });

    return (
        <instancedMesh ref={meshRef} args={[new THREE.BoxGeometry(0.04, 1.0, 0.04), undefined, count]}>
            <meshBasicMaterial
                ref={materialRef}
                color={TIER_COLORS.none}
                transparent
                opacity={0.6}
                blending={THREE.AdditiveBlending}
                depthWrite={false}
            />
        </instancedMesh>
    );
}

// --- MAIN CANVAS COMPONENT ---
export function PricingCore3D({ hoveredTier }: { hoveredTier: TierLevel }) {
    const containerRef = useRef<HTMLDivElement>(null);
    // Pause rendering entirely when the component is off-screen (scrolled past)
    const isInView = useInView(containerRef, { margin: "200px" });
    const [dpr, setDpr] = useState(1); // Manage DPR dynamically

    return (
        <div ref={containerRef} className="absolute inset-0 w-full h-full">
            <Canvas 
                frameloop={isInView ? 'always' : 'never'}
                camera={{ position: [0, 2, 8], fov: 45 }}
                // Optimize GL context: false antialias, false alpha (since background is black), high-perf mode
                gl={{ antialias: false, powerPreference: "high-performance", alpha: false }}
                dpr={dpr}
            >
                {/* Dynamically scale down pixel ratio to preserve FPS on weak devices */}
                <PerformanceMonitor onDecline={() => setDpr(0.75)} onIncline={() => setDpr(1.5)} />

                <color attach="background" args={['#000000']} />
                <fog attach="fog" args={['#000000', 5, 15]} />
                
                <ambientLight intensity={0.5} />
                
                <DataCrystal hoveredTier={hoveredTier} />
                <DataStreams hoveredTier={hoveredTier} />

                {/* Disable MSAA inside the composer for massive performance boost */}
                <EffectComposer multisampling={0}>
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
        </div>
    );
}
