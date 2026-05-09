import { describe, expect, it, vi } from 'vitest';
import AnalyticsPage from '../analytics/page';
import MonitoringPage from '../monitoring/page';
import PartnerPage from '../partner/page';
import UsersPage from '../users/page';

const { notFoundMock } = vi.hoisted(() => ({
  notFoundMock: vi.fn(() => {
    throw new Error('NEXT_NOT_FOUND');
  }),
}));

vi.mock('next/navigation', () => ({
  notFound: notFoundMock,
}));

describe('S1 customer dashboard operator surfaces', () => {
  it('hides analytics, monitoring, users, and partner pages from normal users', async () => {
    expect(() => AnalyticsPage()).toThrow('NEXT_NOT_FOUND');
    expect(() => MonitoringPage()).toThrow('NEXT_NOT_FOUND');
    expect(() => UsersPage()).toThrow('NEXT_NOT_FOUND');
    await expect(
      PartnerPage({ params: Promise.resolve({ locale: 'en-EN' }) }),
    ).rejects.toThrow('NEXT_NOT_FOUND');

    expect(notFoundMock).toHaveBeenCalledTimes(4);
  });
});
