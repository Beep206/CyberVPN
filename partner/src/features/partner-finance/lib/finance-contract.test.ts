import { describe, expect, it } from 'vitest';
import {
  buildPartnerFinancePayoutAccountNotes,
  getPartnerFinancePayoutAccountCurrency,
  getPartnerFinancePayoutHistoryTone,
} from './finance-contract';

describe('partner finance contract helpers', () => {
  it('builds payout account notes from review and eligibility state', () => {
    const notes = buildPartnerFinancePayoutAccountNotes({
      account: {
        id: 'account_001',
        payout_rail: 'bank_wire',
        display_label: 'Primary USD wire',
        masked_destination: 'DE89...4400',
        destination_metadata: { currency: 'usd' },
        verification_status: 'pending',
        approval_status: 'pending',
        account_status: 'active',
        is_default: true,
        created_at: '2026-04-20T10:00:00Z',
        updated_at: '2026-04-20T11:00:00Z',
      },
      eligibility: {
        partner_payout_account_id: 'account_001',
        partner_account_id: 'workspace_001',
        eligible: false,
        reason_codes: ['payout_account_verification_pending'],
        blocking_risk_review_ids: [],
        active_reserve_ids: [],
        checked_at: '2026-04-20T12:00:00Z',
      },
    });

    expect(notes).toContain('DE89...4400');
    expect(notes).toContain('Verification is pending finance review.');
    expect(notes).toContain('Approval is still pending finance sign-off.');
    expect(notes).toContain('Currently selected as the default payout destination.');
    expect(notes).toContain(
      'Eligibility blockers: payout_account_verification_pending.',
    );
  });

  it('normalizes payout account currency and payout history tone', () => {
    expect(
      getPartnerFinancePayoutAccountCurrency({
        id: 'account_002',
        payout_rail: 'crypto_usdt',
        display_label: 'USDT wallet',
        masked_destination: '0x12...abcd',
        destination_metadata: { currency: 'usdt' },
        verification_status: 'verified',
        approval_status: 'approved',
        account_status: 'active',
        is_default: false,
        created_at: '2026-04-20T10:00:00Z',
        updated_at: '2026-04-20T11:00:00Z',
      }),
    ).toBe('USDT');

    expect(
      getPartnerFinancePayoutHistoryTone({
        id: 'history_001',
        instruction_id: 'instruction_001',
        execution_id: 'execution_001',
        partner_statement_id: 'statement_001',
        partner_payout_account_id: 'account_002',
        statement_key: '2026-04-US-01',
        payout_account_label: 'USDT wallet',
        amount: 128.5,
        currency_code: 'USD',
        lifecycle_status: 'failed',
        instruction_status: 'approved',
        execution_status: 'failed',
        execution_mode: 'live',
        external_reference: 'payout_123',
        created_at: '2026-04-20T10:00:00Z',
        updated_at: '2026-04-20T11:00:00Z',
        notes: [],
      }),
    ).toBe('failed');
  });
});
