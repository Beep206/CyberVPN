'use client';

import { Canvas, useFrame } from '@react-three/fiber';
import {
    Stars,
    Line,
    Sphere,
    OrbitControls,
    Trail
} from '@react-three/drei';
import { EffectComposer, Bloom, ChromaticAberration, ToneMapping } from '@react-three/postprocessing';
import { useRef, useMemo, useState } from 'react';
import * as THREE from 'three';

// Interfaces for props
interface NetworkServer {
    id: string;
    name: string;
    lat: number;
    lng: number;
    status: 'online' | 'offline' | 'warning' | 'maintenance';
}

interface NetworkConnection {
    from: { lat: number; lng: number };
    to: { lat: number; lng: number };
}

interface GlobalNetworkSceneProps {
    servers?: NetworkServer[];
    connections?: NetworkConnection[];
}

// Convert Lat/Lng to 3D Vector
function latLngToVector3(lat: number, lng: number, radius: number) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lng + 180) * (Math.PI / 180);

    return new THREE.Vector3(
        -radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.cos(phi),
        radius * Math.sin(phi) * Math.sin(theta)
    );
}

// Pulsing Glow Mesh for Servers
function PulsingGlow({ color }: { color: string }) {
    const mesh = useRef<THREE.Mesh>(null!);
    useFrame((state) => {
        const t = state.clock.getElapsedTime();
        mesh.current.scale.setScalar(1 + Math.sin(t * 3) * 0.3);
        (mesh.current.material as THREE.MeshBasicMaterial).opacity = 0.4 + Math.sin(t * 3) * 0.2;
    });

    return (
        <mesh ref={mesh}>
            <sphereGeometry args={[0.1, 16, 16]} />
            <meshBasicMaterial color={color} transparent depthWrite={false} blending={THREE.AdditiveBlending} />
        </mesh>
    );
}

// Server Nodes Component
function ServerNodes({ servers }: { servers: NetworkServer[] }) {
    return (
        <group>
            {servers.map((server) => {
                const position = latLngToVector3(server.lat, server.lng, 2);
                const color =
                    server.status === 'online' ? '#00ff88' :
                        server.status === 'offline' ? '#ff4444' :
                            server.status === 'warning' ? '#ffcc00' : '#bd00ff';

                return (
                    <group key={server.id} position={position}>
                        {/* Core Server Node */}
                        <Sphere args={[0.04, 16, 16]}>
                            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={2} toneMapped={false} />
                        </Sphere>

                        {/* Outer Ring */}
                        {server.status === 'online' && (
                            <mesh rotation-x={Math.PI / 2}>
                                <ringGeometry args={[0.06, 0.07, 32]} />
                                <meshBasicMaterial color={color} side={THREE.DoubleSide} transparent opacity={0.6} blending={THREE.AdditiveBlending} />
                            </mesh>
                        )}

                        {server.status === 'online' && (
                            <PulsingGlow color={color} />
                        )}
                    </group>
                );
            })}
        </group>
    );
}

// Animated Data Packet
function DataPacket({ curve, color, speed, offset }: { curve: THREE.QuadraticBezierCurve3, color: string, speed: number, offset: number }) {
    const mesh = useRef<THREE.Mesh>(null!);

    useFrame((state) => {
        const t = (state.clock.getElapsedTime() * speed + offset) % 1;
        const point = curve.getPoint(t);
        mesh.current.position.copy(point);
    });

    return (
        <mesh ref={mesh}>
            <sphereGeometry args={[0.015, 8, 8]} />
            <meshBasicMaterial color={color} toneMapped={false} />
        </mesh>
    );
}

// Connections Component with Data Packets
function ConnectionLines({ connections }: { connections: NetworkConnection[] }) {
    const curves = useMemo(() => {
        return connections.map(conn => {
            const start = latLngToVector3(conn.from.lat, conn.from.lng, 2);
            const end = latLngToVector3(conn.to.lat, conn.to.lng, 2);

            // Bezier curve control point (elevated)
            const mid = new THREE.Vector3()
                .addVectors(start, end)
                .multiplyScalar(0.5)
                .normalize()
                .multiplyScalar(2.5); // Elevation height

            return new THREE.QuadraticBezierCurve3(start, mid, end);
        });
    }, [connections]);

    return (
        <group>
            {curves.map((curve, i) => (
                <group key={i}>
                    {/* The static connection line */}
                    <Line
                        points={curve.getPoints(40)}
                        color="#00ffff"
                        lineWidth={0.5}
                        opacity={0.15}
                        transparent
                    />

                    {/* Animated packets traveling along the line */}
                    <DataPacket curve={curve} color="#00ffff" speed={0.5} offset={Math.random()} />
                    <DataPacket curve={curve} color="#ff00ff" speed={0.3} offset={Math.random() + 0.5} />
                </group>
            ))}
        </group>
    );
}

// Rotating Globe
function Globe() {
    const globeRef = useRef<THREE.Group>(null!);

    useFrame((state) => {
        globeRef.current.rotation.y = state.clock.getElapsedTime() * 0.03;
    });

    return (
        <group ref={globeRef}>
            {/* Holographic Earth Surface */}
            <Sphere args={[2, 64, 64]}>
                <meshPhongMaterial
                    color="#050510"
                    emissive="#001133"
                    emissiveIntensity={0.2}
                    shininess={40}
                    transparent
                    opacity={0.9}
                    side={THREE.DoubleSide}
                />
            </Sphere>

            {/* Grid Overlay */}
            <Sphere args={[2.01, 32, 32]}>
                <meshBasicMaterial
                    color="#004466"
                    wireframe
                    transparent
                    opacity={0.15}
                />
            </Sphere>
        </group>
    );
}

// Default Mock Data
const defaultServers: NetworkServer[] = [
    { id: '1', name: 'NY', lat: 40.7128, lng: -74.0060, status: 'online' },
    { id: '2', name: 'LDN', lat: 51.5074, lng: -0.1278, status: 'online' },
    { id: '3', name: 'JP', lat: 35.6762, lng: 139.6503, status: 'warning' },
    { id: '4', name: 'SG', lat: 1.3521, lng: 103.8198, status: 'online' },
    { id: '5', name: 'DE', lat: 52.5200, lng: 13.4050, status: 'maintenance' },
    { id: '6', name: 'BR', lat: -23.5505, lng: -46.6333, status: 'online' },
    { id: '7', name: 'AU', lat: -33.8688, lng: 151.2093, status: 'online' },
];

const defaultConnections: NetworkConnection[] = [
    { from: { lat: 40.7128, lng: -74.0060 }, to: { lat: 51.5074, lng: -0.1278 } }, // NY -> LDN
    { from: { lat: 51.5074, lng: -0.1278 }, to: { lat: 35.6762, lng: 139.6503 } }, // LDN -> JP
    { from: { lat: 35.6762, lng: 139.6503 }, to: { lat: 1.3521, lng: 103.8198 } }, // JP -> SG
    { from: { lat: 1.3521, lng: 103.8198 }, to: { lat: 52.5200, lng: 13.4050 } }, // SG -> DE
    { from: { lat: 52.5200, lng: 13.4050 }, to: { lat: 40.7128, lng: -74.0060 } }, // DE -> NY
    { from: { lat: 40.7128, lng: -74.0060 }, to: { lat: -23.5505, lng: -46.6333 } }, // NY -> BR
    { from: { lat: 35.6762, lng: 139.6503 }, to: { lat: -33.8688, lng: 151.2093 } }, // JP -> AU
    { from: { lat: -33.8688, lng: 151.2093 }, to: { lat: 1.3521, lng: 103.8198 } }, // AU -> SG
];


export default function GlobalNetworkScene({ servers = defaultServers, connections = defaultConnections }: GlobalNetworkSceneProps) {
    return (
        <div className="absolute inset-0 -z-10 bg-terminal-bg/0">
            <Canvas
                camera={{ position: [0, 0, 6.5], fov: 40 }}
                gl={{
                    antialias: true,
                    alpha: true,
                    powerPreference: "high-performance",
                    preserveDrawingBuffer: true
                }}
                dpr={[1, 2]}
            >
                <fog attach="fog" args={['#050510', 5, 20]} />

                <ambientLight intensity={0.2} />
                <pointLight position={[10, 10, 10]} color="#00ffff" intensity={1.5} />
                <pointLight position={[-10, -5, -10]} color="#ff00ff" intensity={1} />

                <Globe />
                <group rotation-y={0}>
                    <ServerNodes servers={servers} />
                    <ConnectionLines connections={connections} />
                </group>

                <Stars radius={50} depth={50} count={3000} factor={4} fade speed={0.5} />

                {/* Restricted Orbital Controls */}
                <OrbitControls
                    enableZoom={false}
                    enablePan={false}
                    autoRotate
                    autoRotateSpeed={0.5}
                    minPolarAngle={Math.PI / 3}
                    maxPolarAngle={Math.PI / 1.5}
                />

                <EffectComposer enableNormalPass={false} multisampling={0}>
                    <Bloom intensity={2} luminanceThreshold={0.2} mipmapBlur radius={0.5} />
                    <ChromaticAberration offset={new THREE.Vector2(0.001, 0.001)} />
                </EffectComposer>
            </Canvas>
        </div>
    );
}
