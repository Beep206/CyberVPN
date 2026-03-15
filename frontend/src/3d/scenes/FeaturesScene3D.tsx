'use client';

import { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom, ChromaticAberration, Noise, Glitch } from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import * as THREE from 'three';
import { FeatureId } from '@/widgets/features/features-dashboard';
import { PerformanceMonitor } from '@react-three/drei';
import { useInView } from 'motion/react';

const COLORS: Record<FeatureId, string> = {
    quantum: '#00ffff',     // Cyan
    multihop: '#00ff88',    // Matrix Green
    obfuscation: '#ff00ff', // Neon Purple
    killswitch: '#ff3300'   // Warning Red
};

// --- INSTANCED ENGINE CORE Nodes ---
function EngineCoreNodes({ activeFeature }: { activeFeature: FeatureId }) {
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    const materialRef = useRef<THREE.MeshPhysicalMaterial>(null!);
    const dummy = useMemo(() => new THREE.Object3D(), []);
    
    // Core parameters
    const count = 300;
    
    // Generate initial ring / spherical positions
    const particles = useMemo(() => {
        return new Array(count).fill(0).map((_, i) => {
            // Distribute on a sphere/cylinder hybrid
            const phi = Math.acos(-1 + (2 * i) / count);
            const theta = Math.sqrt(count * Math.PI) * phi;
            
            const r = 2.5 + Math.random() * 0.5;
            
            return {
                baseX: r * Math.cos(theta) * Math.sin(phi),
                baseY: r * Math.sin(theta) * Math.sin(phi),
                baseZ: r * Math.cos(phi),
                speed: Math.random() * 2 + 0.5,
                phase: Math.random() * Math.PI * 2
            };
        });
    }, [count]);

    // Target color interpolation based on active feature
    const targetColor = useMemo(() => new THREE.Color(COLORS[activeFeature]), [activeFeature]);

    useFrame((state, delta) => {
        if (!meshRef.current || !materialRef.current) return;
        
        const t = state.clock.elapsedTime;
        
        // Behavior modifiers based on feature
        const isQuantum = activeFeature === 'quantum';
        const isMultihop = activeFeature === 'multihop';
        const isObfuscation = activeFeature === 'obfuscation';
        const isKillswitch = activeFeature === 'killswitch';

        particles.forEach((p, i) => {
            // Default position
            let x = p.baseX;
            let y = p.baseY;
            let z = p.baseZ;

            // Apply transformations based on active feature
            if (isQuantum) {
                // Energetic shivering
                x += Math.sin(t * 10 + p.phase) * 0.05;
                y += Math.cos(t * 15 + p.phase) * 0.05;
                dummy.scale.set(1, 1, 1);
            } else if (isMultihop) {
                // Expanding rings / cascading outward
                const expand = Math.sin(t * p.speed + p.phase) * 1.5;
                x += x * expand * 0.2;
                y += y * expand * 0.2;
                z += z * expand * 0.2;
                dummy.scale.set(0.5, 2, 0.5); // Elongated nodes
            } else if (isObfuscation) {
                // Noise / scrambled positions
                x += Math.sin(t * 5 + p.phase * 3) * 0.3;
                z += Math.cos(t * 5 + p.phase * 3) * 0.3;
                dummy.scale.set(Math.sin(t*2+i)*0.5 + 0.5, Math.sin(t*2+i)*0.5 + 0.5, Math.sin(t*2+i)*0.5 + 0.5); // Blinking/scaling
            } else if (isKillswitch) {
                // Contracting tightly to the core
                x *= 0.6;
                y *= 0.6;
                z *= 0.6;
                // Hard angular rotation
                dummy.rotation.x = t * 2;
                dummy.rotation.y = t * 2;
                dummy.scale.set(1.5, 1.5, 1.5);
            }

            dummy.position.set(x, y, z);
            
            // Look away from center
            if (!isKillswitch) {
                dummy.lookAt(0,0,0);
            }

            dummy.updateMatrix();
            meshRef.current.setMatrixAt(i, dummy.matrix);
        });
        
        meshRef.current.instanceMatrix.needsUpdate = true;
        
        // Smoothly interpolate material color
        materialRef.current.emissive.lerp(targetColor, delta * 3);
        materialRef.current.color.lerp(targetColor, delta * 3);
        
        // Global Core Rotation
        meshRef.current.rotation.y += delta * (isKillswitch ? 0 : 0.2);
        meshRef.current.rotation.x = Math.sin(t * 0.5) * 0.2;
    });

    return (
        <instancedMesh ref={meshRef} args={[new THREE.BoxGeometry(0.1, 0.1, 0.3), undefined, count]}>
            <meshPhysicalMaterial 
                ref={materialRef}
                color={COLORS.quantum}
                emissive={COLORS.quantum}
                emissiveIntensity={2}
                roughness={0.2}
                metalness={0.8}
            />
        </instancedMesh>
    );
}

// --- CENTRAL SHIELD (Reacts to Killswitch) ---
function CentralShield({ activeFeature }: { activeFeature: FeatureId }) {
    const shieldRef = useRef<THREE.Mesh>(null!);
    const matRef = useRef<THREE.MeshPhysicalMaterial>(null!);
    
    useFrame((state, delta) => {
        if (!shieldRef.current || !matRef.current) return;
        const isKillswitch = activeFeature === 'killswitch';
        
        // Smoothly scale shield up when killswitch is active, down otherwise
        const targetScale = isKillswitch ? 2.8 : 1.8;
        shieldRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), delta * 4);
        
        // Opacity and color sweep
        const targetOpacity = isKillswitch ? 0.6 : 0.1;
        matRef.current.opacity = THREE.MathUtils.lerp(matRef.current.opacity, targetOpacity, delta * 4);
        
        const targetColor = new THREE.Color(COLORS[activeFeature]);
        matRef.current.color.lerp(targetColor, delta * 3);
        matRef.current.emissive.lerp(targetColor, delta * 3);
    });

    return (
        <mesh ref={shieldRef}>
            <icosahedronGeometry args={[1, 2]} />
            <meshPhysicalMaterial 
                ref={matRef}
                color={COLORS.quantum}
                emissive={COLORS.quantum}
                emissiveIntensity={0.5}
                transparent
                opacity={0.1}
                wireframe={activeFeature !== 'killswitch'}
                roughness={0.1}
                transmission={0.9}
                thickness={0.5}
            />
        </mesh>
    );
}

// --- MAIN CANVAS BUILDER ---
export function FeaturesScene3D({ activeFeature }: { activeFeature: FeatureId }) {
    const containerRef = useRef<HTMLDivElement>(null!);
    const isInView = useInView(containerRef, { margin: "200px" });
    const [dpr, setDpr] = useState(1);
    
    // Trigger a light glitch effect on feature change
    const [glitchActive, setGlitchActive] = useState(false);
    
    // Watch for feature changes to trigger glitch
    const prevFeature = useRef(activeFeature);
    if (prevFeature.current !== activeFeature) {
        setGlitchActive(true);
        setTimeout(() => setGlitchActive(false), 300); // 300ms glitch duration
        prevFeature.current = activeFeature;
    }

    return (
        <div ref={containerRef} className="absolute inset-0 w-full h-full">
            <Canvas 
                frameloop={isInView ? 'always' : 'never'}
                camera={{ position: [0, 0, 8], fov: 45 }}
                gl={{ antialias: false, powerPreference: "high-performance", alpha: true }}
                dpr={dpr}
            >
                <PerformanceMonitor onDecline={() => setDpr(0.75)} onIncline={() => setDpr(1.5)} />

                <ambientLight intensity={0.5} />
                <pointLight position={[5, 5, 5]} intensity={2} />
                
                <group position={[0, 0, 0]}>
                    <CentralShield activeFeature={activeFeature} />
                    <EngineCoreNodes activeFeature={activeFeature} />
                </group>

                <EffectComposer multisampling={0}>
                    <Bloom 
                        luminanceThreshold={0.2} 
                        mipmapBlur 
                        intensity={activeFeature === 'killswitch' ? 2.5 : 1.2} 
                    />
                    <Glitch 
                        active={glitchActive} 
                        delay={new THREE.Vector2(0, 0)} 
                        duration={new THREE.Vector2(0.1, 0.3)} 
                        ratio={0.5}
                    />
                    <ChromaticAberration
                        blendFunction={BlendFunction.NORMAL}
                        offset={new THREE.Vector2(0.003, 0.003)}
                    />
                    <Noise opacity={activeFeature === 'obfuscation' ? 0.08 : 0.03} />
                </EffectComposer>
            </Canvas>
        </div>
    );
}
