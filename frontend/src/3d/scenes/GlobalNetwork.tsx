'use client';

import { Canvas, useFrame } from '@react-three/fiber';
import {
    Stars,
    Line,
    Sphere,
    OrbitControls,
} from '@react-three/drei';
import { EffectComposer, Bloom, ChromaticAberration } from '@react-three/postprocessing';
import { useRef, useMemo } from 'react';
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

// Pulsing Glow Mesh
function PulsingGlow({ color }: { color: string }) {
    const mesh = useRef<THREE.Mesh>(null!);
    useFrame((state) => {
        const t = state.clock.getElapsedTime();
        mesh.current.scale.setScalar(1 + Math.sin(t * 3) * 0.2);
        (mesh.current.material as THREE.MeshBasicMaterial).opacity = 0.5 + Math.sin(t * 3) * 0.3;
    });

    return (
        <mesh ref={mesh}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshBasicMaterial color={color} transparent />
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
                        <Sphere args={[0.05, 16, 16]}>
                            <meshBasicMaterial color={color} />
                        </Sphere>

                        {server.status === 'online' && (
                            <PulsingGlow color={color} />
                        )}

                        {/* HTML Label - hidden when far or occluded could be added */}
                        {/* Keeping it simple for performance */}
                    </group>
                );
            })}
        </group>
    );
}

// Connections Component
function ConnectionLines({ connections }: { connections: NetworkConnection[] }) {
    const points = useMemo(() => {
        return connections.map(conn => {
            const start = latLngToVector3(conn.from.lat, conn.from.lng, 2);
            const end = latLngToVector3(conn.to.lat, conn.to.lng, 2);

            // Bezier curve control point (elevated)
            const mid = new THREE.Vector3()
                .addVectors(start, end)
                .multiplyScalar(0.5)
                .normalize()
                .multiplyScalar(2.5); // Elevation height

            const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
            return curve.getPoints(40);
        });
    }, [connections]);

    return (
        <group>
            {points.map((linePoints, i) => (
                <Line
                    key={i}
                    points={linePoints}
                    color="#00ffff"
                    lineWidth={1}
                    opacity={0.3}
                    transparent
                />
            ))}
        </group>
    );
}

// Rotating Globe
function Globe() {
    const globeRef = useRef<THREE.Group>(null!);

    useFrame((state) => {
        globeRef.current.rotation.y = state.clock.getElapsedTime() * 0.05;
    });

    return (
        <group ref={globeRef}>
            {/* Wireframe Globe */}
            <Sphere args={[2, 32, 32]}>
                <meshBasicMaterial
                    color="#0a0a20"
                    wireframe
                    transparent
                    opacity={0.15}
                />
            </Sphere>

            {/* Inner Globe (Darkness) */}
            <Sphere args={[1.95, 64, 64]}>
                <meshBasicMaterial color="#000510" />
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
];

const defaultConnections: NetworkConnection[] = [
    { from: { lat: 40.7128, lng: -74.0060 }, to: { lat: 51.5074, lng: -0.1278 } }, // NY -> LDN
    { from: { lat: 51.5074, lng: -0.1278 }, to: { lat: 35.6762, lng: 139.6503 } }, // LDN -> JP
    { from: { lat: 35.6762, lng: 139.6503 }, to: { lat: 1.3521, lng: 103.8198 } }, // JP -> SG
    { from: { lat: 1.3521, lng: 103.8198 }, to: { lat: 52.5200, lng: 13.4050 } }, // SG -> DE
    { from: { lat: 52.5200, lng: 13.4050 }, to: { lat: 40.7128, lng: -74.0060 } }, // DE -> NY
];

export default function GlobalNetworkScene({ servers = defaultServers, connections = defaultConnections }: GlobalNetworkSceneProps) {
    return (
        <div className="absolute inset-0 -z-10 bg-terminal-bg">
            <Canvas
                camera={{ position: [0, 2, 5], fov: 45 }}
                gl={{
                    antialias: true,
                    alpha: true,
                    powerPreference: "high-performance",
                    preserveDrawingBuffer: true
                }}
                dpr={[1, 2]}
            >
                <fog attach="fog" args={['#050510', 5, 12]} />

                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} color="#00ffff" intensity={1} />

                <Globe />
                <group rotation-y={0}>
                    <ServerNodes servers={servers} />
                    <ConnectionLines connections={connections} />
                </group>

                <Stars radius={50} depth={50} count={3000} factor={4} fade speed={1} />

                <OrbitControls
                    enableZoom={false}
                    enablePan={false}
                    autoRotate
                    autoRotateSpeed={0.5}
                    minPolarAngle={Math.PI / 4}
                    maxPolarAngle={Math.PI / 2}
                />

                <EffectComposer enableNormalPass={false} multisampling={0} autoClear={false}>
                    <Bloom intensity={1.5} luminanceThreshold={0.1} mipmapBlur />
                    <ChromaticAberration offset={new THREE.Vector2(0.002, 0.002)} />
                </EffectComposer>
            </Canvas>
        </div>
    );
}
