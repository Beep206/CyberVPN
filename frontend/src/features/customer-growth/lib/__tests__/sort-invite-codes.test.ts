import { describe, expect, it } from 'vitest';

import { sortInviteCodes, type InviteCodeSortItem } from '../sort-invite-codes';

const NOW = Date.parse('2026-06-29T00:00:00Z');

function invite(overrides: InviteCodeSortItem): InviteCodeSortItem {
  return {
    id: 'invite-default',
    is_used: false,
    status: 'issued',
    created_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

describe('sortInviteCodes', () => {
  it('sorts active expiring codes before active lifetime codes and used or terminal codes', () => {
    const sorted = sortInviteCodes(
      [
        invite({
          id: 'revoked',
          status: 'revoked',
          revoked_at: '2026-06-28T00:00:00Z',
        }),
        invite({
          id: 'used-old',
          status: 'redeemed',
          is_used: true,
          used_at: '2026-06-20T00:00:00Z',
        }),
        invite({
          id: 'lifetime',
          expires_at: null,
        }),
        invite({
          id: 'expires-later',
          expires_at: '2026-07-10T00:00:00Z',
        }),
        invite({
          id: 'expired',
          status: 'expired',
          expires_at: '2026-06-01T00:00:00Z',
        }),
        invite({
          id: 'exhausted',
          status: 'exhausted',
          is_used: false,
          used_at: '2026-06-23T00:00:00Z',
        }),
        invite({
          id: 'used-new',
          status: 'used',
          is_used: true,
          used_at: '2026-06-25T00:00:00Z',
        }),
        invite({
          id: 'expires-sooner',
          expires_at: '2026-07-01T00:00:00Z',
        }),
      ],
      { now: NOW },
    );

    expect(sorted.map((item) => item.id)).toEqual([
      'expires-sooner',
      'expires-later',
      'lifetime',
      'used-new',
      'exhausted',
      'used-old',
      'expired',
      'revoked',
    ]);
  });

  it('prefers backend status_sort_order and falls back to created_at desc then id', () => {
    const sorted = sortInviteCodes(
      [
        invite({
          id: 'backend-first',
          status: 'revoked',
          status_sort_order: -1,
          created_at: '2026-06-01T00:00:00Z',
        }),
        invite({
          id: 'created-b',
          status: 'mystery',
          created_at: '2026-06-10T00:00:00Z',
        }),
        invite({
          id: 'created-a',
          status: 'mystery',
          created_at: '2026-06-10T00:00:00Z',
        }),
        invite({
          id: 'created-newer',
          status: 'mystery',
          created_at: '2026-06-11T00:00:00Z',
        }),
      ],
      { now: NOW },
    );

    expect(sorted.map((item) => item.id)).toEqual([
      'backend-first',
      'created-newer',
      'created-a',
      'created-b',
    ]);
  });
});
