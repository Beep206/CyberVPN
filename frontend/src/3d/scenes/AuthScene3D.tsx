'use client';

import * as THREE from 'three';

const AUTH_CHROMATIC_OFFSET = new THREE.Vector2(0.001, 0.001);
import { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Trail, PerformanceMonitor } from '@react-three/drei';
import { ErrorBoundary } from '@/shared/ui/error-boundary';
import { Bloom, Vignette, ChromaticAberration } from '@react-three/postprocessing';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';

// Create global static geometries to prevent GC stutters during renders
const SHIELD_SHAPE = new THREE.Shape();
const _size = 1.2;
for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    const x = Math.cos(angle) * _size;
    const y = Math.sin(angle) * _size;
    if (i === 0) SHIELD_SHAPE.moveTo(x, y);
    else SHIELD_SHAPE.lineTo(x, y);
}
SHIELD_SHAPE.closePath();

const SHIELD_GEOMETRY = new THREE.ShapeGeometry(SHIELD_SHAPE);
const SHIELD_LINE_POSITIONS = new Float32Array([
    ...Array.from({ length: 6 }, (_, i) => {
        const angle = (Math.PI / 3) * i - Math.PI / 2;
        return [Math.cos(angle) * 1.2, Math.sin(angle) * 1.2, 0];
    }).flat(),
    Math.cos(-Math.PI / 2) * 1.2, Math.sin(-Math.PI / 2) * 1.2, 0
]);
const LOCK_CIRCLE_GEOMETRY = new THREE.CircleGeometry(0.25, 32);
const ORB_GEOMETRY = new THREE.SphereGeometry(0.08, 16, 16);
const DATA_STREAM_GEOMETRY = new THREE.BoxGeometry(0.01, 1, 0.01);
const PARTICLE_GEOMETRY = new THREE.DodecahedronGeometry(0.02, 0);

// ============================================
// FLOATING SHIELD - Central Security Symbol
// ============================================
function FloatingShield() {
    const groupRef = useRef<THREE.Group>(null!);
    const shieldRef = useRef<THREE.Mesh>(null!);
    const [hovered, setHovered] = useState(false);

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
                <mesh ref={shieldRef} geometry={SHIELD_GEOMETRY}>
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
                            args={[SHIELD_LINE_POSITIONS, 3]}
                        />
                    </bufferGeometry>
                    <lineBasicMaterial color="#00ffff" linewidth={2} />
                </lineLoop>

                {/* Inner hexagon */}
                <mesh scale={0.6} geometry={SHIELD_GEOMETRY}>
                    <meshBasicMaterial
                        color="#00ffff"
                        transparent
                        opacity={0.1}
                        side={THREE.DoubleSide}
                        wireframe
                    />
                </mesh>

                {/* Center lock icon representation */}
                <mesh position={[0, 0, 0.01]} geometry={LOCK_CIRCLE_GEOMETRY}>
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
    const geometry = useMemo(() => new THREE.TorusGeometry(radius, 0.01, 8, 64), [radius]);

    useFrame((state) => {
        const t = state.clock.getElapsedTime();
        const wave = Math.sin(t * 1.5 + delay) * 0.5 + 0.5;
        meshRef.current.scale.setScalar(1 + wave * 0.1);
        (meshRef.current.material as THREE.MeshBasicMaterial).opacity = 0.3 - wave * 0.25;
    });

    return (
        <mesh ref={meshRef} rotation-x={Math.PI / 2} geometry={geometry}>
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
function generateSecurityParticles(count: number) {
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
}

function SecurityParticles({ count = 500 }: { count?: number }) {
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    const dummy = useMemo(() => new THREE.Object3D(), []);

    const [particles] = useState(() => generateSecurityParticles(count));

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
        <instancedMesh ref={meshRef} args={[PARTICLE_GEOMETRY, undefined, count]}>
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
function generateDataStreams(count: number) {
    return Array.from({ length: count }, () => ({
        position: new THREE.Vector3(
            (Math.random() - 0.5) * 10,
            Math.random() * 8 - 4,
            (Math.random() - 0.5) * 4 - 2
        ),
        speed: Math.random() * 0.03 + 0.02,
        scaleY: Math.random() * 1.5 + 0.5,
    }));
}

function DataStreams({ count = 30 }: { count?: number }) {
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    const dummy = useMemo(() => new THREE.Object3D(), []);
    const [streams] = useState(() => generateDataStreams(count));

    useFrame(() => {
        if (!meshRef.current) return;

        streams.forEach((stream, i) => {
            stream.position.y -= stream.speed;

            if (stream.position.y < -4) {
                stream.position.y = 4;
                stream.position.x = (Math.random() - 0.5) * 10;
            }

            dummy.position.copy(stream.position);
            dummy.scale.set(1, stream.scaleY, 1);
            dummy.updateMatrix();
            meshRef.current.setMatrixAt(i, dummy.matrix);
        });

        meshRef.current.instanceMatrix.needsUpdate = true;
    });

    return (
        <instancedMesh ref={meshRef} args={[DATA_STREAM_GEOMETRY, undefined, count]}>
            <meshBasicMaterial
                color="#00ff88"
                transparent
                opacity={0.3}
                blending={THREE.AdditiveBlending}
            />
        </instancedMesh>
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
            <mesh ref={meshRef} position={startPosition} geometry={ORB_GEOMETRY}>
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

            <SafeEffectComposer enableNormalPass={false} multisampling={0}>
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
            </SafeEffectComposer>
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
    const containerRef = useRef<HTMLDivElement>(null);
    const [dpr, setDpr] = useState(1);

    // Force a fresh WebGL tree for each auth route entry while keeping route-level remounts predictable.
    const sceneKey = `auth-scene:${pathname}`;

    return (
        <div key={sceneKey} ref={containerRef} className="absolute inset-0 z-0 pointer-events-none">
            <ErrorBoundary key={sceneKey} label="Auth 3D Scene">
                <Canvas
                    eventSource={containerRef}
                    camera={{ position: [0, 0, 5], fov: 50 }}
                    dpr={dpr}
                    gl={{
                        antialias: false,
                        alpha: true,
                        powerPreference: 'high-performance',
                    }}
                    style={{ background: 'transparent' }}
                >
                    <PerformanceMonitor 
                        onDecline={() => setDpr(0.75)} 
                        onIncline={() => setDpr(1.5)} 
                    />
                    <AuthSceneContent />
                </Canvas>
            </ErrorBoundary>
        </div>
    );
}
