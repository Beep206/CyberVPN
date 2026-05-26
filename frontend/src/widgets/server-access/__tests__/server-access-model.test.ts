import { describe, expect, it } from 'vitest';
import type {
  CurrentServiceState,
  ProfileResponse,
  RawServer,
  UserConfig,
} from '../server-access-model';
import {
  extractConfigLinks,
  formatBytes,
  getConfigAvailability,
  getConfigDeliveryBundle,
  getRecommendedServer,
  isServiceStateActive,
  isUsableServer,
  maskConfigValue,
  rankServers,
  summarizeServers,
} from '../server-access-model';

function server(overrides: Partial<RawServer>): RawServer {
  return {
    active_plugin_uuid: null,
    address: '10.0.0.1',
    country_code: 'DE',
    created_at: '2026-04-24T00:00:00Z',
    inbound_count: 2,
    is_connected: true,
    is_disabled: false,
    name: 'Berlin Gateway',
    node_version: '2.0.0',
    port: 443,
    status: 'online',
    traffic_used_bytes: 1024,
    updated_at: '2026-04-24T00:00:00Z',
    users_online: 12,
    uuid: 'server-1',
    vpn_protocol: 'vless',
    xray_version: '1.8.0',
    ...overrides,
  };
}

const profile: ProfileResponse = {
  avatar_url: null,
  display_name: 'Alice',
  email: 'alice@example.com',
  id: 'user-1',
  language: 'en',
  timezone: 'UTC',
  updated_at: '2026-04-24T00:00:00Z',
};

const serviceState = {
  access_delivery_channel: {
    channel_status: 'active',
  },
  device_credential: {
    credential_status: 'active',
  },
  provisioning_profile: {
    profile_key: 'default',
  },
  service_identity: {
    identity_status: 'active',
  },
} as CurrentServiceState;

describe('server access model', () => {
  it('ranks usable low-load servers before fallbacks', () => {
    const overloaded = server({
      name: 'Tokyo Busy',
      traffic_used_bytes: 9000,
      users_online: 95,
      uuid: 'server-2',
    });
    const disabled = server({
      is_disabled: true,
      name: 'Disabled Node',
      users_online: 1,
      uuid: 'server-3',
    });
    const preferred = server({
      name: 'Berlin Calm',
      traffic_used_bytes: 100,
      users_online: 10,
      uuid: 'server-4',
    });

    expect(rankServers([overloaded, disabled, preferred]).map((item) => item.name)).toEqual([
      'Berlin Calm',
      'Tokyo Busy',
      'Disabled Node',
    ]);
    expect(getRecommendedServer([overloaded, disabled, preferred])?.name).toBe('Berlin Calm');
    expect(isUsableServer(disabled)).toBe(false);
  });

  it('summarizes regions, protocols, and connection readiness', () => {
    const summary = summarizeServers([
      server({ country_code: 'DE', vpn_protocol: 'vless', uuid: 'server-1' }),
      server({ country_code: 'JP', is_connected: false, vpn_protocol: 'wireguard', uuid: 'server-2' }),
      server({ country_code: 'DE', is_disabled: true, vpn_protocol: 'vless', uuid: 'server-3' }),
    ]);

    expect(summary).toMatchObject({
      connected: 2,
      countries: ['DE', 'JP'],
      disabled: 1,
      online: 3,
      protocols: ['VLESS', 'WIREGUARD'],
      total: 3,
    });
  });

  it('extracts unique config links and keeps raw config as a fallback', () => {
    const config: UserConfig = {
      config: 'vless://raw-config-value',
      isFound: true,
      links: ['vless://one', 'vless://one'],
      ssConfLinks: {
        primary: 'ss://primary',
      },
      subscriptionUrl: 'https://vpn.example/sub/user-1',
    };

    expect(extractConfigLinks(config).map((link) => link.value)).toEqual([
      'https://vpn.example/sub/user-1',
      'vless://one',
      'ss://primary',
      'vless://raw-config-value',
    ]);
  });

  it('uses access delivery payload as a fallback config source', () => {
    const deliveryState = {
      ...serviceState,
      access_delivery_channel: {
        channel_status: 'active',
        delivery_payload: {
          connection_links: ['vless://payload-link'],
          raw_config: 'vless://payload-raw-config',
          subscription_url: 'https://delivery.example/sub/token',
        },
      },
    } as CurrentServiceState;

    const links = extractConfigLinks(null, deliveryState);
    const bundle = getConfigDeliveryBundle(links);

    expect(links.map((link) => link.value)).toEqual([
      'https://delivery.example/sub/token',
      'vless://payload-link',
      'vless://payload-raw-config',
    ]);
    expect(bundle.subscriptionLink?.value).toBe('https://delivery.example/sub/token');
    expect(bundle.qrLink?.value).toBe('https://delivery.example/sub/token');
    expect(bundle.configFile?.value).toBe('vless://payload-raw-config');
    expect(
      getConfigAvailability({
        config: null,
        profile,
        serviceState: deliveryState,
      }),
    ).toBe('ready');
  });

  it('derives config availability from profile, service state, and upstream response', () => {
    expect(
      getConfigAvailability({
        config: null,
        profile: null,
        serviceState,
      }),
    ).toBe('missing_profile');
    expect(
      getConfigAvailability({
        config: null,
        profile,
        serviceState: null,
      }),
    ).toBe('missing_service');
    expect(
      getConfigAvailability({
        config: { config: '', isFound: false },
        profile,
        serviceState,
      }),
    ).toBe('not_found');
    expect(
      getConfigAvailability({
        config: { config: '', isFound: true, subscriptionUrl: 'https://vpn.example/sub' },
        profile,
        serviceState,
      }),
    ).toBe('ready');
    expect(
      getConfigAvailability({
        config: { config: '', isFound: true, subscriptionUrl: 'https://vpn.example/sub' },
        profile,
        serviceState: null,
      }),
    ).toBe('ready');
  });

  it('formats public values without leaking full config secrets', () => {
    expect(formatBytes(1536, 'en-EN')).toBe('1.5 KB');
    expect(maskConfigValue('https://vpn.example/sub/user-1?token=secret')).toBe(
      'https://vpn.example/...',
    );
    expect(maskConfigValue('vless://abcdefghijklmnopqrstuvwxyz1234567890')).toBe(
      'vless://...567890',
    );
    expect(isServiceStateActive(serviceState)).toBe(true);
  });
});
