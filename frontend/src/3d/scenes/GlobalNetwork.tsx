'use client';

import * as THREE from 'three';

const CHROMATIC_ABERRATION_OFFSET = new THREE.Vector2(0.002, 0.002);
import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import {
    Line,
    Environment,
    PerformanceMonitor
} from '@react-three/drei';
import { useInView } from 'motion/react';
import { Bloom, ChromaticAberration } from '@react-three/postprocessing';
import { ScenePerformanceMetrics } from '@/3d/components/scene-performance-metrics';
import { SafeEffectComposer } from '@/3d/components/safe-effect-composer';
import {
    MARKETING_SCENE_CANVAS_PERFORMANCE,
    MARKETING_SCENE_GL,
    useAdaptiveSceneDpr,
} from '@/3d/lib/scene-performance';
import { useCanvasHost } from '@/shared/hooks/use-canvas-host';
import { createDeterministicRandom, randomInRange, randomSigned } from '@/3d/lib/seeded-random';
// Import shaders to register them with R3F
// import '@/3d/shaders/CyberSphereShaderV2'; // REMOVED - Using Physical Geometry
import '@/3d/shaders/AtmosphereShader'; // Keeping atmosphere for outer glow only

const particleVertexShader = `
    uniform float uTime;
    attribute float aPhase;
    attribute float aSpeed;
    varying vec3 vColor;
    void main() {
        vec3 pos = position;
        
        // Orbital rotation around Y axis
        float currentAngle = aSpeed * uTime;
        float x = instanceMatrix[3][0];
        float z = instanceMatrix[3][2];
        
        float finalX = x * cos(currentAngle) - z * sin(currentAngle);
        float finalZ = x * sin(currentAngle) + z * cos(currentAngle);
        
        // Vertical hover oscillation
        float finalY = instanceMatrix[3][1] + sin(uTime * 0.5 + aPhase) * 0.5; // Scaled up oscillation to match scale effect
        
        // Dynamic scale
        float scale = 0.5 + sin(uTime * 2.0 + aPhase) * 0.5;
        pos *= scale;

        // Apply instance transformation
        vec4 mvPosition = viewMatrix * modelMatrix * vec4(finalX + pos.x, finalY + pos.y, finalZ + pos.z, 1.0);
        gl_Position = projectionMatrix * mvPosition;
    }
`;

const particleFragmentShader = `
    void main() {
        gl_FragColor = vec4(0.0, 1.0, 1.0, 0.6); // Cyan transparent
    }
`;

function FloatingParticles({ count = 2000 }: { count?: number }) {
    const mesh = useRef<THREE.InstancedMesh>(null!);
    const materialRef = useRef<THREE.ShaderMaterial>(null!);
    
    // Generate initial state once
    const { instanceMatrix, phases, speeds } = useMemo(() => {
        const random = createDeterministicRandom(count * 59);
        const matrix = new THREE.InstancedBufferAttribute(new Float32Array(count * 16), 16);
        const p = new Float32Array(count);
        const s = new Float32Array(count);
        const dummy = new THREE.Object3D();
        
        for (let i = 0; i < count; i++) {
            // Give them random starting positions (similar to worker, simplified here for speed)
            const radius = randomInRange(random, 2, 6);
            const theta = randomInRange(random, 0, Math.PI * 2);
            const y = randomSigned(random, 2);
            
            dummy.position.set(radius * Math.cos(theta), y, radius * Math.sin(theta));
            dummy.updateMatrix();
            dummy.matrix.toArray(matrix.array, i * 16);
            
            p[i] = randomInRange(random, 0, Math.PI * 2);
            s[i] = randomInRange(random, 0.005, 0.055);
        }
        return { instanceMatrix: matrix, phases: p, speeds: s };
    }, [count]);

    // Add attributes to geometry
    const geometry = useMemo(() => {
        const geo = new THREE.IcosahedronGeometry(0.03, 0);
        geo.setAttribute('aPhase', new THREE.InstancedBufferAttribute(phases, 1));
        geo.setAttribute('aSpeed', new THREE.InstancedBufferAttribute(speeds, 1));
        return geo;
    }, [phases, speeds]);

    useFrame((state) => {
        if (materialRef.current) {
            materialRef.current.uniforms.uTime.value = state.clock.getElapsedTime();
        }
    });

    return (
        <instancedMesh ref={mesh} args={[geometry, undefined, count]} instanceMatrix={instanceMatrix}>
            <shaderMaterial
                ref={materialRef}
                vertexShader={particleVertexShader}
                fragmentShader={particleFragmentShader}
                uniforms={{ uTime: { value: 0 } }}
                transparent
                depthWrite={false}
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
    activeNodeId?: string | null;
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

function ServerNodes({
    servers,
    serverPositions,
    activeNodeId,
}: {
    servers: NetworkServer[];
    serverPositions: THREE.Vector3[];
    activeNodeId?: string | null;
}) {
    const coreRef = useRef<THREE.InstancedMesh>(null!);
    const ringRef = useRef<THREE.InstancedMesh>(null!);
    const glowRef = useRef<THREE.InstancedMesh>(null!);
    const ringMaterialRef = useRef<THREE.MeshBasicMaterial>(null!);
    const glowMaterialRef = useRef<THREE.MeshBasicMaterial>(null!);

    const coreGeo = useMemo(() => new THREE.SphereGeometry(0.04, 16, 16), []);
    const ringGeo = useMemo(() => new THREE.RingGeometry(0.06, 0.07, 32), []);
    const glowGeo = useMemo(() => new THREE.SphereGeometry(0.1, 16, 16), []);

    React.useEffect(() => {
        if (!coreRef.current || !ringRef.current || !glowRef.current) return;

        const dummy = new THREE.Object3D();
        const color = new THREE.Color();

        servers.forEach((server, i) => {
            const pos = serverPositions[i];
            dummy.position.copy(pos);
            dummy.rotation.set(0, 0, 0);

            const isHovered = activeNodeId === server.id;
            const isDimmed = activeNodeId && !isHovered;

            dummy.scale.setScalar(isHovered ? 1.5 : (isDimmed ? 0.8 : 1));
            dummy.updateMatrix();

            let cStr = server.status === 'online' ? '#00ff88' :
                server.status === 'offline' ? '#ff4444' :
                    server.status === 'warning' ? '#ffcc00' : '#bd00ff';

            if (isHovered) cStr = '#00ffff';
            if (isDimmed) color.set(cStr).multiplyScalar(0.3);
            else color.set(cStr);

            coreRef.current.setMatrixAt(i, dummy.matrix);
            coreRef.current.setColorAt(i, color);

            if (server.status === 'online') {
                dummy.rotation.x = Math.PI / 2;
                dummy.updateMatrix();
                ringRef.current.setMatrixAt(i, dummy.matrix);

                const ringColor = new THREE.Color(cStr);
                if (isHovered) ringColor.multiplyScalar(2);
                ringRef.current.setColorAt(i, ringColor);

                dummy.rotation.set(0, 0, 0);
                dummy.scale.setScalar(isHovered ? 2 : 1);
                dummy.updateMatrix();
                glowRef.current.setMatrixAt(i, dummy.matrix);
                glowRef.current.setColorAt(i, color);
            } else {
                dummy.scale.setScalar(0);
                dummy.updateMatrix();
                ringRef.current.setMatrixAt(i, dummy.matrix);
                glowRef.current.setMatrixAt(i, dummy.matrix);
            }
        });

        coreRef.current.instanceMatrix.needsUpdate = true;
        if (coreRef.current.instanceColor) coreRef.current.instanceColor.needsUpdate = true;
        ringRef.current.instanceMatrix.needsUpdate = true;
        if (ringRef.current.instanceColor) ringRef.current.instanceColor.needsUpdate = true;
        glowRef.current.instanceMatrix.needsUpdate = true;
        if (glowRef.current.instanceColor) glowRef.current.instanceColor.needsUpdate = true;
    }, [activeNodeId, serverPositions, servers]);

    useFrame((state) => {
        const pulse = Math.sin(state.clock.getElapsedTime() * 3);

        if (glowMaterialRef.current) {
            glowMaterialRef.current.opacity = 0.42 + pulse * 0.12;
        }

        if (ringMaterialRef.current) {
            ringMaterialRef.current.opacity = 0.56 + pulse * 0.06;
        }
    });

    return (
        <group>
            <instancedMesh ref={coreRef} args={[coreGeo, undefined, servers.length]}>
                <meshStandardMaterial toneMapped={false} />
            </instancedMesh>
            <instancedMesh ref={ringRef} args={[ringGeo, undefined, servers.length]}>
                <meshBasicMaterial ref={ringMaterialRef} side={THREE.DoubleSide} transparent opacity={0.6} blending={THREE.AdditiveBlending} />
            </instancedMesh>
            <instancedMesh ref={glowRef} args={[glowGeo, undefined, servers.length]}>
                <meshBasicMaterial ref={glowMaterialRef} transparent depthWrite={false} opacity={0.42} blending={THREE.AdditiveBlending} />
            </instancedMesh>
        </group>
    );
}

const packetVertexShader = `
    uniform float uTime;
    attribute vec3 aStart;
    attribute vec3 aMid;
    attribute vec3 aEnd;
    attribute float aOffset;
    attribute float aSpeed;
    
    // Quadratic Bezier Interpolation
    vec3 getBezierPoint(float t, vec3 p0, vec3 p1, vec3 p2) {
        float u = 1.0 - t;
        float tt = t * t;
        float uu = u * u;
        vec3 p = uu * p0; 
        p += 2.0 * u * t * p1; 
        p += tt * p2; 
        return p;
    }

    void main() {
        // Calculate progress normalized 0 to 1
        float t = fract(uTime * aSpeed + aOffset);
        
        vec3 pos = getBezierPoint(t, aStart, aMid, aEnd);
        
        vec4 mvPosition = viewMatrix * modelMatrix * vec4(pos + position, 1.0);
        gl_Position = projectionMatrix * mvPosition;
    }
`;

const packetFragmentShader = `
    uniform vec3 uColor;
    void main() {
        gl_FragColor = vec4(uColor, 1.0);
    }
`;

function DataPackets({ curves, color, speedBase, offsetBase }: { curves: THREE.QuadraticBezierCurve3[], color: string, speedBase: number, offsetBase: number }) {
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    const materialRef = useRef<THREE.ShaderMaterial>(null!);
    
    const count = curves.length;
    
    const { startArr, midArr, endArr, offsetArr, speedArr } = useMemo(() => {
        const _s = new Float32Array(count * 3);
        const _m = new Float32Array(count * 3);
        const _e = new Float32Array(count * 3);
        const _o = new Float32Array(count);
        const _sp = new Float32Array(count);
        
        curves.forEach((curve, i) => {
            _s[i*3] = curve.v0.x; _s[i*3+1] = curve.v0.y; _s[i*3+2] = curve.v0.z;
            _m[i*3] = curve.v1.x; _m[i*3+1] = curve.v1.y; _m[i*3+2] = curve.v1.z;
            _e[i*3] = curve.v2.x; _e[i*3+1] = curve.v2.y; _e[i*3+2] = curve.v2.z;
            
            _o[i] = ((i * 9301 + 49297) % 233280) / 233280 + offsetBase;
            _sp[i] = speedBase;
        });
        return { startArr: _s, midArr: _m, endArr: _e, offsetArr: _o, speedArr: _sp };
    }, [curves, count, offsetBase, speedBase]);

    const geometry = useMemo(() => {
        const geo = new THREE.SphereGeometry(0.015, 8, 8);
        geo.setAttribute('aStart', new THREE.InstancedBufferAttribute(startArr, 3));
        geo.setAttribute('aMid', new THREE.InstancedBufferAttribute(midArr, 3));
        geo.setAttribute('aEnd', new THREE.InstancedBufferAttribute(endArr, 3));
        geo.setAttribute('aOffset', new THREE.InstancedBufferAttribute(offsetArr, 1));
        geo.setAttribute('aSpeed', new THREE.InstancedBufferAttribute(speedArr, 1));
        return geo;
    }, [startArr, midArr, endArr, offsetArr, speedArr]);

    useFrame((state) => {
        if (materialRef.current) {
            materialRef.current.uniforms.uTime.value = state.clock.getElapsedTime();
        }
    });

    return (
        <instancedMesh ref={meshRef} args={[geometry, undefined, count]}>
            <shaderMaterial
                ref={materialRef}
                vertexShader={packetVertexShader}
                fragmentShader={packetFragmentShader}
                uniforms={{
                    uTime: { value: 0 },
                    uColor: { value: new THREE.Color(color) }
                }}
                toneMapped={false}
            />
        </instancedMesh>
    );
}

// Connections Component with Data Packets
function ConnectionLines({ connections }: { connections: NetworkConnection[] }) {
    const { curves, pointsByCurve } = useMemo(() => {
        const curves = connections.map(conn => {
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

        return {
            curves,
            pointsByCurve: curves.map((curve) => curve.getPoints(40)),
        };
    }, [connections]);

    return (
        <group>
            {pointsByCurve.map((points, i) => {
                const conn = connections[i];
                const key = `${conn.from.lat},${conn.from.lng}-${conn.to.lat},${conn.to.lng}`;
                return (
                    // The static connection line
                    <Line
                        key={key}
                        points={points}
                        color="#00ffff"
                        lineWidth={0.5}
                        opacity={0.15}
                        transparent
                    />
                );
            })}
            
            {/* Animated packets traveling along the lines handled by GPU Instanced Shader */}
            <DataPackets curves={curves} color="#00ffff" speedBase={0.5} offsetBase={0} />
            <DataPackets curves={curves} color="#ff00ff" speedBase={0.3} offsetBase={0.5} />
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
                <meshStandardMaterial
                    color="#000000"
                    roughness={0.1}
                    metalness={0.8}
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
function ParallaxGroup({ children, activeNodeId, servers }: { children: React.ReactNode, activeNodeId?: string | null, servers?: NetworkServer[] }) {
    const group = useRef<THREE.Group>(null!);
    const activeServer = useMemo(
        () => (activeNodeId && servers ? servers.find((server) => server.id === activeNodeId) : undefined),
        [activeNodeId, servers],
    );

    useFrame((state, delta) => {
        const { pointer } = state;
        
        let targetRotX = -pointer.y * 0.2;
        let targetRotY = pointer.x * 0.2;

        // If a node is active, calculate its spherical angle and rotate the globe to face it
        if (activeServer) {
            const phi = (activeServer.lat) * (Math.PI / 180);
            const theta = (activeServer.lng) * (Math.PI / 180);

            targetRotX += phi;
            targetRotY += theta;
        }

        // Smoothly interpolate to the target rotation
        group.current.rotation.y = THREE.MathUtils.lerp(group.current.rotation.y, targetRotY, delta * 3);
        group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, targetRotX, delta * 3);
    });

    return <group ref={group}>{children}</group>;
}

export default function GlobalNetworkScene({ servers = DEFAULT_SERVERS, connections = DEFAULT_CONNECTIONS, activeNodeId }: GlobalNetworkSceneProps) {
    const { containerRef, host, setHostRef } = useCanvasHost<HTMLDivElement>();
    const isInView = useInView(containerRef, { margin: "100px" });
    const { dpr, monitorProps } = useAdaptiveSceneDpr({ initial: 1, min: 0.75, max: 1.25 });
    const serverPositions = useMemo(
        () => servers.map((server) => latLngToVector3(server.lat, server.lng, 2)),
        [servers],
    );

    return (
        <div ref={setHostRef} className="absolute inset-0 -z-10 bg-terminal-bg/0">
            {host ? (
                <Canvas
                    eventSource={host}
                    frameloop={isInView ? 'always' : 'never'}
                    performance={MARKETING_SCENE_CANVAS_PERFORMANCE}
                    camera={{ position: [0, 2, 7], fov: 40 }}
                    gl={MARKETING_SCENE_GL}
                    dpr={dpr}
                >
                    <ScenePerformanceMetrics sceneName="global-network" />
                    <PerformanceMonitor {...monitorProps} />
                    {/* Reduced fog density to ensure stars are visible */}
                    <fog attach="fog" args={['#050510', 5, 25]} />

                    {/* Environment for Glossy Reflections */}
                    <Environment preset="city" />

                    <ambientLight intensity={0.2} />
                    <pointLight position={[10, 10, 10]} color="#00ffff" intensity={1.5} />
                    <pointLight position={[-10, -5, -10]} color="#ff00ff" intensity={1} />

                    {/* Parallax Wrapper for Scene Content */}
                    <ParallaxGroup activeNodeId={activeNodeId} servers={servers}>
                        <ObsidianSphere />
                        <group rotation-y={0}>
                            <ServerNodes servers={servers} serverPositions={serverPositions} activeNodeId={activeNodeId} />
                            <ConnectionLines connections={connections} />
                        </group>
                    </ParallaxGroup>

                    <FloatingParticles count={400} />

                    <SafeEffectComposer enableNormalPass={false} multisampling={0}>
                        <Bloom luminanceThreshold={0.5} mipmapBlur intensity={0.5} radius={0.2} resolutionScale={0.5} />
                        <ChromaticAberration offset={CHROMATIC_ABERRATION_OFFSET} radialModulation={false} modulationOffset={0} />
                    </SafeEffectComposer>
                </Canvas>
            ) : null}
        </div>
    );
}
