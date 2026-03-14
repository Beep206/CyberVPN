'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial, Float, Stars, Outlines } from '@react-three/drei';
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
  const materialRef = useRef<any>(null); // Type any for specific drei material props access if needed, handling safely via ref
  const groupRef = useRef<THREE.Group>(null);
  
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
        // Smoothly interpolate scale
        meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.05);
        // Rotate globe
        meshRef.current.rotation.y += delta * (targetSpeed * 0.2);
        meshRef.current.rotation.x += delta * (targetSpeed * 0.1);
    }

    if (materialRef.current) {
        // Smoothly interpolate material properties
        materialRef.current.distort = THREE.MathUtils.lerp(materialRef.current.distort, targetDistort, 0.05);
        materialRef.current.speed = THREE.MathUtils.lerp(materialRef.current.speed, targetSpeed, 0.05);
        materialRef.current.color.lerp(targetColor, 0.05);
        materialRef.current.emissive.lerp(targetColor, 0.05);
        // Pulse emissive intensity if encrypting
        if (isEncrypting) {
            materialRef.current.emissiveIntensity = 0.5 + Math.sin(state.clock.elapsedTime * 10) * 0.5;
        } else if (isSuccess) {
            materialRef.current.emissiveIntensity = THREE.MathUtils.lerp(materialRef.current.emissiveIntensity, 1.5, 0.1);
        } else {
            materialRef.current.emissiveIntensity = THREE.MathUtils.lerp(materialRef.current.emissiveIntensity, 0.2, 0.05);
        }
    }
    
    if (groupRef.current && isSuccess) {
        // Celebration floating burst
        groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 2) * 0.2;
    }
  });

  return (
    <group ref={groupRef}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#ff00ff" />
      
      <Stars radius={50} depth={50} count={isEncrypting ? 2000 : 1000} factor={4} saturation={0} fade speed={isEncrypting ? 3 : 1} />

      <Float speed={2} rotationIntensity={1} floatIntensity={isTyping ? 3 : 1}>
        {/* Core Sphere */}
        <Sphere ref={meshRef} args={[1.5, 64, 64]}>
          <MeshDistortMaterial
            ref={materialRef}
            color="#555555"
            emissive="#555555"
            emissiveIntensity={0.2}
            envMapIntensity={1}
            clearcoat={1}
            clearcoatRoughness={0.1}
            metalness={0.8}
            roughness={0.2}
            distort={0.2}
            speed={1}
            transparent
            opacity={0.9}
          />
          {/* Wireframe Outline for Cyberpunk Feel */}
          <Outlines thickness={0.02} color={targetColor} />
        </Sphere>
        
        {/* Outer orbital rings */}
        <mesh rotation-x={Math.PI / 2}>
            <ringGeometry args={[2.2, 2.22, 64]} />
            <meshBasicMaterial color={targetColor} transparent opacity={isTyping ? 0.3 : 0.1} side={THREE.DoubleSide} />
        </mesh>
        <mesh rotation-x={Math.PI / 3} rotation-y={Math.PI / 4}>
            <ringGeometry args={[2.6, 2.62, 64]} />
            <meshBasicMaterial color={targetColor} transparent opacity={isEncrypting ? 0.5 : 0.05} side={THREE.DoubleSide} />
        </mesh>
      </Float>
    </group>
  );
}
