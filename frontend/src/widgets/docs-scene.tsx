'use client';

import { Suspense, useRef, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Text, MeshDistortMaterial, ContactShadows } from '@react-three/drei';
import { Bloom, ToneMapping } from '@react-three/postprocessing';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';
import * as THREE from 'three';

// Mapping sections to distinct visual 3D elements
const sectionConfig = {
    'getting_started': { color: '#00ff88', label: 'INITIALIZATION_SEQUENCE' },
    'routing': { color: '#ff00ff', label: 'NODE_ROUTING_ACTIVE' },
    'security': { color: '#00ffff', label: 'ENCRYPTION_LAYER_LOCKED' },
    'api': { color: '#ffaa00', label: 'NEURAL_LINK_ESTABLISHED' }
};

interface DocsSceneProps {
    activeSection: string;
}

export function DocsScene({ activeSection }: DocsSceneProps) {
    const config = sectionConfig[activeSection as keyof typeof sectionConfig] || sectionConfig.getting_started;
    
    return (
        <div className="w-full h-full relative" style={{ background: 'radial-gradient(circle at center, #111 0%, #000 100%)' }}>
            {/* CRT overlay lines */}
            <div className="absolute inset-0 pointer-events-none z-10 opacity-20 mix-blend-overlay"
                 style={{ backgroundImage: 'linear-gradient(rgba(0, 255, 255, 0) 50%, rgba(0, 255, 255, 0.2) 50%)', backgroundSize: '100% 4px' }} />
            
            <Canvas camera={{ position: [0, 0, 5], fov: 45 }} className="w-full h-full">
                <Suspense fallback={null}>
                    {/* Manual lighting to avoid CDN download hangs from Environment */}
                    <ambientLight intensity={0.5} />
                    <directionalLight position={[10, 10, 5]} intensity={1} color={config.color} />
                    <directionalLight position={[-10, 10, -5]} intensity={0.5} color="#ffffff" />
                    
                    {/* The primary 3D representation that changes based on section */}
                    <BlueprintHologram activeSection={activeSection} color={config.color} />
                    
                    {/* Glowing label below */}
                    <Float speed={2} rotationIntensity={0.1} floatIntensity={0.5} position={[0, -1.8, 0]}>
                        <Text
                            fontSize={0.2}
                            color={config.color}
                            anchorX="center"
                            anchorY="middle"
                        >
                            {config.label}
                        </Text>
                    </Float>

                    <ContactShadows position={[0, -2, 0]} opacity={0.4} scale={10} blur={2.5} far={4} color={config.color} />

                    <SafeEffectComposer multisampling={4}>
                        <Bloom luminanceThreshold={0.5} mipmapBlur intensity={1.5} />
                        <ToneMapping />
                    </SafeEffectComposer>
                </Suspense>
            </Canvas>
        </div>
    );
}

// Internal component handling the 3D meshes and morphs
function BlueprintHologram({ activeSection, color }: { activeSection: string, color: string }) {
    const groupRef = useRef<THREE.Group>(null);
    const targetScale = useRef(1);

    // Simple spring animation on mount/change
    useEffect(() => {
        if (groupRef.current) {
            groupRef.current.scale.set(0, 0, 0);
            targetScale.current = 1;
        }
    }, [activeSection]);

    useFrame((state, delta) => {
        if (groupRef.current) {
            // Lerp scale
            groupRef.current.scale.lerp(new THREE.Vector3(targetScale.current, targetScale.current, targetScale.current), delta * 5);
            // Constant rotation
            groupRef.current.rotation.y += delta * 0.2;
        }
    });

    // Different geometries based on section
    return (
        <group ref={groupRef}>
            <Float speed={4} rotationIntensity={1.5} floatIntensity={2}>
                <mesh>
                    {activeSection === 'getting_started' ? <icosahedronGeometry args={[1, 1]} /> : 
                     activeSection === 'routing' ? <torusKnotGeometry args={[0.7, 0.2, 128, 16]} /> :
                     activeSection === 'security' ? <octahedronGeometry args={[1, 0]} /> :
                     <sphereGeometry args={[1, 32, 32]} />}
                    
                    <MeshDistortMaterial 
                        color={color} 
                        emissive={color}
                        emissiveIntensity={0.5}
                        wireframe={true}
                        distort={activeSection === 'api' ? 0.4 : 0.1}
                        speed={3}
                        transparent
                        opacity={0.8}
                    />
                </mesh>
            </Float>
            {/* Inner solid core */}
            <mesh scale={0.5}>
                {activeSection === 'getting_started' ? <icosahedronGeometry args={[1, 1]} /> : 
                 activeSection === 'routing' ? <torusKnotGeometry args={[0.7, 0.2, 128, 16]} /> :
                 activeSection === 'security' ? <octahedronGeometry args={[1, 0]} /> :
                 <sphereGeometry args={[1, 16, 16]} />}
                
                <meshStandardMaterial 
                    color="#111" 
                    emissive={color}
                    emissiveIntensity={0.2}
                    roughness={0.1}
                    metalness={0.8}
                />
            </mesh>
        </group>
    );
}
