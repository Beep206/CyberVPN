import { beforeEach, describe, expect, it, vi } from 'vitest';

const getRequestConfig = vi.fn(<T>(factory: T) => factory);

vi.mock('next-intl/server', () => ({
  getRequestConfig,
}));

describe('i18n request config', () => {
  beforeEach(() => {
    vi.resetModules();
    getRequestConfig.mockClear();
  });

  it('resolves the locale from requestLocale for locale-based routes', async () => {
    const { default: createRequestConfig } = await import('../request');

    const config = await createRequestConfig({
      requestLocale: Promise.resolve('ru-RU'),
    });

    expect(config.locale).toBe('ru-RU');
    const messages = config.messages;
    expect(messages).toBeDefined();
    if (!messages) {
      throw new Error('Expected localized messages to be loaded');
    }

    expect(messages.Header).toMatchObject({
      netUplink: 'СЕТЬ_АПЛИНК',
    });
    expect(messages.Footer).toMatchObject({
      links: {
        privacy: 'Политика конфиденциальности',
      },
    });
    expect(messages.Auth).toMatchObject({
      login: {
        submitButton: 'Войти',
      },
    });
  });

  it('falls back to the default locale for unknown requestLocale values', async () => {
    const { default: createRequestConfig } = await import('../request');

    const config = await createRequestConfig({
      requestLocale: Promise.resolve('unknown-locale'),
    });

    expect(config.locale).toBe('en-EN');
    const messages = config.messages;
    expect(messages).toBeDefined();
    if (!messages) {
      throw new Error('Expected fallback messages to be loaded');
    }

    expect(messages.Header).toMatchObject({
      netUplink: 'NET_UPLINK',
    });
  });
});
