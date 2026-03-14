import * as THREE from 'three';
import { extend } from '@react-three/fiber';
import { shaderMaterial } from '@react-three/drei';

export const FastTrackShader = shaderMaterial(
  {
    time: 0,
    colorPrimary: new THREE.Color('#00ffff'),
    colorSecondary: new THREE.Color('#00ff41'),
    hubPosition: new THREE.Vector3(0, 0, 0),
  },
  // Vertex Shader
  `
    varying vec2 vUv;
    varying float vProgress;
    varying vec3 vColor;

    uniform float time;
    uniform vec3 colorPrimary;
    uniform vec3 colorSecondary;

    // Instance attributes for Cubic Bezier Control Points
    attribute vec3 aP0;
    attribute vec3 aP1;
    attribute vec3 aP2;
    attribute vec3 aP3;
    
    // x: speed, y: offset, z: scale_radius, w: scale_length
    attribute vec4 aParams;
    // Base color for this specific instance to mix with uniforms
    attribute vec3 aColorMix;

    vec3 bezier(float t, vec3 p0, vec3 p1, vec3 p2, vec3 p3) {
      float u = 1.0 - t;
      float tt = t * t;
      float uu = u * u;
      float uuu = uu * u;
      float ttt = tt * t;

      vec3 p = uuu * p0;
      p += 3.0 * uu * t * p1;
      p += 3.0 * u * tt * p2;
      p += ttt * p3;
      return p;
    }

    vec3 bezierDerivative(float t, vec3 p0, vec3 p1, vec3 p2, vec3 p3) {
      float u = 1.0 - t;
      float tt = t * t;
      float uu = u * u;
      
      vec3 dp = 3.0 * uu * (p1 - p0);
      dp += 6.0 * u * t * (p2 - p1);
      dp += 3.0 * tt * (p3 - p2);
      return dp;
    }

    // (Removed unused rotationMatrix function)

    void main() {
      vUv = uv;
      
      float speed = aParams.x;
      float offset = aParams.y;
      float scaleRadius = aParams.z;
      // Multiply by speed to create "Speed Stretching" effect
      float scaleLength = aParams.w + (speed * 0.5); 
      
      // Calculate normalized time [0, 1]
      float t = fract(time * speed + offset);
      vProgress = t; // Pass to fragment for alpha fading

      // Blend instance color with uniform colors based on aColorMix
      vColor = mix(colorPrimary, colorSecondary, aColorMix.r);
      vColor = mix(vColor, vec3(1.0), aColorMix.g); // Sometimes white-ish for super fast ones
      
      // Geometry is assumed to be a Cylinder/Capsule aligned along the Y or Z axis.
      // Let's assume base geometry is along Y. We scale it.
      vec3 localPos = position;
      localPos.x *= scaleRadius;
      localPos.y *= scaleLength; // Stretch along Y axis
      localPos.z *= scaleRadius;
      
      // Calculate path position and direction
      vec3 pathPos = bezier(t, aP0, aP1, aP2, aP3);
      vec3 pathDir = normalize(bezierDerivative(t, aP0, aP1, aP2, aP3));
      
      // We want to orient the cylinder's Y axis to pathDir
      vec3 fw = pathDir;
      vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), fw));
      // Fallback if direction is exactly up/down
      if (length(right) < 0.001) {
          right = vec3(1.0, 0.0, 0.0);
      }
      vec3 up = cross(fw, right);
      
      // For a geometry oriented along Y-axis, we want its local Y to map to fw
      // So local X -> right, local Y -> fw, local Z -> up
      vec3 orientedPos = localPos.x * right + localPos.y * fw + localPos.z * up;
      
      // Add path position
      vec3 worldPosition = pathPos + orientedPos;

      // Apply standard instance transformation matrix (if any base transform from the instancedMesh)
      vec4 mvPosition = viewMatrix * modelMatrix * instanceMatrix * vec4(worldPosition, 1.0);
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  // Fragment Shader
  `
    varying vec2 vUv;
    varying float vProgress;
    varying vec3 vColor;

    uniform float time;

    void main() {
      // Create motion blur effect.
      float alpha = smoothstep(0.0, 0.4, vUv.y) * (1.0 - smoothstep(0.8, 1.0, vUv.y));
      
      // Fading out as it hits the hub (vProgress -> 1) and fading in as it spawns (vProgress -> 0)
      float pathAlpha = smoothstep(0.0, 0.05, vProgress) * (1.0 - smoothstep(0.9, 1.0, vProgress));
      
      // Add some noise or energy pulsing
      float pulse = 0.8 + 0.2 * sin(vUv.y * 20.0 - time * 10.0);

      // Core is bright white, edges are colored
      float core = smoothstep(0.5, 0.8, sin(vUv.x * 3.14159));
      vec3 finalColor = mix(vColor * 0.5, vColor * 2.0 + vec3(1.0), core) * pulse;

      // Output with emissive power
      gl_FragColor = vec4(finalColor, alpha * pathAlpha);
    }
  `
);

export const HubShader = shaderMaterial(
  {
    time: 0,
    colorBase: new THREE.Color('#00ffff'),
    colorGlow: new THREE.Color('#00ff41'),
  },
  `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    
    uniform float time;

    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      vec4 mvPosition = viewMatrix * modelMatrix * vec4(position, 1.0);
      vViewPosition = mvPosition.xyz;
      
      // Pulse animation in vertex scale
      float pulse = sin(time * 3.0) * 0.05;
      vec3 pos = position + normal * pulse;
      gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(pos, 1.0);
    }
  `,
  `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    
    uniform float time;
    uniform vec3 colorBase;
    uniform vec3 colorGlow;

    void main() {
      vec3 viewDir = normalize(-vViewPosition);
      float fresnel = pow(1.0 - max(0.0, dot(viewDir, vNormal)), 3.0);
      
      float pulse = 0.5 + 0.5 * sin(time * 5.0);
      
      // Core pattern
      float pattern = sin(vUv.y * 50.0 - time * 2.0) * 0.5 + 0.5;
      vec3 color = mix(colorBase, colorGlow, fresnel + pattern * 0.5);
      
      gl_FragColor = vec4(color * (1.0 + pulse * fresnel * 2.0), 0.9);
    }
  `
);

extend({ FastTrackShader, HubShader });
