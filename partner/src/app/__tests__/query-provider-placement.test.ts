// @vitest-environment node

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

function readPartnerFile(path: string): string {
  return readFileSync(resolve(process.cwd(), path), 'utf8');
}

describe('partner query provider placement', () => {
  it('keeps root client providers above dashboard, storefront, and dev tools', () => {
    const localeLayout = readPartnerFile('src/app/[locale]/layout.tsx');
    const dashboardLayout = readPartnerFile('src/app/[locale]/(dashboard)/layout.tsx');
    const storefrontLayout = readPartnerFile('src/app/[locale]/(storefront)/layout.tsx');
    const queryProvider = readPartnerFile('src/app/providers/query-provider.tsx');

    expect(localeLayout).toContain("import { ScopedIntlProvider } from '@/app/providers/scoped-intl-provider';");
    expect(localeLayout).toContain("import { QueryProvider } from '@/app/providers/query-provider';");
    expect(localeLayout).toContain('<ScopedIntlProvider locale={locale} namespaces={ROOT_CLIENT_NAMESPACES}>');
    expect(localeLayout).toContain('<QueryProvider>');
    expect(localeLayout).toContain('{isDevelopment ? <DevTools /> : null}');
    expect(dashboardLayout).not.toContain('@/app/providers/query-provider');
    expect(storefrontLayout).not.toContain('@/app/providers/query-provider');
    expect(queryProvider).toContain('queryClientDefaultOptions');
    expect(queryProvider).not.toContain('@tanstack/react-query-devtools');
    expect(queryProvider).not.toContain('ReactQueryDevtools');
  });
});
