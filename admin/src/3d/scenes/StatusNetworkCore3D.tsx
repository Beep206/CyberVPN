'use client';

import { useRef, useMemo, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Canvas } from '@react-three/fiber';
import { Float, Stars, Environment } from '@react-three/drei';
import * as THREE from 'three';
import { Bloom, ChromaticAberration, Noise, Glitch } from '@react-three/postprocessing';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';
import { createDeterministicRandom, randomInRange } from '@/3d/lib/seeded-random';
import { useCanvasHost } from '@/shared/hooks/use-canvas-host';

// Configuration
const CHROMATIC_ABERRATION_OFFSET = new THREE.Vector2(0.002, 0.002);
const GRID_SIZE = 40;
const GRID_DIVISIONS = 40;

// Inner component for the pulsing hexagonal/grid floor
function DigitalGrid({ status }: { status: 'nominal' | 'warning' | 'outage' }) {
    const gridRef = useRef<THREE.GridHelper>(null!);

    const color = useMemo(() => {
        if (status === 'outage') return new THREE.Color('#ff0000');
        if (status === 'warning') return new THREE.Color('#ffb800');
        return new THREE.Color('#00ffff'); // nominal cyber-cyan
    }, [status]);

    useFrame((state) => {
        if (gridRef.current) {
            // Slight breathing effect on the grid
            const scale = 1.0 + Math.sin(state.clock.elapsedTime * 0.5) * 0.02;
            gridRef.current.scale.set(scale, scale, scale);
        }
    });

    return (
        <group position={[0, -2, 0]}>
            <gridHelper 
                ref={gridRef}
                args={[GRID_SIZE, GRID_DIVISIONS, color, '#111111']} 
            />
            {/* Ground reflection plane */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
                <planeGeometry args={[GRID_SIZE, GRID_SIZE]} />
                <meshStandardMaterial 
                    color="#050505" 
                    roughness={0.1} 
                    metalness={0.9} 
                    transparent 
                    opacity={0.8}
                />
            </mesh>
        </group>
    );
}

// The floating central reactor core that represents global network state
function NetworkReactorCore({ status }: { status: 'nominal' | 'warning' | 'outage' }) {
    const coreRef = useRef<THREE.Mesh>(null!);
    const wireframeRef = useRef<THREE.Mesh>(null!);
    
    const coreColor = useMemo(() => {
        if (status === 'outage') return new THREE.Color('#ff0000');
        if (status === 'warning') return new THREE.Color('#ffb800');
        return new THREE.Color('#00ff88'); // nominal matrix green
    }, [status]);

    useFrame((state, delta) => {
        if (coreRef.current && wireframeRef.current) {
            // Speed depends on status (outage = erratic/fast, nominal = slow/steady)
            const speed = status === 'outage' ? 3 : status === 'warning' ? 1.5 : 0.5;
            
            coreRef.current.rotation.y += delta * speed;
            coreRef.current.rotation.z += delta * (speed * 0.5);
            
            wireframeRef.current.rotation.y -= delta * (speed * 1.2);
            wireframeRef.current.rotation.x += delta * (speed * 0.8);

            // Pulsing emissive intensity
            const pulse = status === 'outage' 
                ? 1.5 + Math.sin(state.clock.elapsedTime * 10) * 1.5 // Frantic pulsing
                : 0.8 + Math.sin(state.clock.elapsedTime * 2) * 0.4;  // Calm breathing
            
            (coreRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity = pulse;
            (wireframeRef.current.material as THREE.MeshBasicMaterial).opacity = pulse * 0.5;
        }
    });

    return (
        <Float speed={2} rotationIntensity={0.5} floatIntensity={1.5} position={[0, 1, 0]}>
            <pointLight distance={15} intensity={status === 'outage' ? 3 : 1.5} color={coreColor} />
            
            {/* Inner Glowing Core */}
            <mesh ref={coreRef}>
                <octahedronGeometry args={[1.5, 2]} />
                <meshStandardMaterial 
                    color="#000000" 
                    emissive={coreColor} 
                    emissiveIntensity={1}
                    roughness={0.2} 
                    metalness={0.8} 
                    wireframe={false}
                />
            </mesh>

            {/* Outer Encapsulating Wireframe */}
            <mesh ref={wireframeRef}>
                <icosahedronGeometry args={[2, 1]} />
                <meshBasicMaterial 
                    color={coreColor} 
                    wireframe 
                    transparent 
                    opacity={0.3} 
                />
            </mesh>
            
            {/* Particle ring representing data throughput */}
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[3, 0.02, 16, 100]} />
                <meshBasicMaterial color={coreColor} transparent opacity={0.5} />
            </mesh>
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={[1.2, 1.2, 1.2]}>
                <torusGeometry args={[3.2, 0.01, 16, 100]} />
                <meshBasicMaterial color={coreColor} transparent opacity={0.2} />
            </mesh>
        </Float>
    );
}

// Data Streams shooting outward across the grid
function DataStreamInstanced({ count = 100, status }: { count?: number, status: 'nominal' | 'warning' | 'outage' }) {
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    
    const streamColor = useMemo(() => {
        if (status === 'outage') return new THREE.Color('#ff0055');
        if (status === 'warning') return new THREE.Color('#ffcc00');
        return new THREE.Color('#00ffff');
    }, [status]);

    const dummy = useMemo(() => new THREE.Object3D(), []);
    
    // Store attributes per instance: position, velocity, angle
    const particles = useMemo(() => {
        const random = createDeterministicRandom(count * 101);
        return new Array(count).fill(0).map(() => {
            const angle = randomInRange(random, 0, Math.PI * 2);
            const radius = randomInRange(random, 2, 22);
            const speed = randomInRange(random, 5, 15);
            return {
                angle,
                radius,
                speed,
                y: randomInRange(random, -1.9, -1.4)
            };
        });
    }, [count]);

    useFrame((state, delta) => {
        if (!meshRef.current) return;
        
        particles.forEach((particle, i) => {
            // Move particles outward
            particle.radius += particle.speed * delta;
            
            // Loop back to center
            if (particle.radius > 25) {
                particle.radius = 2; // Reset near core
            }
            
            dummy.position.x = Math.cos(particle.angle) * particle.radius;
            dummy.position.y = particle.y;
            dummy.position.z = Math.sin(particle.angle) * particle.radius;
            
            // Orient along velocity vector
            dummy.lookAt(dummy.position.clone().add(new THREE.Vector3(Math.cos(particle.angle), 0, Math.sin(particle.angle))));
            
            // Stretch based on speed (cyberpunk light trace)
            dummy.scale.set(0.05, 0.05, status === 'outage' ? 0.3 : 1.0);
            
            dummy.updateMatrix();
            meshRef.current.setMatrixAt(i, dummy.matrix);
            meshRef.current.setColorAt(i, streamColor);
        });
        
        meshRef.current.instanceMatrix.needsUpdate = true;
        if (meshRef.current.instanceColor) {
            meshRef.current.instanceColor.needsUpdate = true;
        }
    });

    return (
        <instancedMesh ref={meshRef} args={[new THREE.BoxGeometry(1, 1, 1), undefined, count]}>
            <meshBasicMaterial toneMapped={false} />
        </instancedMesh>
    );
}

// Camera parallax rig based on mouse
function CameraRig({ children }: { children: React.ReactNode }) {
    const groupRef = useRef<THREE.Group>(null!);
    
    useFrame((state) => {
        // Subtle drift
        const t = state.clock.getElapsedTime();
        const mouseX = state.pointer.x;
        const mouseY = state.pointer.y;
        
        groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, mouseX * 0.2 + Math.sin(t * 0.1) * 0.05, 0.05);
        groupRef.current.rotation.x = THREE.MathUtils.lerp(groupRef.current.rotation.x, -mouseY * 0.1 + Math.cos(t * 0.1) * 0.05, 0.05);
    });

    return <group ref={groupRef}>{children}</group>;
}

export function NetworkCore3D() {
    // Determine global status based on app state (mocked as nominal for now, can be updated via props)
    const { host, setHostRef } = useCanvasHost<HTMLDivElement>();
    const [globalStatus] = useState<'nominal' | 'warning' | 'outage'>('nominal');
    const cameraConfig = { position: [0, 4, 12] as [number, number, number], fov: 45 };
    const glConfig = {
        antialias: false,
        alpha: true,
        powerPreference: 'high-performance' as const,
    };

    return (
        <div ref={setHostRef} className="h-full w-full">
            {host ? (
                <Canvas
                    eventSource={host}
                    camera={cameraConfig}
                    gl={glConfig}
                >
                    <fog attach="fog" args={['#000000', 5, 30]} />
                    <Environment preset="city" />
                    
                    <ambientLight intensity={0.2} />

                    <CameraRig>
                        <DigitalGrid status={globalStatus} />
                        <NetworkReactorCore status={globalStatus} />
                        <DataStreamInstanced count={200} status={globalStatus} />
                        
                        {/* Background stars representing remote nodes */}
                        <Stars radius={50} depth={50} count={3000} factor={4} saturation={1} fade speed={globalStatus === 'outage' ? 3 : 1} />
                    </CameraRig>

                    <SafeEffectComposer enableNormalPass={false}>
                        <Bloom luminanceThreshold={0.5} mipmapBlur intensity={globalStatus === 'outage' ? 3.0 : 1.5} />
                        <Glitch active={globalStatus === 'outage'} delay={new THREE.Vector2(0.5, 2.0)} duration={new THREE.Vector2(0.1, 0.3)} />
                        <Noise opacity={0.03} />
                        <ChromaticAberration offset={CHROMATIC_ABERRATION_OFFSET} />
                    </SafeEffectComposer>
                </Canvas>
            ) : null}
        </div>
    );
}
