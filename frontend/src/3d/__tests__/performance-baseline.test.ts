/**
 * Performance Regression Tests for CyberVPN 3D Components
 *
 * These tests verify that key 3D scene components maintain performance
 * characteristics and don't regress in quality:
 *
 * 1. Module exports (components exist and are functions)
 * 2. Static configuration constants are hoisted (not recreated per render)
 * 3. Particle counts stay within baseline limits
 * 4. Canvas configurations use performance-optimized settings
 *
 * Note: These are static/structural tests. WebGL rendering tests belong in E2E.
 */
import { describe, it, expect, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks (inline for hoisting)
// ---------------------------------------------------------------------------
vi.mock('three', () => {
  function C() {
    return {
      x: 0, y: 0, z: 0,
      set() { return this; },
      copy() { return this; },
      clone() { return this; },
      normalize() { return this; },
      multiplyScalar() { return this; },
      add() { return this; },
      sub() { return this; },
      cross() { return this; },
      getPoints() { return []; },
      toArray() { return [0,0,0]; },
      setAttribute() {},
      makeRotationFromEuler() { return this; },
      compose() { return this; },
      moveTo() { return this; },
      lineTo() { return this; },
      closePath() { return this; },
      extractPoints() { return { shape: [], holes: [] }; },
      addVectors() { return this; },
      getPoint() { return this; },
      setScalar() { return this; },
      setHSL() { return this; },
      setHex() { return this; },
      updateMatrix() {},
      setMatrixAt() {},
    };
  }
  return {
    __esModule: true,
    Object3D: C, Vector2: C, Vector3: C, Color: C, Matrix4: C, Euler: C, Quaternion: C,
    Shape: C, ExtrudeGeometry: C, ShapeGeometry: C, WireframeGeometry: C,
    CatmullRomCurve3: C, CubicBezierCurve3: C, LineCurve3: C, QuadraticBezierCurve3: C,
    Float32BufferAttribute: C, BufferGeometry: C, BufferAttribute: C,
    ShaderMaterial: C, MeshBasicMaterial: C, MeshStandardMaterial: C, MeshPhysicalMaterial: C,
    SphereGeometry: C, IcosahedronGeometry: C, BoxGeometry: C, PlaneGeometry: C,
    CylinderGeometry: C, TorusGeometry: C, RingGeometry: C, TubeGeometry: C,
    CircleGeometry: C, DodecahedronGeometry: C,
    InstancedMesh: C, Group: C, Mesh: C, Line: C, LineSegments: C, Points: C,
    Scene: C, Clock: C, Raycaster: C, TextureLoader: C, WebGLRenderer: C,
    PerspectiveCamera: C, AmbientLight: C, PointLight: C, DirectionalLight: C,
    SpotLight: C, HemisphereLight: C, Fog: C, FogExp2: C,
    Sprite: C, SpriteMaterial: C, CanvasTexture: C, Texture: C,
    DoubleSide: 2, FrontSide: 0, BackSide: 1, AdditiveBlending: 2, NormalBlending: 1,
    LinearFilter: 1006, ClampToEdgeWrapping: 1001,
    MathUtils: {
      lerp: (a: number, b: number, t: number) => a + (b - a) * t,
      degToRad: (d: number) => d * 0.01745,
      clamp: (v: number) => v
    },
  };
});

vi.mock('@react-three/fiber', async () => {
  const React = await import('react');
  return {
    Canvas: ({ children, ...props }: Record<string, unknown>) =>
      React.createElement('div', { 'data-testid': 'r3f-canvas', ...props }, children),
    useFrame: () => {},
    useThree: () => ({
      pointer: { x: 0, y: 0 },
      size: { width: 800, height: 600 },
      clock: { getElapsedTime: () => 0, getDelta: () => 0.016 },
      camera: {},
      gl: {},
      scene: {},
    }),
    extend: () => {},
  };
});

vi.mock('@react-three/drei', () => ({
  __esModule: true,
  Line: () => null,
  Sphere: () => null,
  Icosahedron: () => null,
  OrbitControls: () => null,
  Trail: () => null,
  Environment: () => null,
  Float: () => null,
  MeshDistortMaterial: () => null,
  MeshWobbleMaterial: () => null,
  MeshTransmissionMaterial: () => null,
  Sparkles: () => null,
  Stars: () => null,
  GradientTexture: () => null,
  shaderMaterial: () => null,
}));

vi.mock('@react-three/postprocessing', () => ({
  __esModule: true,
  EffectComposer: () => null,
  Bloom: () => null,
  ChromaticAberration: () => null,
  ToneMapping: () => null,
  Noise: () => null,
  Vignette: () => null,
}));

vi.mock('@/3d/shaders/AtmosphereShader', () => ({ AtmosphereShader: null }));
vi.mock('@/3d/shaders/CyberSphereShader', () => ({}));
vi.mock('@/3d/shaders/CyberSphereShaderV2', () => ({}));

// ---------------------------------------------------------------------------
// Performance Baseline Constants
// ---------------------------------------------------------------------------
const PERFORMANCE_BASELINES = {
  // Particle count limits (from scene analysis)
  GlobalNetwork: {
    maxParticles: 2000,
    defaultParticles: 2000,
  },
  AuthScene3D: {
    maxParticles: 500,
    defaultParameterValue: 500, // Default parameter in SecurityParticles function signature
    instantiatedValue: 400,     // Actual value used in scene
  },
  FeaturesScene3D: {
    maxParticles: 800,
    defaultParameterValue: 800, // Default parameter in CyberParticles function signature
    instantiatedValue: 600,     // Actual value used in scene
  },

  // Canvas settings that must be present for performance
  requiredCanvasSettings: {
    dpr: true, // Device pixel ratio should be capped
    gl: true,  // GL options should be configured
  },

  // GL performance settings
  performanceGLSettings: {
    powerPreference: 'high-performance',
    alpha: true,
  },
} as const;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('3D Performance Regression Tests', () => {
  describe('Module Exports', () => {
    it('GlobalNetworkScene exports a function', async () => {
      const globalNetworkModule = await import('@/3d/scenes/GlobalNetwork');
      expect(typeof globalNetworkModule.default).toBe('function');
      expect(globalNetworkModule.default.name).toBe('GlobalNetworkScene');
    });

    it('AuthScene3D exports a function', async () => {
      const authSceneModule = await import('@/3d/scenes/AuthScene3D');
      expect(typeof authSceneModule.AuthScene3D).toBe('function');
    });

    it('FeaturesScene3D exports functions', async () => {
      const featuresModule = await import('@/3d/scenes/FeaturesScene3D');
      expect(typeof featuresModule.FeaturesScene3D).toBe('function');
      expect(typeof featuresModule.FeaturesScene3DWrapper).toBe('function');
    });
  });

  describe('Static Configuration Constants', () => {
    it('GlobalNetwork has CHROMATIC_ABERRATION_OFFSET hoisted at module level', async () => {
      // Read the source file to verify constant is at module level
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Verify constant is declared before imports (hoisted)
      const chromaticOffsetLine = sourceFile.split('\n').findIndex(
        line => line.includes('CHROMATIC_ABERRATION_OFFSET')
      );
      const firstImportLine = sourceFile.split('\n').findIndex(
        line => line.includes("import { useRef")
      );

      expect(chromaticOffsetLine).toBeGreaterThan(-1);
      expect(chromaticOffsetLine).toBeLessThan(firstImportLine);
    });

    it('AuthScene3D has AUTH_CHROMATIC_OFFSET hoisted at module level', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/AuthScene3D.tsx'),
        'utf-8'
      );

      const chromaticOffsetLine = sourceFile.split('\n').findIndex(
        line => line.includes('AUTH_CHROMATIC_OFFSET')
      );
      const firstImportLine = sourceFile.split('\n').findIndex(
        line => line.includes("import { useRef")
      );

      expect(chromaticOffsetLine).toBeGreaterThan(-1);
      expect(chromaticOffsetLine).toBeLessThan(firstImportLine);
    });

    it('GlobalNetwork has default server/connection data hoisted', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Verify DEFAULT_SERVERS and DEFAULT_CONNECTIONS are module-level constants
      expect(sourceFile).toContain('const DEFAULT_SERVERS');
      expect(sourceFile).toContain('const DEFAULT_CONNECTIONS');

      // Verify they're declared outside components (not inside function bodies)
      const defaultServersLine = sourceFile.split('\n').findIndex(
        line => line.includes('const DEFAULT_SERVERS')
      );
      const mainExportLine = sourceFile.split('\n').findIndex(
        line => line.includes('export default function GlobalNetworkScene')
      );

      expect(defaultServersLine).toBeLessThan(mainExportLine);
    });
  });

  describe('Particle Count Baselines', () => {
    it('GlobalNetwork FloatingParticles default count is within baseline', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Extract FloatingParticles component definition
      const floatingParticlesMatch = sourceFile.match(
        /function FloatingParticles\(\{ count = (\d+) \}/
      );
      expect(floatingParticlesMatch).toBeTruthy();

      const defaultCount = parseInt(floatingParticlesMatch![1], 10);
      expect(defaultCount).toBeLessThanOrEqual(
        PERFORMANCE_BASELINES.GlobalNetwork.maxParticles
      );
      expect(defaultCount).toBe(
        PERFORMANCE_BASELINES.GlobalNetwork.defaultParticles
      );
    });

    it('GlobalNetwork FloatingParticles instantiation uses correct count', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Verify FloatingParticles is called with count={2000}
      const floatingParticlesCall = sourceFile.match(
        /<FloatingParticles count=\{(\d+)\} \/>/
      );
      expect(floatingParticlesCall).toBeTruthy();

      const calledCount = parseInt(floatingParticlesCall![1], 10);
      expect(calledCount).toBe(
        PERFORMANCE_BASELINES.GlobalNetwork.defaultParticles
      );
    });

    it('AuthScene3D SecurityParticles default count is within baseline', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/AuthScene3D.tsx'),
        'utf-8'
      );

      const securityParticlesMatch = sourceFile.match(
        /function SecurityParticles\(\{ count = (\d+) \}/
      );
      expect(securityParticlesMatch).toBeTruthy();

      const defaultCount = parseInt(securityParticlesMatch![1], 10);
      expect(defaultCount).toBeLessThanOrEqual(
        PERFORMANCE_BASELINES.AuthScene3D.maxParticles
      );
      expect(defaultCount).toBe(
        PERFORMANCE_BASELINES.AuthScene3D.defaultParameterValue
      );
    });

    it('AuthScene3D SecurityParticles instantiation uses correct count', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/AuthScene3D.tsx'),
        'utf-8'
      );

      const securityParticlesCall = sourceFile.match(
        /<SecurityParticles count=\{(\d+)\} \/>/
      );
      expect(securityParticlesCall).toBeTruthy();

      const calledCount = parseInt(securityParticlesCall![1], 10);
      expect(calledCount).toBeLessThanOrEqual(
        PERFORMANCE_BASELINES.AuthScene3D.maxParticles
      );
      expect(calledCount).toBe(
        PERFORMANCE_BASELINES.AuthScene3D.instantiatedValue
      );
    });

    it('FeaturesScene3D CyberParticles default count is within baseline', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/FeaturesScene3D.tsx'),
        'utf-8'
      );

      const cyberParticlesMatch = sourceFile.match(
        /function CyberParticles\(\{ count = (\d+) \}/
      );
      expect(cyberParticlesMatch).toBeTruthy();

      const defaultCount = parseInt(cyberParticlesMatch![1], 10);
      expect(defaultCount).toBeLessThanOrEqual(
        PERFORMANCE_BASELINES.FeaturesScene3D.maxParticles
      );
      expect(defaultCount).toBe(
        PERFORMANCE_BASELINES.FeaturesScene3D.defaultParameterValue
      );
    });

    it('FeaturesScene3D CyberParticles instantiation uses correct count', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/FeaturesScene3D.tsx'),
        'utf-8'
      );

      const cyberParticlesCall = sourceFile.match(
        /<CyberParticles count=\{(\d+)\} \/>/
      );
      expect(cyberParticlesCall).toBeTruthy();

      const calledCount = parseInt(cyberParticlesCall![1], 10);
      expect(calledCount).toBeLessThanOrEqual(
        PERFORMANCE_BASELINES.FeaturesScene3D.maxParticles
      );
      expect(calledCount).toBe(
        PERFORMANCE_BASELINES.FeaturesScene3D.instantiatedValue
      );
    });
  });

  describe('Geometry Configuration', () => {
    it('GlobalNetwork uses instancedMesh for FloatingParticles', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Verify FloatingParticles uses instancedMesh
      expect(sourceFile).toContain('mesh.current.setMatrixAt');
      expect(sourceFile).toContain('instanceMatrix.needsUpdate = true');
      expect(sourceFile).toContain('<instancedMesh');
    });

    it('AuthScene3D uses instancedMesh for SecurityParticles', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/AuthScene3D.tsx'),
        'utf-8'
      );

      expect(sourceFile).toContain('meshRef.current.setMatrixAt');
      expect(sourceFile).toContain('instanceMatrix.needsUpdate = true');
      expect(sourceFile).toContain('<instancedMesh');
    });

    it('FeaturesScene3D uses instancedMesh for CyberParticles', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/FeaturesScene3D.tsx'),
        'utf-8'
      );

      // FeaturesScene3D uses meshRef.current! with non-null assertion
      expect(sourceFile).toMatch(/meshRef\.current!?\.setMatrixAt/);
      expect(sourceFile).toContain('instanceMatrix.needsUpdate = true');
      expect(sourceFile).toContain('<instancedMesh');
    });
  });

  describe('Canvas Performance Settings', () => {
    it('GlobalNetwork Canvas has dpr capped for performance', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Verify dpr is set to [1, 2] (min 1x, max 2x)
      expect(sourceFile).toMatch(/dpr=\{\[1,\s*2\]\}/);
    });

    it('GlobalNetwork Canvas has GL performance settings', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      expect(sourceFile).toContain('powerPreference: "high-performance"');
      expect(sourceFile).toContain('antialias: false');
      expect(sourceFile).toContain('alpha: true');
    });

    it('AuthScene3D Canvas has dpr capped for performance', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/AuthScene3D.tsx'),
        'utf-8'
      );

      // Verify dpr is set to [1, 1.5] (max 1.5x for auth scenes)
      expect(sourceFile).toMatch(/dpr=\{\[1,\s*1\.5\]\}/);
    });

    it('AuthScene3D Canvas has GL performance settings', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/AuthScene3D.tsx'),
        'utf-8'
      );

      expect(sourceFile).toContain('powerPreference: \'high-performance\'');
      expect(sourceFile).toContain('antialias: true');
      expect(sourceFile).toContain('alpha: true');
    });

    it('FeaturesScene3D Canvas has dpr capped for performance', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/FeaturesScene3D.tsx'),
        'utf-8'
      );

      expect(sourceFile).toMatch(/dpr=\{\[1,\s*1\.5\]\}/);
    });

    it('FeaturesScene3D Canvas has GL performance settings', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/FeaturesScene3D.tsx'),
        'utf-8'
      );

      expect(sourceFile).toContain('powerPreference: \'high-performance\'');
      expect(sourceFile).toContain('antialias: true');
      expect(sourceFile).toContain('alpha: true');
    });
  });

  describe('Post-Processing Configuration', () => {
    it('GlobalNetwork EffectComposer disables normalPass and multisampling', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      expect(sourceFile).toContain('enableNormalPass={false}');
      expect(sourceFile).toContain('multisampling={0}');
    });

    it('AuthScene3D EffectComposer disables normalPass and multisampling', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/AuthScene3D.tsx'),
        'utf-8'
      );

      expect(sourceFile).toContain('enableNormalPass={false}');
      expect(sourceFile).toContain('multisampling={0}');
    });

    it('FeaturesScene3D does not use EffectComposer (performance optimization)', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/FeaturesScene3D.tsx'),
        'utf-8'
      );

      // FeaturesScene3D intentionally doesn't use post-processing for performance
      expect(sourceFile).not.toContain('EffectComposer');
    });
  });

  describe('Frameloop Configuration', () => {
    it('GlobalNetwork uses always frameloop (animated scene)', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      expect(sourceFile).toContain('frameloop="always"');
    });

    it('AuthScene3D and FeaturesScene3D do not specify frameloop (default always)', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const authSource = await fs.readFile(
        path.resolve(__dirname, '../scenes/AuthScene3D.tsx'),
        'utf-8'
      );
      const featuresSource = await fs.readFile(
        path.resolve(__dirname, '../scenes/FeaturesScene3D.tsx'),
        'utf-8'
      );

      // These scenes are animated so they use default "always"
      // If frameloop is specified, it should be "always"
      if (authSource.includes('frameloop=')) {
        expect(authSource).toContain('frameloop="always"');
      }
      if (featuresSource.includes('frameloop=')) {
        expect(featuresSource).toContain('frameloop="always"');
      }
    });
  });

  describe('useMemo for Expensive Computations', () => {
    it('GlobalNetwork FloatingParticles uses useMemo for particle data', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Verify positions/velocities/phases are created in useMemo
      const floatingParticlesSection = sourceFile.substring(
        sourceFile.indexOf('function FloatingParticles'),
        sourceFile.indexOf('function FloatingParticles') + 2000
      );

      expect(floatingParticlesSection).toContain('useMemo(() => {');
      expect(floatingParticlesSection).toContain('positions');
      expect(floatingParticlesSection).toContain('velocities');
      expect(floatingParticlesSection).toContain('phases');
    });

    it('GlobalNetwork dummy object is memoized', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Verify dummy Object3D is created in useMemo
      expect(sourceFile).toMatch(/const dummy = useMemo\(\(\) => new THREE\.Object3D\(\)/);
    });

    it('AuthScene3D SecurityParticles uses useMemo for particle array', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/AuthScene3D.tsx'),
        'utf-8'
      );

      const securityParticlesSection = sourceFile.substring(
        sourceFile.indexOf('function SecurityParticles'),
        sourceFile.indexOf('function SecurityParticles') + 2000
      );

      expect(securityParticlesSection).toContain('useMemo(() => {');
      expect(securityParticlesSection).toContain('Array.from');
    });

    it('FeaturesScene3D CyberParticles uses useMemo for particle array', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/FeaturesScene3D.tsx'),
        'utf-8'
      );

      const cyberParticlesSection = sourceFile.substring(
        sourceFile.indexOf('function CyberParticles'),
        sourceFile.indexOf('function CyberParticles') + 2000
      );

      expect(cyberParticlesSection).toContain('useMemo(() => {');
      expect(cyberParticlesSection).toContain('Array.from');
    });
  });

  describe('Stable Keys for Mapped Elements', () => {
    it('GlobalNetwork ServerNodes uses server.id as key', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Verify server nodes use stable ID-based keys
      expect(sourceFile).toMatch(/key=\{server\.id\}/);
    });

    it('GlobalNetwork ConnectionLines uses coordinate-based keys', async () => {
      const fs = await import('fs/promises');
      const path = await import('path');
      const sourceFile = await fs.readFile(
        path.resolve(__dirname, '../scenes/GlobalNetwork.tsx'),
        'utf-8'
      );

      // Verify connection lines use coordinate-based keys, not index
      const connectionLinesSection = sourceFile.substring(
        sourceFile.indexOf('function ConnectionLines'),
        sourceFile.indexOf('function ConnectionLines') + 1500
      );

      expect(connectionLinesSection).toContain('const key = ');
      expect(connectionLinesSection).toContain('key={key}');
      // Should NOT use index as key
      expect(connectionLinesSection).not.toMatch(/key=\{i\}/);
    });
  });
});
