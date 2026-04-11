import * as THREE from 'three';
import { extend } from '@react-three/fiber';
import { shaderMaterial } from '@react-three/drei';

export const AntiDPIShader = shaderMaterial(
  {
    time: 0,
    uScannerPos: 0.0,
    uBoundMinX: -5.0,
    uBoundMaxX: 5.0,
    colorRaw: new THREE.Color(1.0, 0.0, 0.4), 
    colorClean: new THREE.Color(0.0, 1.0, 1.0), 
    displacementRaw: 0.08, // Significantly reduced
    rimPower: 4.0,
    rimIntensity: 2.0,
  },
  // Vertex Shader
  `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    varying float vState;
    
    uniform float time;
    uniform float uScannerPos;
    uniform float uBoundMinX;
    uniform float uBoundMaxX;
    uniform float displacementRaw;

    attribute vec3 aOffset;
    attribute vec3 aSpeed;

    void main() {
      vUv = uv;
      
      float range = uBoundMaxX - uBoundMinX;
      float currentX = uBoundMinX + mod(aOffset.x - uBoundMinX + time * aSpeed.x, range);
      
      vState = smoothstep(uScannerPos - 0.2, uScannerPos + 0.2, currentX);
      
      vec3 pos = position;
      
      // SUPER SMOOTH organic "breathing" instead of sum of sines
      float id = float(gl_InstanceID);
      float breathe = sin(time * 1.2 + id * 0.5) * 0.5 + 0.5;
      float wave = breathe * (1.0 - vState) * displacementRaw;
      pos += normal * wave;
      
      // Fixed scale - smaller and more consistent
      pos *= aSpeed.y * 0.8;
      
      // Very slow rotation
      float angle = time * 0.2 + aSpeed.z;
      float s = sin(angle);
      float c = cos(angle);
      mat3 rotY = mat3(c, 0.0, s, 0.0, 1.0, 0.0, -s, 0.0, c);
      pos = rotY * pos;
      
      vec3 worldPos = pos + vec3(currentX, aOffset.y + sin(time * 0.8 + aSpeed.z) * 0.2, aOffset.z);
      
      vNormal = normalize(normalMatrix * (rotY * normal));
      vec4 mvPosition = viewMatrix * modelMatrix * vec4(worldPos, 1.0);
      vViewPosition = mvPosition.xyz;
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  // Fragment Shader
  `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    varying float vState;

    uniform vec3 colorRaw;
    uniform vec3 colorClean;
    uniform float time;
    uniform float rimPower;
    uniform float rimIntensity;

    void main() {
      vec3 baseColor = mix(colorRaw, colorClean, vState);
      
      vec3 viewDir = normalize(-vViewPosition);
      float rim = pow(1.0 - max(0.0, dot(viewDir, vNormal)), rimPower);
      
      // Gentle pulse
      float pulse = 0.9 + sin(time * 2.0 + vViewPosition.x) * 0.1;
      
      vec3 finalColor = baseColor * (0.6 + rim * rimIntensity * pulse);
      
      float core = 1.0 - length(vUv - 0.5) * 2.2;
      finalColor += baseColor * max(0.0, core) * 0.4;

      float alpha = (rim * 0.7 + max(0.0, core) * 0.4) * mix(1.0, 0.6, vState);

      gl_FragColor = vec4(finalColor, alpha);
    }
  `
);

extend({ AntiDPIShader });
