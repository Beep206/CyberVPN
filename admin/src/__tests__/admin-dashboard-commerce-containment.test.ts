// @vitest-environment node

import fs from 'fs/promises';
import path from 'path';
import { describe, expect, it } from 'vitest';

const ADMIN_SRC_ROOT = path.resolve(__dirname, '..');

async function readSource(relativePath: string) {
  return fs.readFile(path.join(ADMIN_SRC_ROOT, relativePath), 'utf-8');
}

describe('admin dashboard commerce mobile containment contracts', () => {
  it('shrinks the dashboard flex shell before commerce routes render', async () => {
    const dashboardLayout = await readSource(
      'app/[locale]/(dashboard)/layout.tsx',
    );
    const terminalHeader = await readSource('widgets/terminal-header.tsx');

    expect(dashboardLayout).toContain(
      'flex min-h-dvh w-full max-w-full overflow-x-clip',
    );
    expect(dashboardLayout).toContain(
      'relative flex min-h-dvh min-w-0 max-w-full flex-1 flex-col overflow-x-clip md:pl-64',
    );
    expect(dashboardLayout).toContain(
      'relative z-10 min-w-0 max-w-full flex-1 overflow-x-clip',
    );
    expect(terminalHeader).toContain(
      'sticky top-0 z-30 min-w-0 max-w-full',
    );
    expect(terminalHeader).toContain(
      'flex h-16 w-full min-w-0 max-w-full',
    );
  });

  it('keeps commerce overflow local to navigation and table wrappers', async () => {
    const commerceLayout = await readSource(
      'app/[locale]/(dashboard)/commerce/layout.tsx',
    );
    const commerceSubnav = await readSource(
      'features/commerce/components/commerce-subnav.tsx',
    );
    const table = await readSource('shared/ui/organisms/table.tsx');

    expect(commerceLayout).toContain('min-w-0 max-w-full space-y-6');
    expect(commerceSubnav).toContain(
      'min-w-0 max-w-full overflow-x-auto overscroll-x-contain',
    );
    expect(table).toContain(
      'relative max-w-full overflow-auto overscroll-x-contain',
    );
    expect(table).toContain('w-full min-w-max caption-bottom text-sm');
  });
});
