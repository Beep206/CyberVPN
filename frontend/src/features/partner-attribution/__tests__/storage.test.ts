import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearPartnerAttribution,
  PARTNER_ATTRIBUTION_CHANGED_EVENT,
  PARTNER_ATTRIBUTION_STORAGE_KEY,
  readPartnerAttribution,
  savePartnerAttribution,
} from '../storage';

describe('partner attribution storage v1', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('stores and reads a pending partner attribution snapshot', () => {
    savePartnerAttribution({
      attributionId: 'partner-attr-1',
      capturedAt: '2026-06-19T00:00:00.000Z',
      expiresAt: '2099-06-19T00:00:00.000Z',
      maskedCode: 'PART****',
      sourceHost: 'my.cyber-vpn.net',
      sourcePath: '/ru-RU/register',
      version: 1,
    });

    expect(readPartnerAttribution()).toMatchObject({
      attributionId: 'partner-attr-1',
      maskedCode: 'PART****',
      version: 1,
    });
  });

  it('does not emit change events when reading empty or malformed storage', () => {
    const listener = vi.fn();
    window.addEventListener(PARTNER_ATTRIBUTION_CHANGED_EVENT, listener);

    try {
      expect(readPartnerAttribution()).toBeNull();
      expect(listener).not.toHaveBeenCalled();

      window.localStorage.setItem(PARTNER_ATTRIBUTION_STORAGE_KEY, '{"version":0}');

      expect(readPartnerAttribution()).toBeNull();
      expect(window.localStorage.getItem(PARTNER_ATTRIBUTION_STORAGE_KEY)).toBeNull();
      expect(listener).not.toHaveBeenCalled();
    } finally {
      window.removeEventListener(PARTNER_ATTRIBUTION_CHANGED_EVENT, listener);
    }
  });

  it('emits clear events only when stored attribution actually existed', () => {
    const listener = vi.fn();
    window.addEventListener(PARTNER_ATTRIBUTION_CHANGED_EVENT, listener);

    try {
      clearPartnerAttribution();
      expect(listener).not.toHaveBeenCalled();

      savePartnerAttribution({
        attributionId: 'partner-attr-2',
        capturedAt: '2026-06-19T00:00:00.000Z',
        expiresAt: '2099-06-19T00:00:00.000Z',
        maskedCode: 'PART****',
        sourceHost: null,
        sourcePath: null,
        version: 1,
      });
      expect(listener).toHaveBeenCalledTimes(1);

      clearPartnerAttribution();
      expect(listener).toHaveBeenCalledTimes(2);

      clearPartnerAttribution();
      expect(listener).toHaveBeenCalledTimes(2);
    } finally {
      window.removeEventListener(PARTNER_ATTRIBUTION_CHANGED_EVENT, listener);
    }
  });
});
