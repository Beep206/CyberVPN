import { describe, expect, it } from 'vitest';
import {
  buildCoreNotificationPatch,
  buildGrowthNotificationPatch,
  CORE_NOTIFICATION_PREFERENCES,
  formatDateTime,
  formatShortId,
  getDeviceKind,
  getEnabledCount,
  GROWTH_NOTIFICATION_PREFERENCES,
  getSecurityPosture,
  maskAntiphishingCode,
  parseDeviceLabel,
} from '../settings-cabinet-model';

describe('settings-cabinet-model', () => {
  it('builds notification patches without leaking unrelated preferences', () => {
    expect(buildCoreNotificationPatch('email_marketing', true)).toEqual({
      email_marketing: true,
    });
    expect(buildGrowthNotificationPatch('growth_email_referral_rewards', false)).toEqual({
      growth_email_referral_rewards: false,
    });
    expect(CORE_NOTIFICATION_PREFERENCES.map((item) => item.key)).toEqual([
      'email_security',
      'email_marketing',
      'push_connection',
      'push_payment',
      'push_subscription',
    ]);
    expect(GROWTH_NOTIFICATION_PREFERENCES.map((item) => item.key)).toEqual([
      'growth_in_app_invites',
      'growth_email_referral_rewards',
      'growth_telegram_referral_rewards',
      'growth_email_gifts',
      'growth_telegram_admin_updates',
    ]);
  });

  it('parses device kind and labels from user agent', () => {
    expect(getDeviceKind('Mozilla/5.0 (Android 14) Chrome/120.0.0.0')).toBe('mobile');
    expect(getDeviceKind('Mozilla/5.0 (iPhone) Mobile Safari/604.1')).toBe('mobile');
    expect(getDeviceKind('Mozilla/5.0 (iPad) Safari/604.1')).toBe('tablet');
    expect(getDeviceKind('Mozilla/5.0 (Android 14; Tablet) Chrome/120.0.0.0')).toBe('tablet');
    expect(getDeviceKind(null)).toBe('desktop');
    expect(getDeviceKind('Mozilla/5.0 (Windows NT 10.0) Chrome/120.0.0.0')).toBe('desktop');
    expect(parseDeviceLabel('Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0')).toContain(
      'Chrome / Windows NT 10.0',
    );
    expect(parseDeviceLabel('Mozilla/5.0 (Mac OS X 14_4) Edg/120.0.0.0')).toContain(
      'Edge / Mac OS X 14.4',
    );
    expect(parseDeviceLabel('Mozilla/5.0 (Android 14) Firefox/120.0')).toContain(
      'Firefox / Android 14',
    );
    expect(parseDeviceLabel('Mozilla/5.0 (iPhone OS 17_4) CriOS/120.0')).toContain(
      'Chrome / iPhone OS 17.4',
    );
    expect(parseDeviceLabel('Mozilla/5.0 (CPU OS 17_4) Safari/604.1')).toContain(
      'Safari / CPU OS 17.4',
    );
    expect(parseDeviceLabel('Mozilla/5.0 (X11; Linux x86_64)')).toBe('Browser / Linux');
    expect(parseDeviceLabel('CustomAgent/1.0')).toBe('Browser / Unknown OS');
    expect(parseDeviceLabel('   ')).toBe('Unknown device');
  });

  it('formats identifiers and masks anti-phishing values', () => {
    expect(formatDateTime(null)).toBe('n/a');
    expect(formatDateTime('not-a-date')).toBe('n/a');
    expect(formatDateTime('2026-04-24T10:00:00Z', 'en-EN')).not.toBe('n/a');
    expect(formatShortId(null)).toBe('n/a');
    expect(formatShortId('   ')).toBe('n/a');
    expect(formatShortId('short-id')).toBe('short-id');
    expect(formatShortId('1234567890abcdef')).toBe('12345678...');
    expect(maskAntiphishingCode('ABCD')).toBe('****');
    expect(maskAntiphishingCode('CYBER-ALPHA')).toBe('CY*******HA');
    expect(maskAntiphishingCode('  CYBER-ALPHA  ')).toBe('CY*******HA');
    expect(maskAntiphishingCode(null)).toBe('not-set');
    expect(maskAntiphishingCode('   ')).toBe('not-set');
  });

  it('calculates security posture from backend-owned signals', () => {
    const hardened = getSecurityPosture({
      antiPhishingCode: { code: 'CYBER' },
      devices: [
        {
          is_current: true,
        },
      ],
      notificationPreferences: {
        email_marketing: false,
        email_security: true,
        push_connection: true,
        push_payment: true,
        push_subscription: true,
      },
      twoFactorStatus: { status: 'enabled' },
    });

    expect(hardened).toEqual({ score: 100, state: 'hardened', tone: 'green' });
    expect(getEnabledCount({ first: true, second: false, third: true })).toBe(2);
    expect(getEnabledCount(null)).toBe(0);
    expect(getEnabledCount({ first: true, second: 'true', third: 1 })).toBe(1);
  });

  it('downgrades security posture when 2FA, anti-phishing or session hygiene is missing', () => {
    expect(
      getSecurityPosture({
        antiPhishingCode: { code: null },
        devices: [
          { is_current: true },
          { is_current: false },
        ],
        notificationPreferences: {
          email_marketing: false,
          email_security: true,
          push_connection: false,
          push_payment: false,
          push_subscription: false,
        },
        twoFactorStatus: { status: 'disabled' },
      }),
    ).toEqual({ score: 50, state: 'attention', tone: 'amber' });

    expect(
      getSecurityPosture({
        antiPhishingCode: null,
        devices: [
          { is_current: true },
          { is_current: false },
          { is_current: false },
          { is_current: false },
        ],
        notificationPreferences: null,
        twoFactorStatus: null,
      }),
    ).toEqual({ score: 0, state: 'exposed', tone: 'pink' });
  });
});
