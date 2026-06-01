import { describe, expect, it } from 'vitest';
import {
  ADMIN_NAV_LABEL_FALLBACKS,
} from '@/features/admin-shell/config/admin-navigation';
import type {
  AdminNavigationMessageKey,
} from '@/features/admin-shell/config/admin-navigation';
import {
  buildAdminCommandPaletteResults,
  isSensitiveAdminCommandPaletteQuery,
} from '../admin-command-palette';

function labelFor(key: AdminNavigationMessageKey) {
  return ADMIN_NAV_LABEL_FALLBACKS[key];
}

describe('admin-command-palette providers', () => {
  it('builds route and entity results from the role-aware navigation registry', () => {
    const results = buildAdminCommandPaletteResults({
      role: 'admin',
      query: 'support',
      labelFor,
    });

    expect(results.map((result) => result.providerId)).toContain('routes');
    expect(results.map((result) => result.providerId)).toContain('entities');
    expect(results.some((result) => result.href === '/support')).toBe(true);
    expect(results.every((result) => result.searchText.length > 0)).toBe(true);
  });

  it('filters unavailable routes before returning palette results', () => {
    const results = buildAdminCommandPaletteResults({
      role: 'finance',
      query: 'add-ons',
      labelFor,
    });

    expect(results.map((result) => result.href)).not.toContain('/commerce/addons');
  });

  it('does not return hidden admin-permission destinations for lower roles', () => {
    const results = buildAdminCommandPaletteResults({
      role: 'viewer',
      query: 'admin invites',
      labelFor,
    });

    expect(results.map((result) => result.href)).not.toContain('/governance/admin-invites');
  });

  it('treats raw credentials, URLs, and emails as non-searchable input', () => {
    for (const query of [
      'Bearer abc.def.secret',
      'https://vpn.example.test/subscription/raw-token',
      'vmess://encoded-provider-payload',
      'customer@example.test',
    ]) {
      expect(isSensitiveAdminCommandPaletteQuery(query)).toBe(true);
      expect(
        buildAdminCommandPaletteResults({
          role: 'admin',
          query,
          labelFor,
        }),
      ).toEqual([]);
    }
  });

  it('marks write-risk destinations as review flows, not executable actions', () => {
    const results = buildAdminCommandPaletteResults({
      role: 'admin',
      query: 'withdrawals',
      labelFor,
    });

    expect(results.find((result) => result.href === '/commerce/withdrawals')?.risk).toBe(
      'write',
    );
  });
});
