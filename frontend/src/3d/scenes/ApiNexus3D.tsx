'use client';

import * as THREE from 'three';
import React, { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Text, PerformanceMonitor, Line, Float, CameraControls } from '@react-three/drei';
import { EffectComposer, Bloom, ChromaticAberration } from '@react-three/postprocessing';
import { ActiveEndpoint, EndpointCategory } from '@/widgets/api/api-dashboard';
import { useInView } from 'motion/react';

type NodeCategory = 'client' | 'gateway' | 'auth' | 'servers' | 'db';
type NodeId = 'client' | 'apiGate' | 'auth' | 'generateToken' | 'servers' | 'listServers' | 'connect' | 'dbAuth' | 'dbServers';

interface ApiNode {
    id: NodeId;
    label: string;
    category: NodeCategory;
    pos: [number, number, number];
}

interface ApiEdge {
    source: NodeId;
    target: NodeId;
    flowDirection: 1 | -1 | 0; // 1: forward, -1: backward, 0: bidirectional
}

export const API_NODES: ApiNode[] = [
    { id: 'client', label: 'Client App', category: 'client', pos: [0, 4, 0] },
    { id: 'apiGate', label: 'API Gateway', category: 'gateway', pos: [0, 0, -2] },
    
    // Auth Auth
    { id: 'auth', label: 'Auth Service', category: 'auth', pos: [-4, -2, -4] },
    { id: 'generateToken', label: 'POST /auth/token', category: 'auth', pos: [-6, -4, -3] },
    { id: 'dbAuth', label: 'Users DB', category: 'db', pos: [-5, -6, -6] },
    
    // Servers
    { id: 'servers', label: 'Servers Service', category: 'servers', pos: [4, -2, -4] },
    { id: 'listServers', label: 'GET /servers', category: 'servers', pos: [5, -4, -2] },
    { id: 'connect', label: 'POST /servers/connect', category: 'servers', pos: [7, -4, -4] },
    { id: 'dbServers', label: 'Nodes DB', category: 'db', pos: [5, -6, -6] },
];

export const API_EDGES: ApiEdge[] = [
    { source: 'client', target: 'apiGate', flowDirection: 1 },
    { source: 'apiGate', target: 'auth', flowDirection: 1 },
    { source: 'apiGate', target: 'servers', flowDirection: 1 },
    { source: 'auth', target: 'generateToken', flowDirection: 1 },
    { source: 'auth', target: 'dbAuth', flowDirection: 0 },
    { source: 'servers', target: 'listServers', flowDirection: 1 },
    { source: 'servers', target: 'connect', flowDirection: 1 },
    { source: 'servers', target: 'dbServers', flowDirection: 0 },
];

const getCategoryColor = (cat: EndpointCategory) => {
    switch (cat) {
        case 'auth': return '#ff00ff';     // Neon Pink
        case 'servers': return '#00ff88';  // Matrix Green
        default: return '#00ffff';         // Cyan Default
    }
};

// --- 1. DataFlow (Packets) ---
function DataFlow({ edges, activeEndpoint }: { edges: ApiEdge[], activeEndpoint: ActiveEndpoint }) {
    const meshRef = useRef<THREE.InstancedMesh>(null!);
    const materialRef = useRef<THREE.MeshBasicMaterial>(null!);
    const dummy = useMemo(() => new THREE.Object3D(), []);
    
    const packetCount = 200;
    
    const packets = useMemo(() => {
        return new Array(packetCount).fill(0).map(() => {
            const edge = edges[Math.floor(Math.random() * edges.length)];
            const source = API_NODES.find(n => n.id === edge.source)!;
            const target = API_NODES.find(n => n.id === edge.target)!;
            
            return {
                start: new THREE.Vector3(...source.pos),
                end: new THREE.Vector3(...target.pos),
                progress: Math.random(),
                speed: 0.3 + Math.random() * 0.5,
                offset: Math.random() * Math.PI * 2
            };
        });
    }, [edges]);

    const activeColor = getCategoryColor(activeEndpoint.category);

    useFrame((state, delta) => {
        if (!meshRef.current) return;
        
        const time = state.clock.getElapsedTime();
        // Speed up particles based on the category (just for wow factor variation)
        const speedMultiplier = activeEndpoint.category === 'auth' ? 1.5 : 1.2;

        packets.forEach((p, i) => {
            p.progress += delta * (p.speed * speedMultiplier);
            if (p.progress > 1) {
                p.progress = 0;
            }

            // Interpolate position
            const pos = new THREE.Vector3().copy(p.start).lerp(p.end, p.progress);
            
            // Add sine wave jitter
            pos.x += Math.sin(time * 10.0 + p.offset) * 0.05;
            pos.y += Math.cos(time * 12.0 + p.offset) * 0.05;

            dummy.position.copy(pos);
            
            // Orient packet along path
            if (pos.distanceTo(p.end) > 0.01) {
                dummy.lookAt(p.end);
            }
            
            dummy.updateMatrix();
            meshRef.current.setMatrixAt(i, dummy.matrix);
        });
        
        meshRef.current.instanceMatrix.needsUpdate = true;
        
        // Dynamically morph color
        if (materialRef.current) {
            const alphaColor = 1 - Math.exp(-2.0 * delta); // Safe exponential lerp
            materialRef.current.color.lerp(new THREE.Color(activeColor), alphaColor);
        }
    });

    return (
        <instancedMesh ref={meshRef} args={[new THREE.BoxGeometry(0.04, 0.04, 0.2), undefined, packetCount]}>
            <meshBasicMaterial 
                ref={materialRef} 
                color="#00ffff"
                transparent
                opacity={0.8}
                blending={THREE.AdditiveBlending}
                depthWrite={false}
                toneMapped={false}
            />
        </instancedMesh>
    );
}

// --- 2. The Nodes (Cubes) ---
function GraphNodes({ nodes, activePath, activeEndpoint }: { nodes: ApiNode[], activePath: NodeId[], activeEndpoint: ActiveEndpoint }) {
    const materialRef = useRef<THREE.MeshStandardMaterial>(null!);
    
    useFrame((state) => {
        if (materialRef.current) {
            materialRef.current.emissiveIntensity = 0.5 + Math.sin(state.clock.elapsedTime * 2) * 0.3;
        }
    });

    const activeColor = getCategoryColor(activeEndpoint.category);
    
    return (
        <group>
            {nodes.map((node) => {
                const isActive = activePath.includes(node.id);
                // The targeted active node gets the category color, while the inactive ones fade back to gray
                const color = isActive ? activeColor : "#444455";
                const scale = isActive ? 1.2 : 0.8;

                return (
                    <group key={node.id} position={node.pos}>
                        {/* Main Cube */}
                        <mesh scale={scale}>
                            <boxGeometry args={[0.5, 0.5, 0.5]} />
                            <meshStandardMaterial 
                                color={color} 
                                emissive={color}
                                emissiveIntensity={isActive ? 0.8 : 0.2}
                                roughness={0.2}
                                metalness={0.8}
                                wireframe={!isActive}
                            />
                        </mesh>

                        {/* Node Label */}
                        <Text
                            position={[0, 0.6 * scale, 0]}
                            fontSize={isActive ? 0.3 : 0.2}
                            color={isActive ? activeColor : "#888899"}
                            anchorX="center"
                            anchorY="bottom"
                        >
                            {node.label}
                        </Text>
                        
                        {/* Glowing core for active nodes */}
                        {isActive && (
                            <mesh scale={scale * 0.5}>
                                <sphereGeometry args={[0.3, 16, 16]} />
                                <meshBasicMaterial color="#ffffff" transparent opacity={0.6} blending={THREE.AdditiveBlending} depthWrite={false} toneMapped={false} />
                            </mesh>
                        )}
                    </group>
                );
            })}
        </group>
    );
}

// --- 3. The Edges (Lines) ---
function GraphEdges({ edges, activePath, activeEndpoint }: { edges: ApiEdge[], activePath: NodeId[], activeEndpoint: ActiveEndpoint }) {
    const activeColor = getCategoryColor(activeEndpoint.category);

    return (
        <group>
            {edges.map((edge, i) => {
                const sourceNode = API_NODES.find(n => n.id === edge.source)!;
                const targetNode = API_NODES.find(n => n.id === edge.target)!;
                
                const isActive = activePath.includes(edge.source) && activePath.includes(edge.target);
                
                const points = [
                    new THREE.Vector3(...sourceNode.pos),
                    new THREE.Vector3(...targetNode.pos)
                ];

                return (
                    <Line 
                        key={i}
                        points={points}
                        color={isActive ? activeColor : "#333344"}
                        transparent
                        opacity={isActive ? 0.8 : 0.2}
                        lineWidth={isActive ? 3 : 1}
                    />
                );
            })}
        </group>
    );
}

// --- Inner Scene Component ---
function SceneContent({ activePath, activeEndpoint }: { activePath: NodeId[], activeEndpoint: ActiveEndpoint }) {
    const activeColor = getCategoryColor(activeEndpoint.category);
    const controlsRef = useRef<any>(null);

    useEffect(() => {
        if (!controlsRef.current) return;
        
        const targetNodeId = activePath[activePath.length - 1];
        const targetNode = API_NODES.find(n => n.id === targetNodeId);
        
        if (targetNode) {
            const [tx, ty, tz] = targetNode.pos;
            
            const pannedX = THREE.MathUtils.clamp(tx * 0.4, -2.5, 2.5);
            const pannedY = THREE.MathUtils.clamp(ty * 0.2 + 2, 1, 4);
            const pannedZ = THREE.MathUtils.clamp(tz * 0.5 + 8, 8, 14);

            const lookX = THREE.MathUtils.clamp(tx * 0.2, -1.5, 1.5);
            
            // setLookAt( camX, camY, camZ, lookX, lookY, lookZ, animated )
            controlsRef.current.setLookAt(
                pannedX, pannedY, pannedZ,
                lookX, ty * 0.2 - 1, tz * 0.3 + 1,
                true
            );
        }
    }, [activePath]);

    return (
        <group>
            <color attach="background" args={['#020205']} />
            <fog attach="fog" args={['#020205', 5, 20]} />

            <ambientLight intensity={0.5} />
            <pointLight position={[0, 5, 0]} intensity={2} color={activeColor} />
            
            <CameraControls 
                ref={controlsRef} 
                makeDefault 
                smoothTime={0.5} 
                draggingSmoothTime={0.2}
            />

            <group position={[0, -1, 0]}>
                <Float speed={1.5} rotationIntensity={0.1} floatIntensity={0.5}>
                    <GraphEdges edges={API_EDGES} activePath={activePath} activeEndpoint={activeEndpoint} />
                    <GraphNodes nodes={API_NODES} activePath={activePath} activeEndpoint={activeEndpoint} />
                    <DataFlow edges={API_EDGES} activeEndpoint={activeEndpoint} />
                </Float>
                <gridHelper args={[40, 40, activeColor, '#111122']} position={[0, -4, 0]} material-transparent material-opacity={0.15} />
            </group>
            
            <EffectComposer enableNormalPass={false} multisampling={0}>
                <Bloom luminanceThreshold={0.2} mipmapBlur intensity={1.5} />
                <ChromaticAberration offset={new THREE.Vector2(0.002, 0.002)} radialModulation={false} modulationOffset={0} />
            </EffectComposer>
        </group>
    );
}

// --- Main Export ---
interface ApiNexus3DProps {
    activeEndpoint: ActiveEndpoint;
}

export default function ApiNexus3D({ activeEndpoint }: ApiNexus3DProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [dpr, setDpr] = useState(1);
    
    const activePath = useMemo(() => {
        const path: NodeId[] = ['client', 'apiGate'];
        if (activeEndpoint.category === 'auth') {
            path.push('auth');
            if (activeEndpoint.id === 'generateToken') path.push('generateToken');
        } else if (activeEndpoint.category === 'servers') {
            path.push('servers');
            if (activeEndpoint.id === 'listServers') path.push('listServers');
            if (activeEndpoint.id === 'connect') path.push('connect');
        }
        return path;
    }, [activeEndpoint]);

    return (
        <div ref={containerRef} className="absolute inset-x-0 inset-y-0 w-full h-full pointer-events-none">
            <Canvas
                camera={{ position: [0, 2, 10], fov: 45 }}
                performance={{ min: 0.5 }}
                gl={{
                    antialias: false,
                    alpha: true,
                    powerPreference: "high-performance",
                }}
                dpr={dpr}
            >
                <PerformanceMonitor onDecline={() => setDpr(0.75)} onIncline={() => setDpr(1)} />
                <React.Suspense fallback={null}>
                    <SceneContent activePath={activePath} activeEndpoint={activeEndpoint} />
                </React.Suspense>
            </Canvas>
        </div>
    );
}
