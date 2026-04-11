import { describe, expect, it } from 'vitest';
import {
  getDeviceBucket,
  getRouteGroup,
  getViewportBucket,
} from '../mobile-device-bucket';

describe('mobile-device-bucket', () => {
  it('classifies iPhone Safari as mobile-touch', () => {
    expect(
      getDeviceBucket({
        width: 390,
        finePointer: false,
        prefersReducedMotion: false,
        hardwareConcurrency: 6,
        deviceMemory: 4,
        saveData: false,
        effectiveType: '4g',
      }),
    ).toBe('mobile-touch');
  });

  it('classifies low-power Android as mobile-low-power', () => {
    expect(
      getDeviceBucket({
        width: 360,
        finePointer: false,
        prefersReducedMotion: false,
        hardwareConcurrency: 2,
        deviceMemory: 2,
        saveData: false,
        effectiveType: '3g',
      }),
    ).toBe('mobile-low-power');
  });

  it('classifies tablet portrait as tablet-touch', () => {
    expect(
      getDeviceBucket({
        width: 834,
        finePointer: false,
        prefersReducedMotion: false,
        hardwareConcurrency: 8,
        deviceMemory: 8,
        saveData: false,
        effectiveType: '4g',
      }),
    ).toBe('tablet-touch');
  });

  it('classifies fine-pointer desktop as desktop', () => {
    expect(
      getDeviceBucket({
        width: 1440,
        finePointer: true,
        prefersReducedMotion: false,
        hardwareConcurrency: 10,
        deviceMemory: 16,
        saveData: false,
        effectiveType: '4g',
      }),
    ).toBe('desktop');
  });
});

describe('getViewportBucket', () => {
  it('returns compact mobile for very narrow widths', () => {
    expect(getViewportBucket(360)).toBe('mobile-compact');
  });

  it('returns regular mobile for standard phone widths', () => {
    expect(getViewportBucket(430)).toBe('mobile-regular');
  });

  it('returns tablet for tablet widths', () => {
    expect(getViewportBucket(900)).toBe('tablet');
  });

  it('returns desktop for wide widths', () => {
    expect(getViewportBucket(1280)).toBe('desktop');
  });
});

describe('getRouteGroup', () => {
  it('classifies dashboard routes', () => {
    expect(getRouteGroup('/en-EN/dashboard')).toBe('dashboard');
    expect(getRouteGroup('/ru-RU/analytics')).toBe('dashboard');
  });

  it('classifies miniapp routes', () => {
    expect(getRouteGroup('/en-EN/miniapp/home')).toBe('miniapp');
  });

  it('classifies auth routes', () => {
    expect(getRouteGroup('/en-EN/login')).toBe('auth');
    expect(getRouteGroup('/en-EN/oauth/callback')).toBe('auth');
  });

  it('classifies everything else as marketing', () => {
    expect(getRouteGroup('/en-EN/pricing')).toBe('marketing');
    expect(getRouteGroup('/')).toBe('marketing');
  });
});
