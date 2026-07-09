// @vitest-environment node

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

async function readAdminSource(relativePath: string) {
  return readFile(path.join(process.cwd(), 'src', relativePath), 'utf-8');
}

describe('admin query invalidation call sites', () => {
  it('keeps withdrawal and support mutations wired to action-queue invalidation helpers', async () => {
    const withdrawals = await readAdminSource('features/commerce/components/withdrawals-console.tsx');
    const support = await readAdminSource('features/support/components/support-console.tsx');

    expect(withdrawals).toContain('invalidateAdminWithdrawalQueues(queryClient)');
    expect(support).toContain('invalidateAdminSupportQueues(queryClient, ticketRef)');
  });

  it('keeps plan and pricebook mutations wired to catalog-preview invalidation helpers', async () => {
    const plans = await readAdminSource('features/commerce/components/plans-console.tsx');
    const pricebooks = await readAdminSource('features/commerce/components/pricebooks-console.tsx');

    expect(plans.match(/invalidateAdminCommerceCatalogState\(queryClient\)/g)).toHaveLength(3);
    expect(pricebooks.match(/invalidateAdminCommerceCatalogState\(queryClient\)/g)).toHaveLength(2);
  });
});
