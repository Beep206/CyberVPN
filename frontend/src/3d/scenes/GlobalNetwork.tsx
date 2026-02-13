'use client';

import * as THREE from 'three';

const CHROMATIC_ABERRATION_OFFSET = new THREE.Vector2(0.002, 0.002);
import { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import {
    Line,
    Sphere,
    OrbitControls,
    Environment
} from '@react-three/drei';
import { EffectComposer, Bloom, ChromaticAberration, Noise, Vignette } from '@react-three/postprocessing';
// Import shaders to register them with R3F
// import '@/3d/shaders/CyberSphereShaderV2'; // REMOVED - Using Physical Geometry
import '@/3d/shaders/AtmosphereShader'; // Keeping atmosphere for outer glow only

// Module-level factory — outside render, not analyzed by React Compiler
function generateFloatingParticleData(count: number) {
    const positions = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);
    const phases = new Float32Array(count);

    for (let i = 0; i < count; i++) {
        const r = 4 + Math.random() * 8;
        const theta = Math.random() * 2 * Math.PI;
        const phi = Math.acos(2 * Math.random() - 1);

        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = r * Math.cos(phi);

        velocities[i * 3] = (Math.random() - 0.5) * 0.02;
        velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.02;
        velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.02;

        phases[i] = Math.random() * Math.PI * 2;
    }
    return { positions, velocities, phases };
}

function FloatingParticles({ count = 2000 }: { count?: number }) {
    const mesh = useRef<THREE.InstancedMesh>(null!);
    const [{ positions, velocities, phases }] = useState(() => generateFloatingParticleData(count));

    const dummy = useMemo(() => new THREE.Object3D(), []);

    /* eslint-disable react-hooks/immutability -- Float32Array mutations in animation loop are intentional */
    useFrame((state) => {
        const t = state.clock.getElapsedTime();

        for (let i = 0; i < count; i++) {
            const i3 = i * 3;

            // Orbital rotation (simple axis rotation for flow effect)
            // Apply rotation around Y
            const x = positions[i3];
            const z = positions[i3 + 2];
            const speed = 0.005 + Math.abs(velocities[i3 + 1]) * 0.5;

            positions[i3] = x * Math.cos(speed) - z * Math.sin(speed);
            positions[i3 + 2] = x * Math.sin(speed) + z * Math.cos(speed);

            // Tiny floaty vertical movement
            positions[i3 + 1] += Math.sin(t * 0.5 + phases[i]) * 0.01;

            dummy.position.set(
                positions[i3],
                positions[i3 + 1],
                positions[i3 + 2]
            );

            // Scale pulse
            const s = 0.5 + Math.sin(t * 2 + phases[i]) * 0.5;
            dummy.scale.setScalar(s);

            dummy.updateMatrix();
            mesh.current.setMatrixAt(i, dummy.matrix);
        }
        mesh.current.instanceMatrix.needsUpdate = true;
    });
    /* eslint-enable react-hooks/immutability */

    return (
        <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
            <icosahedronGeometry args={[0.03, 0]} />
            <meshBasicMaterial
                color="#00ffff"
                transparent
                opacity={0.6}
                blending={THREE.AdditiveBlending}
            />
        </instancedMesh>
    );
}

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
            {curves.map((curve, i) => {
                const conn = connections[i];
                const key = `${conn.from.lat},${conn.from.lng}-${conn.to.lat},${conn.to.lng}`;
                return (
                    <group key={key}>
                        {/* The static connection line */}
                        <Line
                            points={curve.getPoints(40)}
                            color="#00ffff"
                            lineWidth={0.5}
                            opacity={0.15}
                            transparent
                        />

                        {/* Animated packets traveling along the line */}
                        <DataPacket curve={curve} color="#00ffff" speed={0.5} offset={((i * 9301 + 49297) % 233280) / 233280} />
                        <DataPacket curve={curve} color="#ff00ff" speed={0.3} offset={((i * 9301 + 49297) % 233280) / 233280 + 0.5} />
                    </group>
                );
            })}
        </group>
    );
}

// Helper Component for Explicit Wireframe Rendering
// FIXED: Increased scale, disabled depthTest, disabled fog for guaranteed visibility
function WireframeSphere({ radius = 2, detail = 4, color = "#00ffff", opacity = 1.0, scaleOffset = 1.05 }: { radius?: number; detail?: number; color?: string; opacity?: number; scaleOffset?: number }) {
    const geometry = useMemo(() => {
        const geo = new THREE.IcosahedronGeometry(radius, detail);
        return new THREE.WireframeGeometry(geo);
    }, [radius, detail]);

    return (
        <lineSegments geometry={geometry} scale={[scaleOffset, scaleOffset, scaleOffset]} renderOrder={10}>
            <lineBasicMaterial
                color={color}
                transparent
                opacity={opacity}
                depthTest={false}
                depthWrite={false}
                toneMapped={false}
                fog={false}
                linewidth={1}
            />
        </lineSegments>
    );
}

// THE OBSIDIAN SPHERE (Physical Tech Construction)
function ObsidianSphere() {
    const globeRef = useRef<THREE.Group>(null!);

    useFrame((state) => {
        globeRef.current.rotation.y = state.clock.getElapsedTime() * 0.05;
    });

    return (
        <group ref={globeRef}>
            {/* 1. THE CORE: Black, Glossy, Solid (Obsidian) */}
            <mesh renderOrder={0}>
                <icosahedronGeometry args={[2, 20]} />
                <meshPhysicalMaterial
                    color="#000000"
                    roughness={0.1}
                    metalness={0.8}
                    clearcoat={1.0}
                    clearcoatRoughness={0.1}
                    side={THREE.FrontSide}
                />
            </mesh>

            {/* 2. THE SKELETON: Physical Line Segments - ALWAYS VISIBLE */}
            <WireframeSphere radius={2} detail={3} color="#00ffff" opacity={0.8} scaleOffset={1.02} />

            {/* 3. THE FRAME: Outer Structural Lines */}
            <WireframeSphere radius={2} detail={1} color="#ffffff" opacity={0.5} scaleOffset={1.05} />

            {/* 4. THE ATMOSPHERE: Subtle outer glow (using shader) */}
            <mesh scale={[1.2, 1.2, 1.2]} renderOrder={-1}>
                <sphereGeometry args={[2, 32, 32]} />
                <atmosphereShader
                    side={THREE.BackSide}
                    transparent
                    blending={THREE.AdditiveBlending}
                />
            </mesh>
        </group>
    );
}

// Default Mock Data
const DEFAULT_SERVERS: NetworkServer[] = [
    { id: '1', name: 'NY', lat: 40.7128, lng: -74.0060, status: 'online' },
    { id: '2', name: 'LDN', lat: 51.5074, lng: -0.1278, status: 'online' },
    { id: '3', name: 'JP', lat: 35.6762, lng: 139.6503, status: 'warning' },
    { id: '4', name: 'SG', lat: 1.3521, lng: 103.8198, status: 'online' },
    { id: '5', name: 'DE', lat: 52.5200, lng: 13.4050, status: 'maintenance' },
    { id: '6', name: 'BR', lat: -23.5505, lng: -46.6333, status: 'online' },
    { id: '7', name: 'AU', lat: -33.8688, lng: 151.2093, status: 'online' },
];

const DEFAULT_CONNECTIONS: NetworkConnection[] = [
    { from: { lat: 40.7128, lng: -74.0060 }, to: { lat: 51.5074, lng: -0.1278 } }, // NY -> LDN
    { from: { lat: 51.5074, lng: -0.1278 }, to: { lat: 35.6762, lng: 139.6503 } }, // LDN -> JP
    { from: { lat: 35.6762, lng: 139.6503 }, to: { lat: 1.3521, lng: 103.8198 } }, // JP -> SG
    { from: { lat: 1.3521, lng: 103.8198 }, to: { lat: 52.5200, lng: 13.4050 } }, // SG -> DE
    { from: { lat: 52.5200, lng: 13.4050 }, to: { lat: 40.7128, lng: -74.0060 } }, // DE -> NY
    { from: { lat: 40.7128, lng: -74.0060 }, to: { lat: -23.5505, lng: -46.6333 } }, // NY -> BR
    { from: { lat: 35.6762, lng: 139.6503 }, to: { lat: -33.8688, lng: 151.2093 } }, // JP -> AU
    { from: { lat: -33.8688, lng: 151.2093 }, to: { lat: 1.3521, lng: 103.8198 } }, // AU -> SG
];


// Parallax Camera Rig
// Parallax Group Component
function ParallaxGroup({ children }: { children: React.ReactNode }) {
    const group = useRef<THREE.Group>(null!);

    useFrame((state) => {
        const { pointer } = state;
        // Rotate the entire group slightly based on mouse position
        group.current.rotation.y = THREE.MathUtils.lerp(group.current.rotation.y, pointer.x * 0.2, 0.1);
        group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, -pointer.y * 0.2, 0.1);
    });

    return <group ref={group}>{children}</group>;
}

export default function GlobalNetworkScene({ servers = DEFAULT_SERVERS, connections = DEFAULT_CONNECTIONS }: GlobalNetworkSceneProps) {
    return (
        <div className="absolute inset-0 -z-10 bg-terminal-bg/0">
            <Canvas
                frameloop="always"
                performance={{ min: 0.5 }}
                camera={{ position: [0, 2, 7], fov: 40 }}
                gl={{
                    antialias: false,
                    alpha: true,
                    powerPreference: "high-performance",
                    stencil: false,
                    depth: true
                }}
                dpr={[1, 1.5]}
            >
                {/* Reduced fog density to ensure stars are visible */}
                <fog attach="fog" args={['#050510', 5, 25]} />

                {/* Environment for Glossy Reflections */}
                <Environment preset="city" />

                <ambientLight intensity={0.2} />
                <pointLight position={[10, 10, 10]} color="#00ffff" intensity={1.5} />
                <pointLight position={[-10, -5, -10]} color="#ff00ff" intensity={1} />

                {/* Parallax Wrapper for Scene Content */}
                <ParallaxGroup>
                    <ObsidianSphere />
                    <group rotation-y={0}>
                        <ServerNodes servers={servers} />
                        <ConnectionLines connections={connections} />
                    </group>
                </ParallaxGroup>

                <FloatingParticles count={800} />

                {/* OrbitControls for auto-rotation, but disable user interaction to not fight parallax */}
                <OrbitControls
                    enableZoom={false}
                    enablePan={false}
                    enableRotate={false}
                    autoRotate
                    autoRotateSpeed={0.5}
                />

                <EffectComposer enableNormalPass={false} multisampling={0}>
                    <Bloom luminanceThreshold={0.5} mipmapBlur intensity={0.5} radius={0.2} />
                    <Noise opacity={0.05} />
                    <Vignette eskil={false} offset={0.1} darkness={1.1} />
                    <ChromaticAberration offset={CHROMATIC_ABERRATION_OFFSET} radialModulation={false} modulationOffset={0} />
                </EffectComposer>
            </Canvas>
        </div>
    );
}
