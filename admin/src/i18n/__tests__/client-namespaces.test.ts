import { describe, expect, it } from 'vitest';
import { DASHBOARD_CLIENT_NAMESPACES } from '../client-namespaces';

describe('dashboard client namespaces', () => {
  it('ships Support messages to dashboard client routes', () => {
    expect(DASHBOARD_CLIENT_NAMESPACES).toContain('Support');
  });
});
