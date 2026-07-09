import { describe, expect, it } from 'vitest';
import type { ErrorEvent } from '@sentry/core';

import { scrubSentryEvent } from '../sentry-privacy';

describe('scrubSentryEvent', () => {
  it('redacts partner-sensitive request, identity, payment, checkout and config material', () => {
    const event = {
      request: {
        url: 'https://partners.cyber-vpn.net/storefront/checkout?token=secret#hash',
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
        id: 'partner-user-id',
        email: 'partner@example.com',
        username: 'partner-admin',
        ip_address: '127.0.0.1',
      },
      extra: {
        checkoutAttemptId: 'attempt-secret',
        oauthAccessToken: 'oauth-secret',
        provider_name: 'cryptobot',
        support_excerpt: 'customer pasted vless://sensitive-config',
      },
      contexts: {
        payment: {
          provider_payment_id: 'pay_123',
        },
        storefront: {
          checkoutUrl: '/checkout?token=secret',
        },
        safe: {
          route_group: 'storefront_checkout',
        },
      },
      tags: {
        checkoutToken: 'token-secret',
        route_group: 'storefront_checkout',
      },
      breadcrumbs: [
        {
          category: 'partner.checkout',
          data: {
            order_ready: 'yes',
            paymentUrl: 'https://gateway.local/pay?access_token=secret',
            vpn_config_path: '/api/v1/vpn/config/secret',
          },
          message: 'submitted vless://sensitive-config',
        },
      ],
      fingerprint: ['partner-runtime', 'password=secret'],
    } as unknown as ErrorEvent;

    const scrubbed = scrubSentryEvent(event);

    expect(scrubbed.request?.url).toBe('https://partners.cyber-vpn.net/storefront/checkout');
    expect(scrubbed.request?.headers?.Authorization).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.Cookie).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['Set-Cookie']).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['X-Telegram-Bot-Api-Secret-Token']).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['X-Request-Id']).toBe('req-1');
    expect(scrubbed.request?.cookies).toBeUndefined();
    expect(scrubbed.request?.data).toBe('[Filtered]');
    expect(scrubbed.user).toEqual({ id: 'partner-user-id' });
    expect(scrubbed.extra?.checkoutAttemptId).toBe('[Filtered]');
    expect(scrubbed.extra?.oauthAccessToken).toBe('[Filtered]');
    expect(scrubbed.extra?.provider_name).toBe('cryptobot');
    expect(scrubbed.extra?.support_excerpt).toBe('[Filtered]');
    expect(scrubbed.contexts?.payment).toBe('[Filtered]');
    expect(scrubbed.contexts?.storefront?.checkoutUrl).toBe('[Filtered]');
    expect(scrubbed.contexts?.safe?.route_group).toBe('storefront_checkout');
    expect(scrubbed.tags?.checkoutToken).toBe('[Filtered]');
    expect(scrubbed.tags?.route_group).toBe('storefront_checkout');
    expect(scrubbed.breadcrumbs?.[0]?.category).toBe('partner.checkout');
    expect(scrubbed.breadcrumbs?.[0]?.message).toBe('[Filtered]');
    expect(scrubbed.breadcrumbs?.[0]?.data?.order_ready).toBe('yes');
    expect(scrubbed.breadcrumbs?.[0]?.data?.paymentUrl).toBe('[Filtered]');
    expect(scrubbed.breadcrumbs?.[0]?.data?.vpn_config_path).toBe('[Filtered]');
    expect(scrubbed.fingerprint).toEqual(['partner-runtime', '[Filtered]']);
  });
});
