/**
 * Static performance regression tests for the current 3D optimization baseline.
 *
 * These tests validate structural guardrails that should not regress silently:
 * - shared canvas/performance helpers stay in use
 * - scene timing metrics remain attached to key scenes
 * - GlobalNetwork avoids per-route controls/remount overhead
 * - click-only crumble effect stays lazy-loaded
 */

import { describe, expect, it } from 'vitest';
import fs from 'fs/promises';
import path from 'path';
import {
  MARKETING_SCENE_CANVAS_PERFORMANCE,
  MARKETING_SCENE_GL,
} from '@/3d/lib/scene-performance';

const ROOT = path.resolve(__dirname, '../..');

async function readSource(relativePath: string) {
  return fs.readFile(path.join(ROOT, relativePath), 'utf-8');
}

describe('3D performance baseline', () => {
  it('shared scene helpers keep production-friendly defaults', () => {
    expect(MARKETING_SCENE_CANVAS_PERFORMANCE.min).toBe(0.5);
    expect(MARKETING_SCENE_CANVAS_PERFORMANCE.max).toBe(1);
    expect(MARKETING_SCENE_GL.powerPreference).toBe('high-performance');
    expect(MARKETING_SCENE_GL.antialias).toBe(false);
    expect(MARKETING_SCENE_GL.alpha).toBe(true);
  });

  it('GlobalNetwork uses scene metrics, adaptive DPR, and no OrbitControls', async () => {
    const source = await readSource('3d/scenes/GlobalNetwork.tsx');

    expect(source).toContain('ScenePerformanceMetrics sceneName="global-network"');
    expect(source).toContain('useAdaptiveSceneDpr');
    expect(source).toContain('MARKETING_SCENE_CANVAS_PERFORMANCE');
    expect(source).toContain('MARKETING_SCENE_GL');
    expect(source).toContain('const serverPositions = useMemo');
    expect(source).toContain('const { curves, pointsByCurve } = useMemo');
    expect(source).toContain('<FloatingParticles count={400} />');
    expect(source).not.toContain('OrbitControls');
  });

  it('FeaturesScene3D keeps adaptive performance hooks and shared composer settings', async () => {
    const source = await readSource('3d/scenes/FeaturesScene3D.tsx');

    expect(source).toContain('ScenePerformanceMetrics sceneName="features-core"');
    expect(source).toContain('useAdaptiveSceneDpr');
    expect(source).toContain('MARKETING_SCENE_CANVAS_PERFORMANCE');
    expect(source).toContain('MARKETING_SCENE_GL');
    expect(source).toContain('enableNormalPass={false}');
    expect(source).toContain('const geometry = useMemo(() => ENGINE_CORE_GEOMETRY');
    expect(source).toContain('shieldRef.current.scale.lerp(isKillswitch ? SHIELD_ACTIVE_SCALE : SHIELD_IDLE_SCALE');
  });

  it('other marketing scenes emit first-frame metrics and share adaptive canvas settings', async () => {
    const antiDpi = await readSource('3d/scenes/AntiDPIScene3D.tsx');
    const fastTrack = await readSource('3d/scenes/FastTrackScene3D.tsx');
    const speedTunnel = await readSource('widgets/speed-tunnel-scene.tsx');

    expect(antiDpi).toContain('ScenePerformanceMetrics sceneName="anti-dpi"');
    expect(antiDpi).toContain('MARKETING_SCENE_GL');
    expect(fastTrack).toContain('ScenePerformanceMetrics sceneName="fast-track"');
    expect(fastTrack).toContain('MARKETING_SCENE_CANVAS_PERFORMANCE');
    expect(speedTunnel).toContain('ScenePerformanceMetrics sceneName="speed-tunnel"');
    expect(speedTunnel).toContain('SPEED_TUNNEL_VERTEX_SHADER');
    expect(speedTunnel).toContain('generateStarfieldData(count)');
  });

  it('interactive UI effects are gated by motion capability', async () => {
    const magnetic = await readSource('shared/ui/magnetic-button.tsx');
    const tilt = await readSource('shared/ui/tilt-card.tsx');
    const scramble = await readSource('shared/ui/scramble-text.tsx');
    const cypher = await readSource('shared/ui/atoms/cypher-text.tsx');
    const statusBadge = await readSource('shared/ui/status-badge-live.tsx');

    expect(magnetic).toContain('useMotionCapability');
    expect(tilt).toContain('useMotionCapability');
    expect(scramble).toContain('allowAmbientAnimations');
    expect(cypher).toContain('allowAmbientAnimations');
    expect(statusBadge).toContain('animate-pulse');
  });

  it('inception overlay stays lazy-loaded instead of bundling Canvas eagerly', async () => {
    const source = await readSource('components/ui/InceptionButton.tsx');

    expect(source).toContain('dynamic(');
    expect(source).toContain("import('./inception-overlay')");
    expect(source).not.toContain("import { Canvas } from '@react-three/fiber'");
  });

  it('dashboard is the only place that explicitly enables live FPS header metrics', async () => {
    const dashboardLayout = await readSource('app/[locale]/(dashboard)/layout.tsx');
    const header = await readSource('widgets/terminal-header.tsx');

    expect(header).toContain('showPerformance = false');
    expect(dashboardLayout).toContain('<TerminalHeader showPerformance />');
  });
});
