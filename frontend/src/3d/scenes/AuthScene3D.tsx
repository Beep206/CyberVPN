'use client';

import * as THREE from 'three';

const AUTH_CHROMATIC_OFFSET = new THREE.Vector2(0.001, 0.001);
import { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Trail } from '@react-three/drei';
import { ErrorBoundary } from '@/shared/ui/error-boundary';
import { EffectComposer, Bloom, Vignette, ChromaticAberration } from '@react-three/postprocessing';

// ============================================
// FLOATING SHIELD - Central Security Symbol
// ============================================
function FloatingShield() {
    const groupRef = useRef<THREE.Group>(null!);
    const shieldRef = useRef<THREE.Mesh>(null!);
    const [hovered, setHovered] = useState(false);

    // Create hexagonal shield shape
    const shieldShape = useMemo(() => {
        const shape = new THREE.Shape();
        const size = 1.2;
        const sides = 6;

        for (let i = 0; i < sides; i++) {
            const angle = (Math.PI / 3) * i - Math.PI / 2;
            const x = Math.cos(angle) * size;
            const y = Math.sin(angle) * size;
            if (i === 0) shape.moveTo(x, y);
            else shape.lineTo(x, y);
        }
        shape.closePath();
        return shape;
    }, []);

    useFrame((state) => {
        const t = state.clock.getElapsedTime();

        // Gentle rotation
        groupRef.current.rotation.y = Math.sin(t * 0.3) * 0.15;
        groupRef.current.rotation.x = Math.cos(t * 0.2) * 0.1;

        // Pulse scale
        const scale = 1 + Math.sin(t * 2) * 0.02;
        shieldRef.current.scale.setScalar(scale);
    });

    return (
        <Float speed={2} rotationIntensity={0.2} floatIntensity={0.3}>
            <group
                ref={groupRef}
                onPointerEnter={() => setHovered(true)}
                onPointerLeave={() => setHovered(false)}
            >
                {/* Main shield face */}
                <mesh ref={shieldRef}>
                    <shapeGeometry args={[shieldShape]} />
                    <meshBasicMaterial
                        color={hovered ? '#00ffff' : '#00cccc'}
                        transparent
                        opacity={0.15}
                        side={THREE.DoubleSide}
                    />
                </mesh>

                {/* Shield wireframe outline */}
                <lineLoop>
                    <bufferGeometry>
                        <bufferAttribute
                            attach="attributes-position"
                            args={[new Float32Array([
                                ...Array.from({ length: 6 }, (_, i) => {
                                    const angle = (Math.PI / 3) * i - Math.PI / 2;
                                    return [Math.cos(angle) * 1.2, Math.sin(angle) * 1.2, 0];
                                }).flat(),
                                Math.cos(-Math.PI / 2) * 1.2, Math.sin(-Math.PI / 2) * 1.2, 0
                            ]), 3]}
                        />
                    </bufferGeometry>
                    <lineBasicMaterial color="#00ffff" linewidth={2} />
                </lineLoop>

                {/* Inner hexagon */}
                <mesh scale={0.6}>
                    <shapeGeometry args={[shieldShape]} />
                    <meshBasicMaterial
                        color="#00ffff"
                        transparent
                        opacity={0.1}
                        side={THREE.DoubleSide}
                        wireframe
                    />
                </mesh>

                {/* Center lock icon representation */}
                <mesh position={[0, 0, 0.01]}>
                    <circleGeometry args={[0.25, 32]} />
                    <meshBasicMaterial color="#00ffff" transparent opacity={hovered ? 0.4 : 0.2} />
                </mesh>

                {/* Pulsing glow rings */}
                {[1.4, 1.6, 1.8].map((radius, i) => (
                    <PulsingRing key={i} radius={radius} delay={i * 0.5} />
                ))}
            </group>
        </Float>
    );
}

// ============================================
// PULSING RING - Expanding security waves
// ============================================
function PulsingRing({ radius, delay }: { radius: number; delay: number }) {
    const meshRef = useRef<THREE.Mesh>(null!);

    useFrame((state) => {
        const t = state.clock.getElapsedTime();
        const wave = Math.sin(t * 1.5 + delay) * 0.5 + 0.5;
        meshRef.current.scale.setScalar(1 + wave * 0.1);
        (meshRef.current.material as THREE.MeshBasicMaterial).opacity = 0.3 - wave * 0.25;
    });

    return (
        <mesh ref={meshRef} rotation-x={Math.PI / 2}>
            <torusGeometry args={[radius, 0.01, 8, 64]} />
            <meshBasicMaterial
                color="#00ffff"
                transparent
                opacity={0.2}
                blending={THREE.AdditiveBlending}
            />
        </mesh>
    );
}

// ============================================
// SECURITY PARTICLES - Orbiting data points
// ============================================
function SecurityParticles({ count = 500 }: { count?: number }) {
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    const dummy = useMemo(() => new THREE.Object3D(), []);

    const particles = useMemo(() => {
        return Array.from({ length: count }, () => ({
            position: new THREE.Vector3(
                (Math.random() - 0.5) * 12,
                (Math.random() - 0.5) * 8,
                (Math.random() - 0.5) * 6
            ),
            velocity: new THREE.Vector3(
                (Math.random() - 0.5) * 0.01,
                (Math.random() - 0.5) * 0.01,
                (Math.random() - 0.5) * 0.005
            ),
            scale: Math.random() * 0.4 + 0.1,
            phase: Math.random() * Math.PI * 2,
            color: Math.random() > 0.7 ? 1 : 0, // 30% purple, 70% cyan
        }));
    }, [count]);

    useFrame((state) => {
        if (!meshRef.current) return;
        const t = state.clock.getElapsedTime();

        particles.forEach((p, i) => {
            // Orbital motion
            p.position.x += p.velocity.x + Math.sin(t * 0.5 + p.phase) * 0.002;
            p.position.y += p.velocity.y + Math.cos(t * 0.3 + p.phase) * 0.002;
            p.position.z += p.velocity.z;

            // Wrap boundaries
            if (p.position.x > 6) p.position.x = -6;
            if (p.position.x < -6) p.position.x = 6;
            if (p.position.y > 4) p.position.y = -4;
            if (p.position.y < -4) p.position.y = 4;
            if (p.position.z > 3) p.position.z = -3;
            if (p.position.z < -3) p.position.z = 3;

            dummy.position.copy(p.position);
            dummy.scale.setScalar(p.scale * (0.8 + Math.sin(t * 2 + p.phase) * 0.2));
            dummy.updateMatrix();
            meshRef.current.setMatrixAt(i, dummy.matrix);
        });

        meshRef.current.instanceMatrix.needsUpdate = true;
    });

    return (
        <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
            <dodecahedronGeometry args={[0.02, 0]} />
            <meshBasicMaterial
                color="#00ffff"
                transparent
                opacity={0.6}
                blending={THREE.AdditiveBlending}
            />
        </instancedMesh>
    );
}

// ============================================
// DATA STREAMS - Matrix-style falling lines
// ============================================
function DataStreams({ count = 30 }: { count?: number }) {
    const groupRef = useRef<THREE.Group>(null!);

    const streams = useMemo(() => {
        return Array.from({ length: count }, () => ({
            x: (Math.random() - 0.5) * 10,
            z: (Math.random() - 0.5) * 4 - 2,
            speed: Math.random() * 0.03 + 0.02,
            length: Math.random() * 1.5 + 0.5,
            y: Math.random() * 8 - 4,
        }));
    }, [count]);

    useFrame(() => {
        if (!groupRef.current) return;

        groupRef.current.children.forEach((child, i) => {
            const stream = streams[i];
            child.position.y -= stream.speed;

            if (child.position.y < -4) {
                child.position.y = 4;
                child.position.x = (Math.random() - 0.5) * 10;
            }
        });
    });

    return (
        <group ref={groupRef}>
            {streams.map((stream, i) => (
                <mesh key={i} position={[stream.x, stream.y, stream.z]}>
                    <boxGeometry args={[0.01, stream.length, 0.01]} />
                    <meshBasicMaterial
                        color="#00ff88"
                        transparent
                        opacity={0.3}
                        blending={THREE.AdditiveBlending}
                    />
                </mesh>
            ))}
        </group>
    );
}

// ============================================
// GLOWING ORB - Accent element with trail
// ============================================
function GlowingOrb({ color, startPosition }: { color: string; startPosition: [number, number, number] }) {
    const meshRef = useRef<THREE.Mesh>(null!);

    useFrame((state) => {
        const t = state.clock.getElapsedTime();
        meshRef.current.position.x = startPosition[0] + Math.sin(t * 0.4) * 2;
        meshRef.current.position.y = startPosition[1] + Math.cos(t * 0.3) * 1.5;
        meshRef.current.position.z = startPosition[2] + Math.sin(t * 0.5) * 0.5;
    });

    return (
        <Trail width={0.8} length={6} color={color} attenuation={(t) => t * t}>
            <mesh ref={meshRef} position={startPosition}>
                <sphereGeometry args={[0.08, 16, 16]} />
                <meshBasicMaterial color={color} transparent opacity={0.9} />
            </mesh>
        </Trail>
    );
}

// ============================================
// PARALLAX GROUP - Mouse-reactive wrapper
// ============================================
function ParallaxGroup({ children }: { children: React.ReactNode }) {
    const groupRef = useRef<THREE.Group>(null!);

    useFrame((state) => {
        const { pointer } = state;
        groupRef.current.rotation.y = THREE.MathUtils.lerp(
            groupRef.current.rotation.y,
            pointer.x * 0.15,
            0.08
        );
        groupRef.current.rotation.x = THREE.MathUtils.lerp(
            groupRef.current.rotation.x,
            -pointer.y * 0.1,
            0.08
        );
    });

    return <group ref={groupRef}>{children}</group>;
}

// ============================================
// MAIN SCENE CONTENT
// ============================================
function AuthSceneContent() {
    return (
        <>
            <ambientLight intensity={0.3} />
            <pointLight position={[5, 5, 5]} color="#00ffff" intensity={1} />
            <pointLight position={[-5, -3, -5]} color="#9d00ff" intensity={0.5} />

            <ParallaxGroup>
                <FloatingShield />
            </ParallaxGroup>

            <SecurityParticles count={400} />
            <DataStreams count={25} />

            <GlowingOrb color="#00ffff" startPosition={[3, 1.5, -1]} />
            <GlowingOrb color="#9d00ff" startPosition={[-3, -1, -1]} />
            <GlowingOrb color="#00ff88" startPosition={[0, -2, -2]} />

            <EffectComposer enableNormalPass={false} multisampling={0}>
                <Bloom
                    luminanceThreshold={0.4}
                    mipmapBlur
                    intensity={0.6}
                    radius={0.3}
                />
                <Vignette eskil={false} offset={0.1} darkness={0.8} />
                <ChromaticAberration
                    offset={AUTH_CHROMATIC_OFFSET}
                    radialModulation={false}
                    modulationOffset={0}
                />
            </EffectComposer>
        </>
    );
}

// ============================================
// EXPORTED COMPONENT
// ============================================
import { usePathname } from 'next/navigation';

// ============================================
// EXPORTED COMPONENT
// ============================================
export function AuthScene3D() {
    const pathname = usePathname();

    // Use pathname as key to force full R3F/WebGL context recreation on navigation
    // This fixes "Cannot read properties of null" errors when switching languages
    return (
        <div key={pathname} className="absolute inset-0 z-0 pointer-events-none">
            <ErrorBoundary label="Auth 3D Scene">
                <Canvas
                    camera={{ position: [0, 0, 5], fov: 50 }}
                    dpr={[1, 1.5]}
                    gl={{
                        antialias: true,
                        alpha: true,
                        powerPreference: 'high-performance',
                    }}
                    style={{ background: 'transparent' }}
                >
                    <AuthSceneContent />
                </Canvas>
            </ErrorBoundary>
        </div>
    );
}
