import { beforeEach, describe, expect, it, vi } from 'vitest';

async function loadFeatureFlagsModule() {
  vi.resetModules();
  return import('../feature-flags');
}

describe('featureFlagManager', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('loads persisted dev flags, notifies subscribers, persists changes, and resets to defaults', async () => {
    window.localStorage.setItem(
      'DEV_FEATURE_FLAGS',
      JSON.stringify({ enableCryptoPayments: true, newServerGrid: true }),
    );
    const { featureFlagManager } = await loadFeatureFlagsModule();
    const listener = vi.fn();

    const unsubscribe = featureFlagManager.subscribe(listener);

    expect(featureFlagManager.getFlag('enableCryptoPayments')).toBe(true);
    expect(featureFlagManager.getFlag('newServerGrid')).toBe(true);
    expect(featureFlagManager.getFlag('useMockData')).toBe(false);
    expect(listener).toHaveBeenLastCalledWith(
      expect.objectContaining({
        enableCryptoPayments: true,
        newServerGrid: true,
        useMockData: false,
      }),
    );

    featureFlagManager.setFlag('useMockData', true);

    expect(featureFlagManager.getFlags()).toMatchObject({ useMockData: true });
    expect(JSON.parse(window.localStorage.getItem('DEV_FEATURE_FLAGS') ?? '{}')).toMatchObject({
      enableCryptoPayments: true,
      newServerGrid: true,
      useMockData: true,
    });
    expect(listener).toHaveBeenLastCalledWith(expect.objectContaining({ useMockData: true }));

    featureFlagManager.reset();

    expect(featureFlagManager.getFlags()).toEqual({
      enableCryptoPayments: false,
      useMockData: false,
      newServerGrid: false,
      experimentalAnimations: false,
    });
    expect(JSON.parse(window.localStorage.getItem('DEV_FEATURE_FLAGS') ?? '{}')).toEqual({
      enableCryptoPayments: false,
      useMockData: false,
      newServerGrid: false,
      experimentalAnimations: false,
    });

    unsubscribe();
    featureFlagManager.setFlag('experimentalAnimations', true);
    expect(listener).not.toHaveBeenLastCalledWith(
      expect.objectContaining({ experimentalAnimations: true }),
    );
  });

  it('keeps safe defaults when persisted dev flag JSON is malformed', async () => {
    window.localStorage.setItem('DEV_FEATURE_FLAGS', '{bad json');

    const { FEATURE_FLAGS, featureFlagManager } = await loadFeatureFlagsModule();

    expect(Object.keys(FEATURE_FLAGS)).toEqual([
      'enableCryptoPayments',
      'useMockData',
      'newServerGrid',
      'experimentalAnimations',
    ]);
    expect(featureFlagManager.getFlags()).toEqual({
      enableCryptoPayments: false,
      useMockData: false,
      newServerGrid: false,
      experimentalAnimations: false,
    });
  });
});
