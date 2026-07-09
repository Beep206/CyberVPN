// @vitest-environment node

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

async function readPartnerSource(relativePath: string) {
  return readFile(path.join(process.cwd(), 'src', relativePath), 'utf-8');
}

describe('partner query invalidation call sites', () => {
  it('keeps finance mutations wired to finance summary and statement invalidation helpers', async () => {
    const finance = await readPartnerSource('features/partner-finance/components/finance-operations-page.tsx');

    expect(finance).toContain('invalidatePartnerFinanceState(queryClient, workspaceId)');
    expect(finance).toContain('invalidatePartnerPayoutAccountEligibility(queryClient, workspaceId, response.data.id)');
  });

  it('keeps storefront checkout retries scoped to one resumable logical attempt', async () => {
    const checkout = await readPartnerSource('features/storefront-shell/components/storefront-checkout-shell.tsx');

    expect(checkout).toContain('useRef<StorefrontCheckoutAttempt | null>(null)');
    expect(checkout).toContain('checkoutAttemptRef.current = attempt');
    expect(checkout).toContain('attempt.checkoutIdempotencyKey');
    expect(checkout).toContain('attempt.paymentAttemptIdempotencyKey');
    expect(checkout).toContain('attempt.quoteSessionId');
    expect(checkout).toContain('attempt.checkoutSessionId');
    expect(checkout).toContain('attempt.order = orderResponse.data');
    expect(checkout).toContain('checkoutAttemptRef.current = null');
  });
});
