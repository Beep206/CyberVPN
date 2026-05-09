import { describe, expect, it } from 'vitest';
import type { ErrorEvent } from '@sentry/core';

import { scrubSentryEvent } from '../sentry-privacy';

describe('scrubSentryEvent', () => {
  it('redacts S1-sensitive request, identity, payment and config material', () => {
    const event = {
      request: {
        url: 'https://admin.cyber-vpn.net/payments?token=secret#hash',
        headers: {
          Authorization: 'Bearer top-secret',
          Cookie: 'session=secret',
          'Set-Cookie': 'refresh=secret',
          'X-Telegram-Bot-Api-Secret-Token': 'telegram-secret',
          'X-Request-Id': 'req-1',
        },
        cookies: { session: 'secret' },
        data: { password: 'secret' },
      },
      user: {
        id: 'admin-user-id',
        email: 'admin@example.com',
        username: 'sasha',
        ip_address: '127.0.0.1',
      },
      extra: {
        remnawaveConfigUrl: 'https://remnawave.local/api/v1/vpn/config/user',
        oauthAccessToken: 'oauth-secret',
        provider_name: 'yookassa',
      },
      contexts: {
        payment: {
          provider_payment_id: 'pay_123',
        },
        safe: {
          action: 'manual_review',
        },
      },
    } as unknown as ErrorEvent;

    const scrubbed = scrubSentryEvent(event);

    expect(scrubbed.request?.url).toBe('https://admin.cyber-vpn.net/payments');
    expect(scrubbed.request?.headers?.Authorization).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.Cookie).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['Set-Cookie']).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['X-Telegram-Bot-Api-Secret-Token']).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['X-Request-Id']).toBe('req-1');
    expect(scrubbed.request?.cookies).toBeUndefined();
    expect(scrubbed.request?.data).toBe('[Filtered]');
    expect(scrubbed.user).toEqual({ id: 'admin-user-id' });
    expect(scrubbed.extra?.remnawaveConfigUrl).toBe('[Filtered]');
    expect(scrubbed.extra?.oauthAccessToken).toBe('[Filtered]');
    expect(scrubbed.extra?.provider_name).toBe('yookassa');
    expect(scrubbed.contexts?.payment).toBe('[Filtered]');
    expect(scrubbed.contexts?.safe?.action).toBe('manual_review');
  });
});
