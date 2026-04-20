import type {
  PartnerWorkspacePayoutAccountEligibilityResponse,
  PartnerWorkspacePayoutAccountResponse,
  PartnerWorkspacePayoutHistoryResponse,
} from '@/lib/api/partner-portal';

export type PartnerFinancePayoutHistoryTone =
  | 'pending_review'
  | 'queued'
  | 'in_flight'
  | 'paid'
  | 'blocked'
  | 'failed';

export function getPartnerFinancePayoutAccountCurrency(
  account: PartnerWorkspacePayoutAccountResponse,
): string {
  const currency = account.destination_metadata?.currency;
  return typeof currency === 'string' && currency.trim().length > 0
    ? currency.toUpperCase()
    : 'USD';
}

export function buildPartnerFinancePayoutAccountNotes({
  account,
  eligibility,
}: {
  account: PartnerWorkspacePayoutAccountResponse;
  eligibility?: PartnerWorkspacePayoutAccountEligibilityResponse | null;
}): string[] {
  const notes = [account.masked_destination];

  if (account.verification_status !== 'verified') {
    notes.push('Verification is pending finance review.');
  }

  if (account.approval_status !== 'approved') {
    notes.push('Approval is still pending finance sign-off.');
  }

  if (account.account_status === 'suspended') {
    notes.push(
      account.suspension_reason_code
        ? `Suspended: ${account.suspension_reason_code}.`
        : 'Suspended by finance or governance.',
    );
  }

  if (account.account_status === 'archived') {
    notes.push(
      account.archive_reason_code
        ? `Archived: ${account.archive_reason_code}.`
        : 'Archived and no longer eligible for payout execution.',
    );
  }

  if (account.is_default) {
    notes.push('Currently selected as the default payout destination.');
  }

  if (eligibility) {
    if (eligibility.eligible) {
      notes.push('Eligible for payout execution when a closed statement is available.');
    } else if (eligibility.reason_codes.length > 0) {
      notes.push(`Eligibility blockers: ${eligibility.reason_codes.join(', ')}.`);
    }
  }

  return notes;
}

export function getPartnerFinancePayoutHistoryTone(
  item: PartnerWorkspacePayoutHistoryResponse,
): PartnerFinancePayoutHistoryTone {
  switch (item.lifecycle_status) {
    case 'queued':
      return 'queued';
    case 'in_flight':
      return 'in_flight';
    case 'paid':
      return 'paid';
    case 'blocked':
      return 'blocked';
    case 'failed':
      return 'failed';
    default:
      return 'pending_review';
  }
}
