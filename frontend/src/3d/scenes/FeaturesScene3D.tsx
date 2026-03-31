'use client';

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Bloom, ChromaticAberration, Noise, Glitch } from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import { ScenePerformanceMetrics } from '@/3d/components/scene-performance-metrics';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';
import {
    MARKETING_SCENE_CANVAS_PERFORMANCE,
    MARKETING_SCENE_GL,
    useAdaptiveSceneDpr,
} from '@/3d/lib/scene-performance';
import * as THREE from 'three';
import { FeatureId } from '@/widgets/features/features-dashboard';
import { PerformanceMonitor } from '@react-three/drei';
import { useInView } from 'motion/react';
import { createDeterministicRandom, randomInRange } from '@/3d/lib/seeded-random';

const COLORS: Record<FeatureId, string> = {
    quantum: '#00ffff',     // Cyan
    multihop: '#00ff88',    // Matrix Green
    obfuscation: '#ff00ff', // Neon Purple
    killswitch: '#ff3300'   // Warning Red
};

const FEATURES_CHROMATIC_ABERRATION_OFFSET = new THREE.Vector2(0.003, 0.003);
const ENGINE_CORE_GEOMETRY = new THREE.BoxGeometry(0.1, 0.1, 0.3);
const SHIELD_IDLE_SCALE = new THREE.Vector3(1.8, 1.8, 1.8);
const SHIELD_ACTIVE_SCALE = new THREE.Vector3(2.8, 2.8, 2.8);

// --- INSTANCED ENGINE CORE Nodes ---
function EngineCoreNodes({ activeFeature }: { activeFeature: FeatureId }) {
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    const materialRef = useRef<THREE.MeshPhysicalMaterial>(null!);
    const dummy = useMemo(() => new THREE.Object3D(), []);
    const geometry = useMemo(() => ENGINE_CORE_GEOMETRY, []);
    
    // Core parameters
    const count = 300;
    
    // Generate initial ring / spherical positions
    const particles = useMemo(() => {
        const random = createDeterministicRandom(count * 43);
        return new Array(count).fill(0).map((_, i) => {
            // Distribute on a sphere/cylinder hybrid
            const phi = Math.acos(-1 + (2 * i) / count);
            const theta = Math.sqrt(count * Math.PI) * phi;
            
            const r = randomInRange(random, 2.5, 3.0);
            
            return {
                baseX: r * Math.cos(theta) * Math.sin(phi),
                baseY: r * Math.sin(theta) * Math.sin(phi),
                baseZ: r * Math.cos(phi),
                speed: randomInRange(random, 0.5, 2.5),
                phase: randomInRange(random, 0, Math.PI * 2)
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
            dummy.rotation.set(0, 0, 0);
            dummy.scale.set(1, 1, 1);

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
                const scrambleScale = Math.sin(t * 2 + i) * 0.5 + 0.5;
                dummy.scale.setScalar(scrambleScale);
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
        <instancedMesh ref={meshRef} args={[geometry, undefined, count]}>
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
    const targetColor = useMemo(() => new THREE.Color(), []);
    
    useFrame((state, delta) => {
        if (!shieldRef.current || !matRef.current) return;
        const isKillswitch = activeFeature === 'killswitch';
        
        // Smoothly scale shield up when killswitch is active, down otherwise
        shieldRef.current.scale.lerp(isKillswitch ? SHIELD_ACTIVE_SCALE : SHIELD_IDLE_SCALE, delta * 4);
        
        // Opacity and color sweep
        const targetOpacity = isKillswitch ? 0.6 : 0.1;
        matRef.current.opacity = THREE.MathUtils.lerp(matRef.current.opacity, targetOpacity, delta * 4);
        
        targetColor.set(COLORS[activeFeature]);
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
    const { dpr, monitorProps } = useAdaptiveSceneDpr({ initial: 1, min: 0.75, max: 1.5 });
    
    return (
        <div ref={containerRef} className="absolute inset-0 w-full h-full">
            <Canvas 
                eventSource={containerRef}
                frameloop={isInView ? 'always' : 'never'}
                performance={MARKETING_SCENE_CANVAS_PERFORMANCE}
                camera={{ position: [0, 0, 8], fov: 45 }}
                gl={MARKETING_SCENE_GL}
                dpr={dpr}
            >
                <ScenePerformanceMetrics sceneName="features-core" />
                <PerformanceMonitor {...monitorProps} />

                <ambientLight intensity={0.5} />
                <pointLight position={[5, 5, 5]} intensity={2} />
                
                <group position={[0, 0, 0]}>
                    <CentralShield activeFeature={activeFeature} />
                    <EngineCoreNodes activeFeature={activeFeature} />
                </group>

                <SafeEffectComposer enableNormalPass={false} multisampling={0}>
                    <Bloom 
                        luminanceThreshold={0.2} 
                        mipmapBlur 
                        intensity={activeFeature === 'killswitch' ? 2.5 : 1.2} 
                    />
                    <Glitch 
                        active={activeFeature === 'obfuscation' || activeFeature === 'killswitch'} 
                        delay={new THREE.Vector2(0, 0)} 
                        duration={new THREE.Vector2(0.1, 0.3)} 
                        ratio={0.5}
                    />
                    <ChromaticAberration
                        blendFunction={BlendFunction.NORMAL}
                        offset={FEATURES_CHROMATIC_ABERRATION_OFFSET}
                    />
                    <Noise opacity={activeFeature === 'obfuscation' ? 0.08 : 0.03} />
                </SafeEffectComposer>
            </Canvas>
        </div>
    );
}
