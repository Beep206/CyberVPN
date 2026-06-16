import { describe, expect, it } from 'vitest';
import { formatCustomerPublicUid } from '../public-account-id';

describe('formatCustomerPublicUid', () => {
  it('formats valid customer public UIDs without truncation', () => {
    expect(formatCustomerPublicUid(14677650)).toBe('14677650');
    expect(formatCustomerPublicUid('14677650')).toBe('14677650');
    expect(formatCustomerPublicUid(' 14677650 ')).toBe('14677650');
  });

  it('rejects missing, out-of-range, and UUID-like values', () => {
    expect(formatCustomerPublicUid(null)).toBeNull();
    expect(formatCustomerPublicUid(undefined)).toBeNull();
    expect(formatCustomerPublicUid(9999999)).toBeNull();
    expect(formatCustomerPublicUid(100000000)).toBeNull();
    expect(formatCustomerPublicUid('7d871bc5-af6c-49b2-a3e6-e77eec938021')).toBeNull();
    expect(formatCustomerPublicUid('7d87...')).toBeNull();
  });
});
