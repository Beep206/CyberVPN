import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMotionCapability } from '@/shared/hooks/use-motion-capability';
import { useVisualTier } from '../use-visual-tier';

vi.mock('@/shared/hooks/use-motion-capability', () => ({
  useMotionCapability: vi.fn(),
}));

const mockedUseMotionCapability = vi.mocked(useMotionCapability);
const originalInnerWidth = window.innerWidth;

function setViewportWidth(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value: width,
  });
}

describe('useVisualTier', () => {
  beforeEach(() => {
    mockedUseMotionCapability.mockReturnValue({
      allowAmbientAnimations: true,
      allowPointerEffects: true,
      hasFinePointer: true,
      isLowPowerDevice: false,
    });
  });

  afterEach(() => {
    act(() => {
      setViewportWidth(originalInnerWidth);
      window.dispatchEvent(new Event('resize'));
    });
    vi.clearAllMocks();
  });

  it('returns minimal for low-power mobile devices', () => {
    mockedUseMotionCapability.mockReturnValue({
      allowAmbientAnimations: false,
      allowPointerEffects: false,
      hasFinePointer: false,
      isLowPowerDevice: true,
    });
    act(() => {
      setViewportWidth(390);
      window.dispatchEvent(new Event('resize'));
    });

    const { result } = renderHook(() => useVisualTier());

    expect(result.current.tier).toBe('minimal');
    expect(result.current.isMinimal).toBe(true);
  });

  it('returns reduced for normal touch devices', () => {
    mockedUseMotionCapability.mockReturnValue({
      allowAmbientAnimations: true,
      allowPointerEffects: false,
      hasFinePointer: false,
      isLowPowerDevice: false,
    });
    act(() => {
      setViewportWidth(430);
      window.dispatchEvent(new Event('resize'));
    });

    const { result } = renderHook(() => useVisualTier());

    expect(result.current.tier).toBe('reduced');
    expect(result.current.isReduced).toBe(true);
  });

  it('returns full for desktop devices with a fine pointer', () => {
    act(() => {
      setViewportWidth(1440);
      window.dispatchEvent(new Event('resize'));
    });

    const { result } = renderHook(() => useVisualTier());

    expect(result.current.tier).toBe('full');
    expect(result.current.isFull).toBe(true);
  });

  it('reacts to viewport changes', async () => {
    act(() => {
      setViewportWidth(1440);
      window.dispatchEvent(new Event('resize'));
    });

    const { result } = renderHook(() => useVisualTier());

    expect(result.current.tier).toBe('full');

    mockedUseMotionCapability.mockReturnValue({
      allowAmbientAnimations: true,
      allowPointerEffects: false,
      hasFinePointer: false,
      isLowPowerDevice: false,
    });

    act(() => {
      setViewportWidth(430);
      window.dispatchEvent(new Event('resize'));
    });

    await waitFor(() => {
      expect(result.current.tier).toBe('reduced');
    });
  });
});
