import * as THREE from 'three';
import { extend } from '@react-three/fiber';
import { shaderMaterial } from '@react-three/drei';

// SUBTLE ATMOSPHERE
// Barely visible, just a hint of volumetric depth at the edges.

export const AtmosphereShader = shaderMaterial(
  {
    color: new THREE.Color(0.0, 1.0, 1.0),
    coefficient: 0.5,
    power: 6.0, // Very fast falloff
    intensity: 0.4, // Low intensity
  },
  // Vertex Shader
  `
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    void main() {
      vNormal = normalize(normalMatrix * normal);
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      vViewPosition = mvPosition.xyz;
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  // Fragment Shader
  `
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    
    uniform vec3 color;
    uniform float coefficient;
    uniform float power;
    uniform float intensity;

    void main() {
      vec3 viewDir = normalize(-vViewPosition);
      float viewDot = dot(viewDir, vNormal);
      float glow = pow(coefficient - viewDot, power);
      
      gl_FragColor = vec4(color, clamp(glow, 0.0, 1.0) * intensity);
    }
  `
);

extend({ AtmosphereShader });

declare global {
  namespace JSX {
    interface IntrinsicElements {
      atmosphereShader: any;
    }
  }
}
