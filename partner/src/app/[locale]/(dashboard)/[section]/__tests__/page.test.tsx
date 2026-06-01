import { beforeEach, describe, expect, it, vi } from 'vitest';
import RetiredPartnerSectionOverviewPage from '../page';

vi.mock('next/navigation', () => ({
  notFound: vi.fn(() => {
    throw new Error('NEXT_NOT_FOUND');
  }),
}));

const { notFound } = await import('next/navigation');

describe('retired partner section overview route', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns notFound so concrete partner sections remain the canonical owners', () => {
    expect(() => RetiredPartnerSectionOverviewPage()).toThrow('NEXT_NOT_FOUND');
    expect(notFound).toHaveBeenCalled();
  });
});
