// @vitest-environment node

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const APP_ROOT = path.join(process.cwd(), 'src/app');

async function readAppSource(relativePath: string) {
  return readFile(path.join(APP_ROOT, relativePath), 'utf-8');
}

describe('app query provider boundary', () => {
  it('keeps the React Query provider at the locale root for all partner surfaces', async () => {
    const localeLayout = await readAppSource('[locale]/layout.tsx');
    const dashboardLayout = await readAppSource('[locale]/(dashboard)/layout.tsx');
    const storefrontLayout = await readAppSource('[locale]/(storefront)/layout.tsx');

    expect(localeLayout).toContain("import { QueryProvider } from '@/app/providers/query-provider';");
    expect(localeLayout).toContain('<QueryProvider>');
    expect(localeLayout).toContain('</QueryProvider>');
    expect(dashboardLayout).not.toContain('QueryProvider');
    expect(storefrontLayout).not.toContain('QueryProvider');
  });
});
