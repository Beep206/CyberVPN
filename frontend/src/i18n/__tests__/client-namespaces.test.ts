import { describe, expect, it } from 'vitest';
import { DASHBOARD_CLIENT_NAMESPACES, MARKETING_CLIENT_NAMESPACES } from '../client-namespaces';

describe('client i18n namespace scopes', () => {
  it('keeps notification center messages available in dashboard and public headers', () => {
    expect(DASHBOARD_CLIENT_NAMESPACES).toContain('Messaging');
    expect(DASHBOARD_CLIENT_NAMESPACES).toContain('DeleteAccount');
    expect(DASHBOARD_CLIENT_NAMESPACES).toContain('Header');
    expect(MARKETING_CLIENT_NAMESPACES).toContain('Messaging');
  });

  it('keeps authenticated public header user menu messages available', () => {
    expect(MARKETING_CLIENT_NAMESPACES).toContain('Header');
  });
});
