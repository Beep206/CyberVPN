import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const SOURCE_ROOT = resolve(process.cwd(), 'src');

async function readSource(relativePath: string) {
  return readFile(resolve(SOURCE_ROOT, relativePath), 'utf8');
}

describe('DevButton accessibility wiring', () => {
  it('keeps the floating developer-tools icon button named from translated copy', async () => {
    const [buttonSource, clientSource, panelSource, layoutSource] = await Promise.all([
      readSource('features/dev/dev-button.tsx'),
      readSource('app/providers/dev-tools-client.tsx'),
      readSource('features/dev/dev-panel.tsx'),
      readSource('app/[locale]/layout.tsx'),
    ]);

    expect(buttonSource).toContain('aria-label={ariaLabel}');
    expect(buttonSource).toContain('type="button"');
    expect(clientSource).toContain('ariaLabel={openButtonLabel}');
    expect(panelSource).toContain('ariaLabel={openButtonLabel}');
    expect(panelSource).toContain('aria-label={closeButtonLabel}');
    expect(layoutSource).toContain("openButtonLabel={t('openDeveloperTools')}");
    expect(layoutSource).toContain("closeButtonLabel={t('closeDeveloperTools')}");
  });
});
