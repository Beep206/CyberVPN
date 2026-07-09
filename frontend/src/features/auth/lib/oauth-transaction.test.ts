import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  createProviderTransactionCookieValue,
  OAUTH_TRANSACTION_TTL_SECONDS,
  parseProviderTransactionCookieValue,
} from './oauth-transaction';

describe('OAuth transaction cookie', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
  });

  it('rejects a tampered signed transaction payload', () => {
    vi.stubEnv('OAUTH_TRANSACTION_SECRET', 'test-oauth-transaction-signing-key');

    const transaction = createProviderTransactionCookieValue('google', 'ru-RU', '/ru-RU/dashboard');
    const [encodedPayload, signature] = transaction.cookieValue.split('.');
    const payload = JSON.parse(
      Buffer.from(encodedPayload ?? '', 'base64url').toString('utf8'),
    ) as { returnTo: string };
    payload.returnTo = '/ru-RU/wallet';

    const tamperedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');

    expect(parseProviderTransactionCookieValue(`${tamperedPayload}.${signature}`)).toBeNull();
  });

  it('rejects an otherwise valid transaction after the TTL window', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-07-08T00:00:00.000Z'));
    vi.stubEnv('OAUTH_TRANSACTION_SECRET', 'test-oauth-transaction-signing-key');

    const transaction = createProviderTransactionCookieValue('github', 'ru-RU', '/ru-RU/dashboard');
    vi.setSystemTime(new Date(Date.now() + (OAUTH_TRANSACTION_TTL_SECONDS + 1) * 1000));

    expect(parseProviderTransactionCookieValue(transaction.cookieValue)).toBeNull();
  });
});
