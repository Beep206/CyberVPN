/**
 * Smoke tests for 3D scene components.
 * Verifies modules load and export React components without crashing.
 * Full rendering tests belong in E2E (Playwright) since jsdom has no WebGL.
 */
import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mocks (all inline for hoisting)
// ---------------------------------------------------------------------------
vi.mock('three', () => {
  function C() { return { x: 0, y: 0, z: 0, set() { return this; }, copy() { return this; }, clone() { return this; }, normalize() { return this; }, multiplyScalar() { return this; }, add() { return this; }, sub() { return this; }, cross() { return this; }, getPoints() { return []; }, toArray() { return [0,0,0]; }, setAttribute() {}, makeRotationFromEuler() { return this; }, compose() { return this; }, moveTo() { return this; }, lineTo() { return this; }, closePath() { return this; }, extractPoints() { return { shape: [], holes: [] }; } }; }
  return {
    __esModule: true,
    Object3D: C, Vector2: C, Vector3: C, Color: C, Matrix4: C, Euler: C, Quaternion: C,
    Shape: C, ExtrudeGeometry: C, ShapeGeometry: C,
    CatmullRomCurve3: C, CubicBezierCurve3: C, LineCurve3: C,
    Float32BufferAttribute: C, BufferGeometry: C, BufferAttribute: C,
    ShaderMaterial: C, MeshBasicMaterial: C, MeshStandardMaterial: C, MeshPhysicalMaterial: C,
    SphereGeometry: C, IcosahedronGeometry: C, BoxGeometry: C, PlaneGeometry: C,
    CylinderGeometry: C, TorusGeometry: C, RingGeometry: C, TubeGeometry: C,
    InstancedMesh: C, Group: C, Mesh: C, Line: C, LineSegments: C, Points: C,
    Scene: C, Clock: C, Raycaster: C, TextureLoader: C, WebGLRenderer: C,
    PerspectiveCamera: C, AmbientLight: C, PointLight: C, DirectionalLight: C,
    SpotLight: C, HemisphereLight: C, Fog: C, FogExp2: C,
    Sprite: C, SpriteMaterial: C, CanvasTexture: C, Texture: C,
    DoubleSide: 2, FrontSide: 0, BackSide: 1, AdditiveBlending: 2, NormalBlending: 1,
    LinearFilter: 1006, ClampToEdgeWrapping: 1001,
    MathUtils: { lerp: (a: number) => a, degToRad: (d: number) => d * 0.01745, clamp: (v: number) => v },
  };
});

vi.mock('@react-three/fiber', async () => {
  const React = await import('react');
  return {
    Canvas: () => React.createElement('div', { 'data-testid': 'r3f-canvas' }),
    useFrame: () => {},
    useThree: () => ({ pointer: { x: 0, y: 0 }, size: { width: 800, height: 600 } }),
    extend: () => {},
  };
});

vi.mock('@react-three/drei', () => ({
  __esModule: true,
  Line: () => null, Sphere: () => null, Icosahedron: () => null, OrbitControls: () => null,
  Trail: () => null, Environment: () => null, Float: () => null,
  MeshDistortMaterial: () => null, MeshWobbleMaterial: () => null,
  MeshTransmissionMaterial: () => null,
  Sparkles: () => null, Stars: () => null, GradientTexture: () => null,
  shaderMaterial: () => null,
}));

vi.mock('@react-three/postprocessing', () => ({
  __esModule: true,
  EffectComposer: () => null, Bloom: () => null, ChromaticAberration: () => null,
  ToneMapping: () => null, Noise: () => null, Vignette: () => null,
}));

vi.mock('@/3d/shaders/AtmosphereShader', () => ({ AtmosphereShader: null }));
vi.mock('@/3d/shaders/CyberSphereShader', () => ({}));
vi.mock('@/3d/shaders/CyberSphereShaderV2', () => ({}));
vi.mock('next-intl', () => ({ useTranslations: () => (k: string) => k }));

// ---------------------------------------------------------------------------
// Static imports (mocks applied during resolution)
// ---------------------------------------------------------------------------
import GlobalNetworkScene from '@/3d/scenes/GlobalNetwork';
import { FeaturesScene3D, FeaturesScene3DWrapper } from '@/3d/scenes/FeaturesScene3D';
import { AuthScene3D } from '@/3d/scenes/AuthScene3D';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('3D Components - Smoke Tests', () => {
  describe('GlobalNetworkScene', () => {
    it('test_export_is_function', () => {
      expect(typeof GlobalNetworkScene).toBe('function');
      expect(GlobalNetworkScene.name).toBe('GlobalNetworkScene');
    });

    it('test_renders_wrapper_div', () => {
      const { container } = render(<GlobalNetworkScene />);
      const wrapper = container.firstElementChild as HTMLElement;
      expect(wrapper).toBeTruthy();
      expect(wrapper.className).toContain('absolute');
    });
  });

  describe('FeaturesScene3D', () => {
    it('test_export_is_function', () => {
      expect(typeof FeaturesScene3D).toBe('function');
    });

    it('test_renders_wrapper_div', () => {
      const { container } = render(<FeaturesScene3D />);
      const wrapper = container.firstElementChild as HTMLElement;
      expect(wrapper).toBeTruthy();
      expect(wrapper.className).toContain('pointer-events-none');
    });
  });

  describe('FeaturesScene3DWrapper', () => {
    it('test_export_is_function', () => {
      expect(typeof FeaturesScene3DWrapper).toBe('function');
    });

    it('test_renders_without_crashing', () => {
      const { container } = render(<FeaturesScene3DWrapper />);
      expect(container).toBeTruthy();
    });
  });

  describe('AuthScene3D', () => {
    it('test_export_is_function', () => {
      expect(typeof AuthScene3D).toBe('function');
    });

    it('test_renders_wrapper_div', () => {
      const { container } = render(<AuthScene3D />);
      const wrapper = container.firstElementChild as HTMLElement;
      expect(wrapper).toBeTruthy();
      expect(wrapper.className).toContain('absolute');
    });
  });
});
