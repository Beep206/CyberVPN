import { describe, expect, it } from 'vitest';
import type { ErrorEvent } from '@sentry/core';

import { scrubSentryEvent } from '../sentry-privacy';

describe('scrubSentryEvent', () => {
  it('redacts S1-sensitive request, identity, payment and config material', () => {
    const event = {
      request: {
        url: 'https://cyber-vpn.net/ru-RU/miniapp/plans?token=secret&tgWebAppData=query#hash',
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
        id: 'internal-user-id',
        email: 'user@example.com',
        username: 'alice',
        ip_address: '127.0.0.1',
      },
      extra: {
        oauthAccessToken: 'oauth-secret',
        totpSecret: 'totp-secret',
        provider_name: 'cryptobot',
        support_excerpt: 'user pasted vless://sensitive-config',
      },
      contexts: {
        payment: {
          provider_payment_id: 'pay_123',
        },
        telegram: {
          initData: 'query_id=aa&hash=bb',
        },
        safe: {
          region: 'nl',
        },
      },
    } as unknown as ErrorEvent;

    const scrubbed = scrubSentryEvent(event);

    expect(scrubbed.request?.url).toBe('https://cyber-vpn.net/ru-RU/miniapp/plans');
    expect(scrubbed.request?.headers?.Authorization).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.Cookie).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['Set-Cookie']).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['X-Telegram-Bot-Api-Secret-Token']).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['X-Request-Id']).toBe('req-1');
    expect(scrubbed.request?.cookies).toBeUndefined();
    expect(scrubbed.request?.data).toBe('[Filtered]');
    expect(scrubbed.user).toEqual({ id: 'internal-user-id' });
    expect(scrubbed.extra?.oauthAccessToken).toBe('[Filtered]');
    expect(scrubbed.extra?.totpSecret).toBe('[Filtered]');
    expect(scrubbed.extra?.provider_name).toBe('cryptobot');
    expect(scrubbed.extra?.support_excerpt).toBe('[Filtered]');
    expect(scrubbed.contexts?.payment).toBe('[Filtered]');
    expect(scrubbed.contexts?.telegram?.initData).toBe('[Filtered]');
    expect(scrubbed.contexts?.safe?.region).toBe('nl');
  });
});
