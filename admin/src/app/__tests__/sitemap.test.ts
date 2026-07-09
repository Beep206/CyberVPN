import { describe, expect, it, vi } from 'vitest';
import sitemap from '../sitemap';

vi.mock('next/cache', () => ({
  cacheLife: vi.fn(),
  cacheTag: vi.fn(),
}));

describe('sitemap', () => {
  it('does not publish private admin or copied marketing routes', async () => {
    await expect(sitemap()).resolves.toEqual([]);
  });
});
