import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const readSource = (path: string) =>
  readFileSync(resolve(process.cwd(), path), 'utf8');

describe('localized layout script scope', () => {
  it('does not load Telegram WebApp SDK from the root localized layout', () => {
    const source = readSource('src/app/[locale]/layout.tsx');

    expect(source).not.toContain('telegram.org/js/telegram-web-app.js');
  });

  it('keeps Telegram WebApp SDK scoped to the Mini App shell', () => {
    const source = readSource(
      'src/app/[locale]/miniapp/components/TelegramWebAppScript.tsx',
    );
    const layoutSource = readSource('src/app/[locale]/miniapp/layout.tsx');

    expect(source).toContain('telegram.org/js/telegram-web-app.js');
    expect(source).toContain('strategy="afterInteractive"');
    expect(layoutSource).toContain('<TelegramWebAppScript />');
  });
});
