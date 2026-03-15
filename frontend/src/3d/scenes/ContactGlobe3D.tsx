'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial, Float, Stars, Environment } from '@react-three/drei';
import * as THREE from 'three';
import { useTranslations } from 'next-intl';

interface ContactGlobe3DProps {
  isTyping: boolean;
  isEncrypting: boolean;
  isSuccess: boolean;
  isHoveringSubmit: boolean;
}

export function ContactGlobe3D({ isTyping, isEncrypting, isSuccess, isHoveringSubmit }: ContactGlobe3DProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<any>(null);
  const wireframeGlobeMatRef = useRef<any>(null);
  const groupRef = useRef<THREE.Group>(null);
  const wireframeMaterialRef = useRef<THREE.MeshBasicMaterial>(null);
  
  // Dynamic target values based on state
  const targetDistort = isSuccess ? 0.8 : isEncrypting ? 0.6 : isHoveringSubmit ? 0.5 : isTyping ? 0.4 : 0.2;
  const targetSpeed = isSuccess ? 10 : isEncrypting ? 8 : isHoveringSubmit ? 4 : isTyping ? 3 : 1;
  const targetScale = isSuccess ? 1.4 : isHoveringSubmit ? 1.1 : 1.0;
  
  const targetColor = useMemo(() => {
    if (isSuccess) return new THREE.Color('#00ffff'); // neon-cyan
    if (isEncrypting) return new THREE.Color('#ffb800'); // warning
    if (isHoveringSubmit) return new THREE.Color('#ff00ff'); // neon-pink
    if (isTyping) return new THREE.Color('#00ff88'); // matrix-green
    return new THREE.Color('#555555'); // Idle muted
  }, [isTyping, isEncrypting, isSuccess, isHoveringSubmit]);

  useFrame((state, delta) => {
    if (meshRef.current) {
        meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.05);
        meshRef.current.rotation.y += delta * (targetSpeed * 0.2);
        meshRef.current.rotation.x += delta * (targetSpeed * 0.1);
    }

    if (materialRef.current) {
        // Base dark sphere only changes distortion
        materialRef.current.distort = THREE.MathUtils.lerp(materialRef.current.distort, targetDistort, 0.05);
        materialRef.current.speed = THREE.MathUtils.lerp(materialRef.current.speed, targetSpeed, 0.05);
    }
    
    if (wireframeGlobeMatRef.current) {
        // Wireframe layer glows and matches distortion
        wireframeGlobeMatRef.current.distort = THREE.MathUtils.lerp(wireframeGlobeMatRef.current.distort, targetDistort, 0.05);
        wireframeGlobeMatRef.current.speed = THREE.MathUtils.lerp(wireframeGlobeMatRef.current.speed, targetSpeed, 0.05);
        
        wireframeGlobeMatRef.current.color.lerp(targetColor, 0.05);
        wireframeGlobeMatRef.current.emissive.lerp(targetColor, 0.05);
        
        if (isEncrypting) {
            wireframeGlobeMatRef.current.emissiveIntensity = 1.0 + Math.sin(state.clock.elapsedTime * 15) * 1.0;
            wireframeGlobeMatRef.current.opacity = 0.8;
        } else if (isSuccess) {
            wireframeGlobeMatRef.current.emissiveIntensity = THREE.MathUtils.lerp(wireframeGlobeMatRef.current.emissiveIntensity, 2.0, 0.1);
            wireframeGlobeMatRef.current.opacity = 1.0;
        } else if (isTyping) {
            wireframeGlobeMatRef.current.emissiveIntensity = 0.8 + Math.sin(state.clock.elapsedTime * 8) * 0.4;
            wireframeGlobeMatRef.current.opacity = 0.6;
        } else {
            wireframeGlobeMatRef.current.emissiveIntensity = THREE.MathUtils.lerp(wireframeGlobeMatRef.current.emissiveIntensity, 0.2, 0.05);
            wireframeGlobeMatRef.current.opacity = 0.2;
        }
    }

    if (wireframeMaterialRef.current) {
        wireframeMaterialRef.current.color.lerp(targetColor, 0.05);
        wireframeMaterialRef.current.opacity = isEncrypting ? 0.8 : isSuccess ? 1.0 : isTyping ? 0.5 : 0.2;
    }
    
    if (groupRef.current && isSuccess) {
        groupRef.current.position.y = THREE.MathUtils.lerp(groupRef.current.position.y, Math.sin(state.clock.elapsedTime * 2) * 0.2, 0.1);
    }
  });

  return (
    <group ref={groupRef}>
      <Environment preset="city" />
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#ff00ff" />
      
      <Stars radius={50} depth={50} count={isEncrypting ? 2000 : 1000} factor={4} saturation={0} fade speed={isEncrypting ? 3 : 1} />

      <Float speed={2} rotationIntensity={1} floatIntensity={isTyping ? 3 : 1}>
        {/* Core Base Sphere - Glossy obsidian black */}
        <Sphere ref={meshRef} args={[1.5, 64, 64]}>
          <MeshDistortMaterial
            ref={materialRef}
            color="#000000"
            emissive="#000000"
            emissiveIntensity={0}
            envMapIntensity={2}
            clearcoat={1}
            clearcoatRoughness={0.1}
            metalness={0.9}
            roughness={0.1}
            distort={0.2}
            speed={1}
          />
          {/* Internal Wireframe for Cyberpunk Structure */}
          <Sphere args={[1.505, 32, 32]}>
            <MeshDistortMaterial
               ref={wireframeGlobeMatRef}
               wireframe
               transparent
               distort={0.2}
               speed={1}
            />
          </Sphere>
        </Sphere>
        
        {/* Outer orbital rings */}
        <mesh rotation-x={Math.PI / 2}>
            <ringGeometry args={[2.2, 2.22, 64]} />
            <meshBasicMaterial ref={wireframeMaterialRef} color={targetColor} transparent opacity={isTyping || isEncrypting ? 0.8 : 0.2} side={THREE.DoubleSide} />
        </mesh>
        <mesh rotation-x={Math.PI / 3} rotation-y={Math.PI / 4}>
            <ringGeometry args={[2.6, 2.62, 64]} />
            <meshBasicMaterial color={targetColor} transparent opacity={isEncrypting ? 0.9 : 0.1} side={THREE.DoubleSide} />
        </mesh>
      </Float>
    </group>
  );
}
