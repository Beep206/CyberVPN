"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { type Texture } from "three";

// Shader to handle the explosion/re-assembly
const vertexShader = `
  uniform float uProgress;
  uniform float uTime;
  uniform vec2 uResolution;
  
  attribute vec3 aOffset; // Original position (grid)
  attribute vec2 aUv;     // UV for the texture mapping
  attribute float aRandom; // Random factor for each particle

  varying vec2 vUv;
  varying float vVisible;

  // Simple noise function
  float hash(float n) { return fract(sin(n) * 43758.5453123); }
  float noise(vec3 x) {
    vec3 p = floor(x);
    vec3 f = fract(x);
    f = f * f * (3.0 - 2.0 * f);
    float n = p.x + p.y * 57.0 + 113.0 * p.z;
    return mix(mix(mix(hash(n + 0.0), hash(n + 1.0), f.x),
                   mix(hash(n + 57.0), hash(n + 58.0), f.x), f.y),
               mix(mix(hash(n + 113.0), hash(n + 114.0), f.x),
                   mix(hash(n + 170.0), hash(n + 171.0), f.x), f.y), f.z);
  }

  void main() {
    vUv = aUv;
    
    // Calculate ease
    float t = uProgress; 
    // Ease out cubic
    float ease = 1.0 - pow(1.0 - t, 3.0);
    
    // Explode logic
    vec3 pos = position; // Local vertex position of the instance (the small cube)
    
    // Offset logic
    vec3 transformed = pos;
    
    // Initial position in the grid
    vec3 instancePos = aOffset;
    
    // Explosion direction based on randomness and noise
    float n = noise(vec3(instancePos.xy * 0.01, uTime * 0.1));
    
    // Random direction vector
    vec3 direction = vec3(
        (hash(aRandom * 12.0) - 0.5) * 2.0,
        (hash(aRandom * 45.0) - 0.5) * 2.0,
        (hash(aRandom * 99.0) - 0.5) * 2.0 // Z-depth for 3D feel
    );
    
    // Basic explosion movement
    float explosionStrength = 500.0; // Distance of explosion
    
    // Physics-like feel: some particles move faster
    float speed = 1.0 + aRandom * 2.0;
    
    // Apply movement
    // We want them to start at aOffset and move OUT when progress goes 0 -> 1
    // BUT user wants: "crumble into pixels... and then assemble back" 
    // So let's handle uProgress: 0 = assembled, 1 = exploded
    
    vec3 targetPos = instancePos + direction * explosionStrength * ease * speed;
    
    // Rotation during explosion
    float rotAngle = ease * 10.0 * aRandom;
    float c = cos(rotAngle);
    float s = sin(rotAngle);
    mat3 rotMat = mat3(
      c, -s, 0.0,
      s, c, 0.0,
      0.0, 0.0, 1.0
    );
    
    transformed = rotMat * transformed;
    
    // Add wave effect during start (inception wobble)
    float wave = sin(instancePos.y * 0.1 + uTime * 5.0) * (1.0 - ease) * 5.0 * t;
    targetPos.x += wave;

    // Final position
    vec3 finalPos = targetPos + transformed;
    
    gl_Position = projectionMatrix * modelViewMatrix * vec4(finalPos, 1.0);
    
    // Hide particles that go too far or handled by alpha
    vVisible = 1.0; 
  }
`;

const fragmentShader = `
  uniform sampler2D uTexture;
  uniform float uProgress;
  
  varying vec2 vUv;
  varying float vVisible;

  void main() {
    // Standard texture mapping
    vec4 color = texture2D(uTexture, vUv);
    
    // Fade out slightly at max explosion
    float alpha = color.a * (1.0 - uProgress * 0.2); 
    
    if (alpha < 0.1) discard;
    
    gl_FragColor = vec4(color.rgb, alpha);
  }
`;

interface CrumbleEffectProps {
    texture: Texture;
    width: number;
    height: number;
    progress: number; // 0 to 1
}

// Module-level factory — outside render, not analyzed by React Compiler
function generateCrumbleData(count: number, cols: number, rows: number, width: number, height: number, particleSize: number) {
    const offsets = new Float32Array(count * 3);
    const uvs = new Float32Array(count * 2);
    const randoms = new Float32Array(count);

    for (let i = 0; i < count; i++) {
        const col = i % cols;
        const row = Math.floor(i / cols);

        const x = (col * particleSize) - (width / 2) + (particleSize / 2);
        const y = -((row * particleSize) - (height / 2) + (particleSize / 2));

        offsets[i * 3 + 0] = x;
        offsets[i * 3 + 1] = y;
        offsets[i * 3 + 2] = 0;

        uvs[i * 2 + 0] = col / cols;
        uvs[i * 2 + 1] = 1.0 - (row / rows);

        randoms[i] = Math.random();
    }
    return { offsets, uvs, randoms };
}

export function CrumbleEffect({ texture, width, height, progress }: CrumbleEffectProps) {
    const meshRef = useRef<THREE.InstancedMesh>(null);
    const shaderRef = useRef<THREE.ShaderMaterial>(null);
    // Configuration
    const particleSize = 4; // Size of each "pixel" cube
    const cols = Math.floor(width / particleSize);
    const rows = Math.floor(height / particleSize);
    const count = cols * rows;

    const uniforms = useMemo(
        () => ({
            uTexture: { value: texture },
            uProgress: { value: 0 },
            uTime: { value: 0 },
            uResolution: { value: new THREE.Vector2(width, height) },
        }),
        [texture, width, height]
    );

    // Generate attributes — factory is module-level for purity
    const { offsets, uvs, randoms } = useMemo(
        () => generateCrumbleData(count, cols, rows, width, height, particleSize),
        [count, cols, rows, width, height, particleSize]
    );

    useFrame((state) => {
        if (shaderRef.current) {
            shaderRef.current.uniforms.uProgress.value = progress;
            shaderRef.current.uniforms.uTime.value = state.clock.elapsedTime;
        }
    });

    return (
        <instancedMesh ref={meshRef} args={[undefined, undefined, count]} position={[0, 0, 0]}>
            {/* Small Box Geometry for 3D pixel look */}
            <boxGeometry args={[particleSize, particleSize, particleSize]} >
                <instancedBufferAttribute attach="attributes-aOffset" args={[offsets, 3]} />
                <instancedBufferAttribute attach="attributes-aUv" args={[uvs, 2]} />
                <instancedBufferAttribute attach="attributes-aRandom" args={[randoms, 1]} />
            </boxGeometry>
            <shaderMaterial
                ref={shaderRef}
                uniforms={uniforms}
                vertexShader={vertexShader}
                fragmentShader={fragmentShader}
                transparent={true}
                side={THREE.DoubleSide}
            />
        </instancedMesh>
    );
}
