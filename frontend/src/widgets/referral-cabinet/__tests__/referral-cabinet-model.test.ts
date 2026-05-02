import { describe, expect, it } from 'vitest';
import {
  buildReferralLink,
  buildShareText,
  formatDate,
  formatLabel,
  formatMoney,
  formatPercent,
  formatShortId,
  getCapProgress,
  getReferralProgramHealth,
  getRewardAmountByStatus,
  getRewardTone,
  mergeRewardTimeline,
  summarizeRewardTimeline,
  type ReferralCommission,
  type ReferralReward,
} from '../referral-cabinet-model';

const reward = (overrides: Partial<ReferralReward>): ReferralReward => ({
  available_at: null,
  created_at: '2026-04-24T10:00:00Z',
  currency: 'USD',
  hold_until: null,
  id: 'reward-1',
  payment_id: null,
  referred_user_id: 'user-2',
  reversed_at: null,
  reward_amount: 10,
  reward_status: 'available',
  ...overrides,
});

const commission = (overrides: Partial<ReferralCommission>): ReferralCommission => ({
  available_at: null,
  base_amount: 100,
  commission_amount: 10,
  commission_rate: 0.1,
  created_at: '2026-04-24T09:00:00Z',
  currency: 'USD',
  hold_until: null,
  id: 'commission-1',
  referred_user_id: 'user-3',
  reversed_at: null,
  reward_status: 'pending',
  source_model: 'legacy_commission',
  ...overrides,
});

describe('referral-cabinet-model', () => {
  it('builds referral links and share text without guessing backend eligibility', () => {
    const link = buildReferralLink({
      code: 'ABC 123',
      origin: 'https://cybervpn.example/',
    });

    expect(link).toBe('https://cybervpn.example/referral?code=ABC%20123');
    expect(buildShareText('Use {code}: {link}', 'ABC123', link)).toBe(
      'Use ABC123: https://cybervpn.example/referral?code=ABC%20123',
    );
    expect(buildReferralLink({ code: '  CODE+PLUS  ' })).toBe(
      'https://cybervpn.example/referral?code=CODE%2BPLUS',
    );
    expect(
      buildReferralLink({
        code: 'VIP',
        fallbackOrigin: 'https://fallback.example/',
        origin: '',
      }),
    ).toBe('/referral?code=VIP');
  });

  it('normalizes reward lifecycle statuses and tones', () => {
    expect(getRewardTone('available')).toBe('green');
    expect(getRewardTone('blocked_by_risk')).toBe('amber');
    expect(getRewardTone('expired')).toBe('muted');
    expect(getRewardTone('pending')).toBe('cyan');
    expect(getRewardTone('reversed')).toBe('pink');
    expect(getRewardTone('allocated')).toBe('cyan');
    expect(getRewardTone('unknown')).toBe('cyan');
    expect(getRewardTone(null)).toBe('cyan');
  });

  it('merges rewards and commissions into newest-first lifecycle timeline', () => {
    const timeline = mergeRewardTimeline({
      commissions: [
        commission({
          available_at: '2026-04-30T00:00:00Z',
          created_at: 'not-a-date',
          currency: '',
          hold_until: '2026-04-29T00:00:00Z',
          id: 'commission-invalid-date',
          reward_status: 'reversed',
        }),
        commission({ created_at: '2026-04-24T09:00:00Z' }),
      ],
      rewards: [
        reward({
          created_at: '2026-04-25T09:00:00Z',
          currency: 'eur',
          id: 'reward-new',
          reward_status: 'blocked_by_risk',
        }),
        reward({
          created_at: '2026-04-23T09:00:00Z',
          id: 'reward-expired',
          referred_user_id: null,
          reward_amount: 3,
          reward_status: 'expired',
        }),
      ],
    });

    expect(timeline.map((item) => item.id)).toEqual([
      'reward-new',
      'commission-1',
      'reward-expired',
      'commission-invalid-date',
    ]);
    expect(timeline[0]).toMatchObject({
      currency: 'EUR',
      source: 'reward',
      status: 'blocked_by_risk',
    });
    expect(timeline[3]).toMatchObject({
      currency: 'USD',
      holdUntil: '2026-04-29T00:00:00Z',
      source: 'commission',
      status: 'reversed',
    });
    expect(timeline[2]).toMatchObject({
      referredUserId: null,
      source: 'reward',
      status: 'expired',
    });
    expect(summarizeRewardTimeline(timeline)).toMatchObject({
      blocked_by_risk: 1,
      expired: 1,
      pending: 1,
      reversed: 1,
    });
    expect(getRewardAmountByStatus(timeline, 'blocked_by_risk')).toBe(10);
    expect(getRewardAmountByStatus(timeline, 'expired')).toBe(3);
  });

  it('calculates program health, caps and percent labels', () => {
    expect(
      getReferralProgramHealth({
        status: { commission_rate: 0.1, enabled: false, friend_discount_pct: 10, reward_hold_days: 7 },
      }),
    ).toBe('disabled');
    expect(
      getReferralProgramHealth({
        stats: {
          available_rewards_usd: 0,
          commission_rate: 0.1,
          lifetime_cap_used_usd: 0,
          monthly_cap_used_usd: 0,
          pending_rewards_usd: 10,
          qualifying_orders: 1,
          reversed_rewards_usd: 0,
          total_earned: 10,
          total_referrals: 1,
        },
        status: { commission_rate: 0.1, enabled: true, friend_discount_pct: 10, reward_hold_days: 7 },
      }),
    ).toBe('review');
    expect(
      getReferralProgramHealth({
        stats: {
          available_rewards_usd: 5,
          commission_rate: 0.1,
          lifetime_cap_used_usd: 0,
          monthly_cap_used_usd: 0,
          pending_rewards_usd: 0,
          qualifying_orders: 1,
          reversed_rewards_usd: 0,
          total_earned: 5,
          total_referrals: 0,
        },
        status: { commission_rate: 0.1, enabled: true, friend_discount_pct: 10, reward_hold_days: 7 },
      }),
    ).toBe('earning');
    expect(
      getReferralProgramHealth({
        stats: {
          available_rewards_usd: 0,
          commission_rate: 0.1,
          lifetime_cap_used_usd: 0,
          monthly_cap_used_usd: 0,
          pending_rewards_usd: 0,
          qualifying_orders: 0,
          reversed_rewards_usd: 0,
          total_earned: 0,
          total_referrals: 2,
        },
      }),
    ).toBe('earning');
    expect(getReferralProgramHealth({})).toBe('active');
    expect(getCapProgress(25, 100)).toBe(25);
    expect(getCapProgress(150, 100)).toBe(100);
    expect(getCapProgress(0, 100)).toBe(0);
    expect(getCapProgress(Number.NaN, 100)).toBe(0);
    expect(getCapProgress(50, 0)).toBe(0);
    expect(formatPercent(0.125, 'en-EN')).toBe('12.5%');
    expect(formatPercent(12.5, 'en-EN')).toBe('12.5%');
    expect(formatPercent(null, 'en-EN')).toBe('0%');
  });

  it('formats referral money, dates, labels and short identifiers safely', () => {
    expect(formatMoney('en-EN', 10, 'usd')).toBe('$10');
    expect(formatMoney('en-EN', 10.25, 'USD')).toBe('$10.25');
    expect(formatMoney('en-EN', Number.NaN, 'USD')).toBe('$0');
    expect(formatMoney('en-EN', 12, 'bad-code')).toBe('12.00 BAD-CODE');
    expect(formatDate('2026-04-24T00:00:00Z', 'en-EN')).toBe('Apr 24, 2026');
    expect(formatDate(null, 'en-EN')).toBeNull();
    expect(formatDate('not-a-date', 'en-EN')).toBeNull();
    expect(formatShortId(null)).toBe('n/a');
    expect(formatShortId('   ')).toBe('n/a');
    expect(formatShortId('short-id')).toBe('short-id');
    expect(formatShortId('1234567890abcdef')).toBe('12345678...');
    expect(formatLabel('blocked_by-risk', 'Fallback')).toBe('Blocked By Risk');
    expect(formatLabel('   ', 'Fallback')).toBe('Fallback');
  });
});
