import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { adminWalletApi } from '../wallet';

describe('partner admin wallet surface policy', () => {
  beforeEach(() => {
    window.location.href = 'http://portal.localhost:3002/en-EN/dashboard';
  });

  afterEach(() => {
    window.location.href = 'http://portal.localhost:3002/en-EN/dashboard';
  });

  it('blocks pending withdrawal moderation calls on the partner portal surface', () => {
    expect(() => adminWalletApi.getPendingWithdrawals()).toThrow(
      /internal_admin_moderation is not allowed on portal surface/i,
    );
  });

  it('blocks maker-checker approval calls on the partner portal surface', () => {
    expect(() => adminWalletApi.approveWithdrawal('withdrawal_001')).toThrow(
      /maker_checker_controls is not allowed on portal surface/i,
    );
  });
});
