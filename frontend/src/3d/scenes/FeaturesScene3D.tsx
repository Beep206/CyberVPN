'use client';

import * as THREE from 'three';
import { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Trail, MeshTransmissionMaterial } from '@react-three/drei';
import { ErrorBoundary } from '@/shared/ui/error-boundary';

// Floating Cyber Particles - Performance optimized with InstancedMesh
function CyberParticles({ count = 800 }: { count?: number }) {
    const meshRef = useRef<THREE.InstancedMesh>(null);
    const dummy = useMemo(() => new THREE.Object3D(), []);

    // Generate random positions and velocities
    const particles = useMemo(() => {
        return Array.from({ length: count }, () => ({
            position: new THREE.Vector3(
                (Math.random() - 0.5) * 20,
                (Math.random() - 0.5) * 12,
                (Math.random() - 0.5) * 10
            ),
            velocity: new THREE.Vector3(
                (Math.random() - 0.5) * 0.02,
                (Math.random() - 0.5) * 0.02,
                (Math.random() - 0.5) * 0.01
            ),
            scale: Math.random() * 0.5 + 0.1,
            phase: Math.random() * Math.PI * 2,
        }));
    }, [count]);

    useFrame((state) => {
        if (!meshRef.current) return;
        const time = state.clock.getElapsedTime();

        particles.forEach((particle, i) => {
            // Random wandering motion
            particle.position.x += particle.velocity.x + Math.sin(time + particle.phase) * 0.003;
            particle.position.y += particle.velocity.y + Math.cos(time * 0.7 + particle.phase) * 0.003;
            particle.position.z += particle.velocity.z;

            // Wrap around boundaries
            if (particle.position.x > 10) particle.position.x = -10;
            if (particle.position.x < -10) particle.position.x = 10;
            if (particle.position.y > 6) particle.position.y = -6;
            if (particle.position.y < -6) particle.position.y = 6;
            if (particle.position.z > 5) particle.position.z = -5;
            if (particle.position.z < -5) particle.position.z = 5;

            dummy.position.copy(particle.position);
            dummy.scale.setScalar(particle.scale * (0.8 + Math.sin(time * 2 + particle.phase) * 0.2));
            dummy.updateMatrix();
            meshRef.current!.setMatrixAt(i, dummy.matrix);
        });

        meshRef.current.instanceMatrix.needsUpdate = true;
    });

    return (
        <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
            <dodecahedronGeometry args={[0.03, 0]} />
            <meshBasicMaterial color="#00ffff" transparent opacity={0.6} />
        </instancedMesh>
    );
}

// Hexagonal Shield Grid
function HexagonalShield({ position = [0, 0, 0] as [number, number, number] }) {
    const groupRef = useRef<THREE.Group>(null);
    const [hovered, setHovered] = useState(false);

    // Generate hexagon grid positions
    const hexagons = useMemo(() => {
        const hexes: { x: number; y: number; delay: number }[] = [];
        const radius = 0.3;
        const rows = 5;
        const cols = 7;

        for (let row = 0; row < rows; row++) {
            for (let col = 0; col < cols; col++) {
                const offset = row % 2 === 0 ? 0 : radius * 0.866;
                hexes.push({
                    x: col * radius * 1.732 + offset - (cols * radius * 0.866),
                    y: row * radius * 1.5 - (rows * radius * 0.75),
                    delay: (row + col) * 0.1,
                });
            }
        }
        return hexes;
    }, []);

    useFrame((state) => {
        if (!groupRef.current) return;
        const time = state.clock.getElapsedTime();
        groupRef.current.rotation.z = Math.sin(time * 0.3) * 0.05;
        groupRef.current.rotation.y = Math.sin(time * 0.2) * 0.1;
    });

    return (
        <Float speed={2} rotationIntensity={0.3} floatIntensity={0.5}>
            <group
                ref={groupRef}
                position={position}
                onPointerEnter={() => setHovered(true)}
                onPointerLeave={() => setHovered(false)}
            >
                {hexagons.map((hex, i) => (
                    <HexCell
                        key={i}
                        position={[hex.x, hex.y, 0]}
                        delay={hex.delay}
                        hovered={hovered}
                    />
                ))}
                {/* Central glow */}
                <mesh>
                    <sphereGeometry args={[0.5, 16, 16]} />
                    <meshBasicMaterial
                        color="#00ffff"
                        transparent
                        opacity={hovered ? 0.3 : 0.1}
                    />
                </mesh>
            </group>
        </Float>
    );
}

function HexCell({
    position,
    delay,
    hovered
}: {
    position: [number, number, number];
    delay: number;
    hovered: boolean;
}) {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((state) => {
        if (!meshRef.current) return;
        const time = state.clock.getElapsedTime();
        const wave = Math.sin(time * 2 + delay) * 0.5 + 0.5;
        const material = meshRef.current.material as THREE.MeshBasicMaterial;
        material.opacity = hovered ? 0.4 + wave * 0.4 : 0.1 + wave * 0.2;
    });

    // Hexagon shape
    const hexShape = useMemo(() => {
        const shape = new THREE.Shape();
        const size = 0.12;
        for (let i = 0; i < 6; i++) {
            const angle = (Math.PI / 3) * i - Math.PI / 6;
            const x = Math.cos(angle) * size;
            const y = Math.sin(angle) * size;
            if (i === 0) shape.moveTo(x, y);
            else shape.lineTo(x, y);
        }
        shape.closePath();
        return shape;
    }, []);

    return (
        <mesh ref={meshRef} position={position}>
            <shapeGeometry args={[hexShape]} />
            <meshBasicMaterial
                color="#00ffff"
                transparent
                opacity={0.2}
                side={THREE.DoubleSide}
                wireframe
            />
        </mesh>
    );
}

// Speed Lines Effect
function SpeedLines({ count = 50 }: { count?: number }) {
    const linesRef = useRef<THREE.Group>(null);

    const lines = useMemo(() => {
        return Array.from({ length: count }, () => ({
            x: (Math.random() - 0.5) * 15,
            y: (Math.random() - 0.5) * 8,
            z: Math.random() * -10 - 2,
            length: Math.random() * 2 + 0.5,
            speed: Math.random() * 0.1 + 0.05,
        }));
    }, [count]);

    useFrame(() => {
        if (!linesRef.current) return;
        linesRef.current.children.forEach((child, i) => {
            const line = lines[i];
            child.position.z += line.speed;
            if (child.position.z > 2) {
                child.position.z = -12;
                child.position.x = (Math.random() - 0.5) * 15;
                child.position.y = (Math.random() - 0.5) * 8;
            }
        });
    });

    return (
        <group ref={linesRef}>
            {lines.map((line, i) => (
                <mesh key={i} position={[line.x, line.y, line.z]}>
                    <boxGeometry args={[0.01, 0.01, line.length]} />
                    <meshBasicMaterial color="#00ffff" transparent opacity={0.3} />
                </mesh>
            ))}
        </group>
    );
}

// Glowing Orb with Trail
function GlowingOrb({
    color = '#00ffff',
    position = [0, 0, 0] as [number, number, number],
    radius = 0.15
}) {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((state) => {
        if (!meshRef.current) return;
        const time = state.clock.getElapsedTime();
        meshRef.current.position.x = position[0] + Math.sin(time * 0.5) * 2;
        meshRef.current.position.y = position[1] + Math.cos(time * 0.3) * 1;
        meshRef.current.position.z = position[2] + Math.sin(time * 0.7) * 0.5;
    });

    return (
        <Trail
            width={1}
            length={8}
            color={color}
            attenuation={(t) => t * t}
        >
            <mesh ref={meshRef} position={position}>
                <sphereGeometry args={[radius, 16, 16]} />
                <meshBasicMaterial color={color} transparent opacity={0.8} />
            </mesh>
        </Trail>
    );
}

// Floating Tech Ring
function TechRing({ radius = 3, segments = 64 }) {
    const ringRef = useRef<THREE.Mesh>(null);

    useFrame((state) => {
        if (!ringRef.current) return;
        const time = state.clock.getElapsedTime();
        ringRef.current.rotation.x = Math.PI / 2 + Math.sin(time * 0.3) * 0.2;
        ringRef.current.rotation.z = time * 0.1;
    });

    return (
        <mesh ref={ringRef} position={[0, 0, -2]}>
            <torusGeometry args={[radius, 0.02, 8, segments]} />
            <meshBasicMaterial color="#9d00ff" transparent opacity={0.3} />
        </mesh>
    );
}

// Data Grid Background
function DataGrid() {
    const gridRef = useRef<THREE.Group>(null);

    useFrame((state) => {
        if (!gridRef.current) return;
        const time = state.clock.getElapsedTime();
        gridRef.current.position.z = (time * 0.5) % 2 - 6;
    });

    const lines = useMemo(() => {
        const horizontalLines = [];
        const verticalLines = [];

        for (let i = -10; i <= 10; i += 1) {
            horizontalLines.push(i);
            verticalLines.push(i);
        }

        return { horizontalLines, verticalLines };
    }, []);

    return (
        <group ref={gridRef} position={[0, 0, -6]} rotation={[Math.PI / 2, 0, 0]}>
            {lines.horizontalLines.map((y, i) => (
                <mesh key={`h-${i}`} position={[0, y, 0]}>
                    <boxGeometry args={[20, 0.01, 0.01]} />
                    <meshBasicMaterial color="#00ffff" transparent opacity={0.1} />
                </mesh>
            ))}
            {lines.verticalLines.map((x, i) => (
                <mesh key={`v-${i}`} position={[x, 0, 0]}>
                    <boxGeometry args={[0.01, 20, 0.01]} />
                    <meshBasicMaterial color="#00ffff" transparent opacity={0.1} />
                </mesh>
            ))}
        </group>
    );
}

// Main Scene Component
function FeaturesSceneContent() {
    return (
        <>
            {/* Ambient light for visibility */}
            <ambientLight intensity={0.5} />

            {/* Background elements */}
            <DataGrid />
            <SpeedLines count={40} />
            <TechRing radius={4} />
            <TechRing radius={5} />

            {/* Floating particles */}
            <CyberParticles count={600} />

            {/* Shield element - left side */}
            <HexagonalShield position={[-4, 0, -1]} />

            {/* Glowing orbs for visual interest */}
            <GlowingOrb color="#00ffff" position={[3, 1, 0]} radius={0.1} />
            <GlowingOrb color="#9d00ff" position={[-3, -1, 0]} radius={0.08} />
            <GlowingOrb color="#00ff88" position={[0, 2, -1]} radius={0.06} />
        </>
    );
}

// Exported wrapper component
export function FeaturesScene3D() {
    return (
        <div className="absolute inset-0 z-0 pointer-events-none">
            <ErrorBoundary label="Features 3D Scene">
                <Canvas
                    camera={{ position: [0, 0, 6], fov: 60 }}
                    dpr={[1, 1.5]}
                    gl={{
                        antialias: true,
                        alpha: true,
                        powerPreference: 'high-performance'
                    }}
                    style={{ background: 'transparent' }}
                >
                    <FeaturesSceneContent />
                </Canvas>
            </ErrorBoundary>
        </div>
    );
}

// Wrapper for SSR compatibility
export function FeaturesScene3DWrapper() {
    const [mounted, setMounted] = useState(false);

    // Only render on client
    if (typeof window === 'undefined') return null;

    return (
        <div className="absolute inset-0 z-0">
            <FeaturesScene3D />
        </div>
    );
}
