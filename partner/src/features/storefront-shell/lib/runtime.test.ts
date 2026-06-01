import { describe, expect, it } from 'vitest';
import {
  isPortalWorkspacePath,
  isRetiredGenericPortalSectionPath,
  isStorefrontPublicPath,
  normalizeRequestHost,
  resolvePartnerSurfaceContext,
} from './runtime';

describe('storefront runtime resolution', () => {
  it('resolves portal hosts to the portal surface family', () => {
    const context = resolvePartnerSurfaceContext('partner.cyber-vpn.net');

    expect(context.family).toBe('portal');
    expect(context.authRealmKey).toBe('partner');
  });

  it('resolves the QA gate localhost port to the portal surface family', () => {
    expect(resolvePartnerSurfaceContext('127.0.0.1:3004').family).toBe('portal');
    expect(resolvePartnerSurfaceContext('localhost:3004').family).toBe('portal');
  });

  it('resolves dedicated storefront dev hosts to the storefront family', () => {
    const context = resolvePartnerSurfaceContext('storefront.localhost:3002');

    expect(context.family).toBe('storefront');
    if (context.family === 'storefront') {
      expect(context.storefrontKey).toBe('cybervpn-storefront');
      expect(context.routes.checkout).toBe('/checkout');
    }
  });

  it('treats unknown non-portal hosts as deterministic storefront aliases', () => {
    const context = resolvePartnerSurfaceContext('brand-a.example.com');

    expect(context.family).toBe('storefront');
    if (context.family === 'storefront') {
      expect(context.brandKey).toBe('brand-a');
      expect(context.host).toBe('brand-a.example.com');
    }
  });

  it('normalizes mixed-case request hosts', () => {
    expect(normalizeRequestHost('HTTPS://Storefront.Localhost:3002/checkout')).toBe('storefront.localhost:3002');
  });
});

describe('storefront route classification', () => {
  it('recognizes portal workspace paths', () => {
    expect(isPortalWorkspacePath('/ru-RU/dashboard')).toBe(true);
    expect(isPortalWorkspacePath('/en-EN/legal')).toBe(true);
  });

  it('recognizes storefront public paths', () => {
    expect(isStorefrontPublicPath('/ru-RU/checkout')).toBe(true);
    expect(isStorefrontPublicPath('/en-EN/support')).toBe(true);
    expect(isStorefrontPublicPath('/en-EN/legal-docs')).toBe(true);
  });

  it('recognizes retired generic portal section paths without catching active routes', () => {
    expect(isRetiredGenericPortalSectionPath('/en-EN/not-a-real-section')).toBe(true);
    expect(isRetiredGenericPortalSectionPath('/en-EN/dashboard')).toBe(false);
    expect(isRetiredGenericPortalSectionPath('/en-EN/login')).toBe(false);
    expect(isRetiredGenericPortalSectionPath('/en-EN/checkout')).toBe(false);
    expect(isRetiredGenericPortalSectionPath('/en-EN/not-a-real-section/deep')).toBe(false);
  });
});
