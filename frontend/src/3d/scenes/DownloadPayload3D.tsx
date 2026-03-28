import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Environment, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { EffectComposer, Bloom, ChromaticAberration, Noise } from '@react-three/postprocessing';
import { OSPlatform } from '@/widgets/download/download-dashboard';

interface PayloadProps {
    selectedOS: OSPlatform;
}

// OS Config mappings for 3D state switching
const OS_CONFIGS = {
    none: { color: new THREE.Color('#ffffff'), wireframe: true, form: 'icosahedron', speed: 0.5, scale: 0.8 },
    windows: { color: new THREE.Color('#00ffff'), wireframe: false, form: 'box', speed: 1.0, scale: 1.2 },
    macos: { color: new THREE.Color('#ffffff'), wireframe: false, form: 'torus', speed: 0.2, scale: 1.1 },
    linux: { color: new THREE.Color('#ffb800'), wireframe: true, form: 'octahedron', speed: 2.0, scale: 1.0 },
    ios: { color: new THREE.Color('#a0a0a0'), wireframe: false, form: 'sphere', speed: 0.8, scale: 0.9 },
    android: { color: new THREE.Color('#00ff88'), wireframe: false, form: 'cylinder', speed: 1.5, scale: 1.0 },
};

function AnimatedPayloadCore({ selectedOS }: PayloadProps) {
    const coreRef = useRef<THREE.Mesh>(null!);
    const materialRef = useRef<THREE.MeshStandardMaterial>(null!);
    const ring1MaterialRef = useRef<THREE.MeshBasicMaterial>(null!);
    const ring2MaterialRef = useRef<THREE.MeshBasicMaterial>(null!);
    const config = OS_CONFIGS[selectedOS];

    // Track current interpolated values
    const currentScale = useRef(config.scale);
    const currentColor = useRef(config.color.clone());

    useFrame((state, delta) => {
        if (!coreRef.current || !materialRef.current) return;

        // Rotate
        coreRef.current.rotation.x += delta * config.speed;
        coreRef.current.rotation.y += delta * (config.speed * 0.8);

        // Interpolate scale
        currentScale.current = THREE.MathUtils.lerp(currentScale.current, config.scale, delta * 5);
        coreRef.current.scale.set(currentScale.current, currentScale.current, currentScale.current);

        // Interpolate color properties
        currentColor.current.lerp(config.color, delta * 5);
        materialRef.current.color.copy(currentColor.current);
        materialRef.current.emissive.copy(currentColor.current);
        
        if (ring1MaterialRef.current) ring1MaterialRef.current.color.copy(currentColor.current);
        if (ring2MaterialRef.current) ring2MaterialRef.current.color.copy(currentColor.current);

        // Interpolate opacity/intensity based on selectedOS
        const targetEmissive = selectedOS === 'none' ? 0.2 : 0.8;
        materialRef.current.emissiveIntensity = THREE.MathUtils.lerp(materialRef.current.emissiveIntensity, targetEmissive, delta * 5);
        
        const targetOpacity = config.wireframe ? 0.4 : 0.9;
        materialRef.current.opacity = THREE.MathUtils.lerp(materialRef.current.opacity, targetOpacity, delta * 5);
        materialRef.current.wireframe = config.wireframe;
    });

    return (
        <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
            <mesh ref={coreRef}>
                {config.form === 'icosahedron' && <icosahedronGeometry args={[2, 0]} />}
                {config.form === 'box' && <boxGeometry args={[2.5, 2.5, 2.5]} />}
                {config.form === 'torus' && <torusKnotGeometry args={[1.5, 0.4, 128, 32]} />}
                {config.form === 'octahedron' && <octahedronGeometry args={[2.5, 0]} />}
                {config.form === 'sphere' && <sphereGeometry args={[2, 32, 32]} />}
                {config.form === 'cylinder' && <cylinderGeometry args={[1.5, 1.5, 3, 32]} />}

                <meshStandardMaterial
                    ref={materialRef}
                    roughness={0.1}
                    metalness={0.9}
                    transparent
                />
            </mesh>

            {/* Orbiting data rings */}
            <mesh rotation={[Math.PI / 3, 0, 0]}>
                <torusGeometry args={[4, 0.01, 16, 100]} />
                <meshBasicMaterial ref={ring1MaterialRef} transparent opacity={0.3} />
            </mesh>
            <mesh rotation={[-Math.PI / 4, Math.PI / 2, 0]}>
                <torusGeometry args={[4.5, 0.02, 16, 100]} />
                <meshBasicMaterial ref={ring2MaterialRef} transparent opacity={0.1} />
            </mesh>
        </Float>
    );
}

// Background environment grid
function ScannerGrid() {
    const gridRef = useRef<THREE.GridHelper>(null!);

    useFrame((state) => {
        if (gridRef.current) {
            gridRef.current.position.z = (state.clock.elapsedTime * 2) % 1; // Rolling forward effect
        }
    });

    return (
        <group position={[0, -4, 0]}>
            <gridHelper 
                ref={gridRef}
                args={[50, 50]} 
                material-opacity={0.2}
                material-transparent
            />
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
                <planeGeometry args={[50, 50]} />
                <meshBasicMaterial color="#000000" transparent opacity={0.8} />
            </mesh>
        </group>
    );
}

export function DownloadPayload3D({ selectedOS }: PayloadProps) {
    return (
        <Canvas
            camera={{ position: [5, 2, 10], fov: 45 }}
            gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
        >
            <fog attach="fog" args={['#000000', 5, 20]} />
            <Environment preset="city" />
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1} />

            <AnimatedPayloadCore selectedOS={selectedOS} />
            <ScannerGrid />
            
            {/* Gentle camera sway, limited to prevent dizzying */}
            <OrbitControls 
                enableZoom={false} 
                enablePan={false}
                autoRotate 
                autoRotateSpeed={selectedOS === 'none' ? 0.5 : 2.0} 
                maxPolarAngle={Math.PI / 2 + 0.1} 
                minPolarAngle={Math.PI / 2 - 0.5}
            />

            <EffectComposer enableNormalPass={false}>
                <Bloom luminanceThreshold={0.2} mipmapBlur intensity={1.5} />
                <Noise opacity={0.02} />
                <ChromaticAberration offset={new THREE.Vector2(0.002, 0.002)} />
            </EffectComposer>
        </Canvas>
    );
}
