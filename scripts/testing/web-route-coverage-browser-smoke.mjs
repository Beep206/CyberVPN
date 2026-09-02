import { spawn, spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { mkdir, mkdtemp, readdir, rm, writeFile } from 'node:fs/promises';
import http from 'node:http';
import https from 'node:https';
import { tmpdir } from 'node:os';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const LOCALE = readCliOption('locale') || 'en-EN';
const SURFACE = readCliOption('surface') || process.env.WEB_ROUTE_SMOKE_SURFACE || 'frontend';
const START_SERVER = readBooleanOption('start-server') || process.env.WEB_ROUTE_SMOKE_START_SERVER === '1';
const ROUTE_LIMIT = readNumberOption('route-limit', 0);
const ROUTE_FILTERS = readCliOptions('route');
const GROUP_FILTER = readCliOption('group');
const OUTPUT_PATH = readCliOption('output');
const VERBOSE = readBooleanOption('verbose') || process.env.WEB_ROUTE_SMOKE_VERBOSE === '1';
const LIVE_API = readBooleanOption('live-api') || process.env.WEB_ROUTE_SMOKE_LIVE_API === '1';
const EXPECTED_API_SUBSTRINGS = readCliOptions('expect-api');
const CHROMIUM_BIN = process.env.CHROMIUM_BIN || findChromium();
const ASSERTION_TIMEOUT_MS = readNumberEnv('WEB_ROUTE_SMOKE_ASSERTION_TIMEOUT_MS', 15_000);
const NAVIGATION_TIMEOUT_MS = readNumberEnv('WEB_ROUTE_SMOKE_NAVIGATION_TIMEOUT_MS', 45_000);
const SERVER_READY_TIMEOUT_MS = readNumberEnv('WEB_ROUTE_SMOKE_SERVER_READY_TIMEOUT_MS', 120_000);
const ROUTE_SETTLE_MS = readNumberEnv('WEB_ROUTE_SMOKE_ROUTE_SETTLE_MS', 800);
const CDP_COMMAND_TIMEOUT_MS = readNumberEnv('WEB_ROUTE_SMOKE_CDP_COMMAND_TIMEOUT_MS', 10_000);
const LIVE_AUTH_TIMEOUT_MS = readNumberEnv('WEB_ROUTE_SMOKE_LIVE_AUTH_TIMEOUT_MS', 15_000);
const BROWSER_ROUTE_BATCH_SIZE = readNumberOption(
  'browser-batch-size',
  readNumberEnv('WEB_ROUTE_SMOKE_BROWSER_BATCH_SIZE', LIVE_API ? 20 : 0),
);

const PARTNER_SMOKE_WORKSPACE_UUID = '10000000-0000-4000-8000-000000000001';
const PARTNER_SMOKE_PROFILE_UUID = '20000000-0000-4000-8000-000000000001';
const PARTNER_SMOKE_INTEGRATION_UUID = '20000000-0000-4000-8000-000000000002';
const PARTNER_SMOKE_MUTATION_ATTEMPT_UUID = '30000000-0000-4000-8000-000000000001';
const PARTNER_SMOKE_ROLE_PERMISSIONS = Object.freeze([
  'workspace_read',
  'operations_write',
  'membership_read',
  'membership_write',
  'codes_read',
  'codes_write',
  'earnings_read',
  'payouts_read',
  'payouts_write',
  'traffic_read',
  'traffic_write',
  'integrations_read',
  'integrations_write',
  'remnawave_read',
  'remnawave_write',
]);

const SURFACE_CONFIGS = {
  frontend: {
    workspace: 'frontend',
    defaultBaseUrl: 'http://127.0.0.1:9001',
    expectedAuthCookies: ['customer_access_token', 'customer_refresh_token'],
    expectedRealm: 'customer',
    expectedPrincipalType: 'customer',
    expectedScopeFamily: 'customer',
    port: 9001,
    sessionUser: {
      id: 'smoke-customer',
      email: 'customer-smoke@example.invalid',
      login: 'customer-smoke',
      is_active: true,
      is_email_verified: true,
      role: 'viewer',
      created_at: '2026-06-03T00:00:00.000Z',
    },
    skipRoute(route) {
      return route.cleanSegments[0]?.startsWith('test-') || route.cleanSegments[0] === 'widgets';
    },
  },
  admin: {
    workspace: 'admin',
    defaultBaseUrl: 'http://127.0.0.1:3001',
    expectedAuthCookies: ['access_token', 'refresh_token'],
    expectedRealm: 'admin',
    expectedPrincipalType: 'admin',
    expectedScopeFamily: 'admin',
    port: 3001,
    sessionUser: {
      id: 'smoke-admin',
      email: 'admin-smoke@example.invalid',
      login: 'admin-smoke',
      is_active: true,
      is_email_verified: true,
      role: 'super_admin',
      permissions: ['*'],
      created_at: '2026-06-03T00:00:00.000Z',
    },
  },
  partner: {
    workspace: 'partner',
    defaultBaseUrl: 'http://127.0.0.1:3002',
    storefrontBaseUrl: 'http://storefront.localhost:3002',
    expectedAuthCookies: ['partner_access_token', 'partner_refresh_token'],
    expectedRealm: 'partner',
    expectedPrincipalType: 'partner_operator',
    expectedScopeFamily: 'partner',
    port: 3002,
    sessionUser: {
      id: 'smoke-partner',
      email: 'partner-smoke@example.invalid',
      login: 'partner-smoke',
      is_active: true,
      is_email_verified: true,
      role: 'partner_operator',
      auth_realm_key: 'partner',
      audience: 'cybervpn:partner',
      principal_type: 'partner_operator',
      created_at: '2026-06-03T00:00:00.000Z',
    },
  },
};

const CONFIG = SURFACE_CONFIGS[SURFACE];
assert(CONFIG, `Unknown surface "${SURFACE}". Expected one of ${Object.keys(SURFACE_CONFIGS).join(', ')}.`);

const BASE_URL = trimTrailingSlash(readCliOption('base-url') || process.env.WEB_ROUTE_SMOKE_BASE_URL || CONFIG.defaultBaseUrl);
const STOREFRONT_BASE_URL = trimTrailingSlash(
  readCliOption('storefront-base-url') ||
    process.env.WEB_ROUTE_SMOKE_STOREFRONT_BASE_URL ||
    CONFIG.storefrontBaseUrl ||
    BASE_URL,
);
const AUTH_CONNECT_BASE_URL = trimTrailingSlash(
  readCliOption('auth-connect-base-url') ||
    process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_CONNECT_BASE_URL`] ||
    process.env.AUTH_BFF_SMOKE_CONNECT_BASE_URL ||
    process.env.WEB_ROUTE_SMOKE_AUTH_CONNECT_BASE_URL ||
    BASE_URL,
);
const AUTH_HOST_HEADER =
  readCliOption('auth-host-header') ||
  process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_HOST_HEADER`] ||
  process.env.AUTH_BFF_SMOKE_HOST_HEADER ||
  process.env.WEB_ROUTE_SMOKE_AUTH_HOST_HEADER ||
  (AUTH_CONNECT_BASE_URL !== BASE_URL ? new URL(BASE_URL).host : null);
const AUTH_IDENTIFIER =
  readCliOption('identifier') ||
  process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_IDENTIFIER`] ||
  process.env.AUTH_BFF_SMOKE_IDENTIFIER ||
  process.env.WEB_ROUTE_SMOKE_IDENTIFIER;
const AUTH_PASSWORD =
  readCliOption('password') ||
  process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_PASSWORD`] ||
  process.env.AUTH_BFF_SMOKE_PASSWORD ||
  process.env.WEB_ROUTE_SMOKE_PASSWORD;
const AUTH_TOTP_CODE =
  readCliOption('totp-code') ||
  process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_TOTP_CODE`] ||
  process.env.AUTH_BFF_SMOKE_TOTP_CODE ||
  process.env.WEB_ROUTE_SMOKE_TOTP_CODE;
const CONNECT_BASE_URL = trimTrailingSlash(
  readCliOption('connect-base-url') ||
    process.env.WEB_ROUTE_SMOKE_CONNECT_BASE_URL ||
    (LIVE_API ? AUTH_CONNECT_BASE_URL : BASE_URL),
);
const DEV_PORT = Number(new URL(BASE_URL).port) || CONFIG.port;
const LOCALE_PATH_PATTERN = /^\/[a-z]{2,3}-[A-Z]{2}(?:\/|$)/;

const DYNAMIC_SEGMENT_SAMPLES = {
  compare: ['vless-reality-vs-wireguard', 'sing-box-vs-clash-meta-for-advanced-routing'],
  devices: [
    'android-vpn-setup',
    'ios-vpn-setup',
    'windows-vpn-setup',
    'macos-vpn-setup',
    'linux-vpn-setup',
    'telegram-mini-app-vpn-setup',
  ],
  guides: [
    'how-to-bypass-dpi-with-vless-reality',
    'vpn-speed-optimization-for-streaming-and-gaming',
    'zero-log-vpn-rollout-checklist-for-teams',
  ],
  customers: ['smoke-user-001'],
  messaging: ['smoke-conversation-001'],
  'privacy-requests': ['PRIV-2026-001'],
  support: ['SUP-2026-001'],
};
const LIVE_ROUTE_SAMPLE_OVERRIDES = LIVE_API ? loadRouteSampleOverrides() : {};

const ADMIN_SECTION_SLUGS = [
  'customers',
  'commerce',
  'growth',
  'infrastructure',
  'security',
  'governance',
  'integrations',
];

const SURFACE_SECTION_SAMPLES = {
  admin: [],
  // partner/[section] is a retired catch-all that intentionally returns notFound.
  // Canonical partner sections are concrete route files and are discovered below.
  partner: [],
};

const API_ROUTE_FIXTURES = {
  customer: buildCustomerSessionFixture(),
  admin: buildAdminSessionFixture(),
  partner: buildPartnerSessionFixture(),
  workspace: buildPartnerWorkspaceFixture(),
};

function readCliOption(name) {
  const prefix = `--${name}=`;
  const exact = `--${name}`;
  const index = process.argv.findIndex((arg) => arg === exact || arg.startsWith(prefix));
  if (index === -1) {
    return null;
  }
  const arg = process.argv[index];
  return arg.startsWith(prefix) ? arg.slice(prefix.length) : process.argv[index + 1] ?? null;
}

function readCliOptions(name) {
  const prefix = `--${name}=`;
  const exact = `--${name}`;
  const values = [];

  for (let index = 0; index < process.argv.length; index += 1) {
    const arg = process.argv[index];
    if (arg.startsWith(prefix)) {
      values.push(arg.slice(prefix.length));
      continue;
    }
    if (arg === exact && process.argv[index + 1]) {
      values.push(process.argv[index + 1]);
      index += 1;
    }
  }

  return values.filter(Boolean);
}

function readBooleanOption(name) {
  return process.argv.includes(`--${name}`);
}

function readNumberOption(name, fallback) {
  const raw = readCliOption(name);
  if (!raw) {
    return fallback;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function readNumberEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function loadRouteSampleOverrides() {
  const candidates = [];
  if (process.env.WEB_ROUTE_SMOKE_DYNAMIC_SAMPLES_JSON) {
    candidates.push({
      source: 'WEB_ROUTE_SMOKE_DYNAMIC_SAMPLES_JSON',
      required: true,
      payload: process.env.WEB_ROUTE_SMOKE_DYNAMIC_SAMPLES_JSON,
    });
  }

  const configuredFile = process.env.WEB_ROUTE_SMOKE_DYNAMIC_SAMPLES_FILE;
  const sampleFile = configuredFile || join(REPO_ROOT, '.private', `latest-${SURFACE}-smoke.json`);
  if (existsSync(sampleFile)) {
    candidates.push({
      source: sampleFile,
      required: Boolean(configuredFile),
      payload: readFileSync(sampleFile, 'utf8'),
    });
  }

  for (const candidate of candidates) {
    let parsed;
    try {
      parsed = JSON.parse(candidate.payload);
    } catch (error) {
      if (candidate.required) {
        throw new Error(`Failed to parse route sample overrides from ${candidate.source}: ${error.message}`);
      }
      logVerbose(`ignoring unparsable route sample overrides from ${candidate.source}: ${error.message}`);
      continue;
    }

    const rawSamples =
      parsed.route_samples ||
      parsed.routeSamples ||
      parsed.dynamic_segment_samples ||
      parsed.dynamicSegmentSamples ||
      parsed[`${SURFACE}_route_samples`];
    const normalized = normalizeRouteSampleOverrides(rawSamples);
    if (Object.keys(normalized).length > 0) {
      logVerbose(`loaded ${Object.keys(normalized).length} live route sample override group(s) from ${candidate.source}`);
      return normalized;
    }
  }

  return {};
}

function normalizeRouteSampleOverrides(rawSamples) {
  if (!rawSamples || typeof rawSamples !== 'object' || Array.isArray(rawSamples)) {
    return {};
  }

  const normalized = {};
  for (const [key, value] of Object.entries(rawSamples)) {
    const samples = Array.isArray(value) ? value : [value];
    const strings = samples
      .map((sample) => String(sample || '').trim())
      .filter(Boolean);
    if (strings.length > 0) {
      normalized[key] = [...new Set(strings)];
    }
  }
  return normalized;
}

class LiveCookieJar {
  constructor(baseUrl) {
    this.baseUrl = new URL(baseUrl);
    this.host = this.baseUrl.hostname.toLowerCase();
    this.isHttps = this.baseUrl.protocol === 'https:';
    this.cookies = new Map();
    this.history = [];
  }

  apply(setCookieHeaders, requestPath = '/') {
    for (const header of setCookieHeaders) {
      const cookie = parseSetCookie(header, requestPath);
      if (!cookie) continue;
      if (cookie.hostOnly) {
        cookie.domain = this.host;
      }

      const rejectionReason = this.getRejectionReason(cookie);
      if (rejectionReason) {
        this.history.push(this.historyEntry(cookie, 'rejected', rejectionReason));
        continue;
      }

      const key = `${cookie.name};${cookie.hostOnly ? 'host' : 'domain'}=${cookie.domain};${cookie.path}`;
      if (cookie.attributes.get('max-age') === '0') {
        this.cookies.delete(key);
        this.history.push(this.historyEntry(cookie, 'deleted'));
        continue;
      }

      this.cookies.set(key, cookie);
      this.history.push(this.historyEntry(cookie, 'stored'));
    }
  }

  header(requestPath = '/') {
    return this.cookiesForUrl(new URL(requestPath, this.baseUrl).toString())
      .sort((left, right) => right.path.length - left.path.length)
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join('; ');
  }

  has(name, requestPath = '/') {
    return this.cookiesForUrl(new URL(requestPath, this.baseUrl).toString())
      .some((cookie) => cookie.name === name);
  }

  activeNames() {
    return [...this.cookies.values()].map((cookie) => cookie.name).sort();
  }

  cookiesForUrl(rawUrl) {
    const url = new URL(rawUrl);
    const host = url.hostname.toLowerCase();
    const isHttps = url.protocol === 'https:';
    return [...this.cookies.values()].filter((cookie) => (
      pathMatches(url.pathname || '/', cookie.path)
      && domainMatchesCookie(cookie, host)
      && (!cookie.secure || isHttps)
    ));
  }

  cookiesForOrigin(rawUrl) {
    const url = new URL(rawUrl);
    const host = url.hostname.toLowerCase();
    const isHttps = url.protocol === 'https:';
    return [...this.cookies.values()].filter((cookie) => (
      domainMatchesCookie(cookie, host)
      && (!cookie.secure || isHttps)
    ));
  }

  getRejectionReason(cookie) {
    if (cookie.secure && !this.isHttps) {
      return 'secure-cookie-on-http-origin';
    }
    if (!domainMatchesCookie(cookie, this.host)) {
      return 'domain-mismatch';
    }
    return null;
  }

  historyEntry(cookie, action, rejectionReason = null) {
    const entry = {
      action,
      domain: cookie.hostOnly ? '<host-only>' : cookie.domain,
      httpOnly: cookie.httpOnly,
      name: cookie.name,
      path: cookie.path,
      secure: cookie.secure,
    };
    if (rejectionReason) {
      entry.rejectionReason = rejectionReason;
    }
    return entry;
  }
}

async function authenticateLiveSession() {
  assert(AUTH_IDENTIFIER, 'Set AUTH_BFF_SMOKE_IDENTIFIER or WEB_ROUTE_SMOKE_IDENTIFIER before running --live-api.');
  assert(AUTH_PASSWORD, 'Set AUTH_BFF_SMOKE_PASSWORD or WEB_ROUTE_SMOKE_PASSWORD before running --live-api.');
  assertLocalUrl(BASE_URL);
  assertLocalUrl(AUTH_CONNECT_BASE_URL);

  const jar = new LiveCookieJar(BASE_URL);
  const healthProbe = await liveFetch('/api/v1/auth/session', {
    headers: buildLiveAuthHeaders({ accept: 'application/json' }),
    method: 'GET',
  }).catch((error) => {
    throw new Error(`Live BFF route is not reachable at ${AUTH_CONNECT_BASE_URL}: ${error.message}`);
  });
  await healthProbe.arrayBuffer().catch(() => null);

  const loginResponse = await liveJsonRequest('/api/v1/auth/login', {
    body: {
      login_or_email: AUTH_IDENTIFIER,
      password: AUTH_PASSWORD,
    },
    jar,
    method: 'POST',
  });
  assert(
    loginResponse.status === 200,
    `Expected live login status 200, got ${loginResponse.status}: ${formatLivePayload(loginResponse.payload)}`,
  );
  assertNoTokenFields(loginResponse.payload, 'live login response');

  let twoFactorPendingResponse = null;
  let twoFactorCompleteResponse = null;
  if (loginResponse.payload?.requires_2fa === true) {
    assert(
      typeof loginResponse.payload.tfa_token === 'string' && loginResponse.payload.tfa_token.length > 0,
      'Expected live login 2FA challenge to include a pending token.',
    );
    assert(AUTH_TOTP_CODE, `Set AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_TOTP_CODE or WEB_ROUTE_SMOKE_TOTP_CODE for a 2FA-enabled account.`);

    twoFactorPendingResponse = await liveJsonRequest('/api/auth/2fa/pending', {
      body: {
        token: loginResponse.payload.tfa_token,
        locale: LOCALE,
        return_to: `/${LOCALE}/dashboard`,
        is_new_user: false,
      },
      jar,
      method: 'POST',
    });
    assert(
      twoFactorPendingResponse.status === 204,
      `Expected live 2FA pending status 204, got ${twoFactorPendingResponse.status}: ${formatLivePayload(twoFactorPendingResponse.payload)}`,
    );

    twoFactorCompleteResponse = await liveJsonRequest('/api/auth/2fa/complete', {
      body: { code: AUTH_TOTP_CODE },
      jar,
      method: 'POST',
    });
    assert(
      twoFactorCompleteResponse.status === 200,
      `Expected live 2FA complete status 200, got ${twoFactorCompleteResponse.status}: ${formatLivePayload(twoFactorCompleteResponse.payload)}`,
    );
    assertNoTokenFields(twoFactorCompleteResponse.payload, 'live 2FA complete response');
  }

  for (const cookieName of CONFIG.expectedAuthCookies ?? []) {
    assert(
      jar.has(cookieName, '/api/v1/auth/session'),
      `Expected live authenticated flow to set ${cookieName}; active cookies: ${jar.activeNames().join(', ') || '<none>'}.`,
    );
  }

  const sessionResponse = await liveJsonRequest('/api/v1/auth/session', {
    jar,
    method: 'GET',
  });
  assert(
    sessionResponse.status === 200,
    `Expected live session status 200 after login, got ${sessionResponse.status}: ${formatLivePayload(sessionResponse.payload)}`,
  );
  assertNoTokenFields(sessionResponse.payload, 'live session response');
  assertRealmPayload(sessionResponse.payload, 'live session response');

  return {
    jar,
    summary: {
      status: 'passed',
      login: summarizeLiveResponse(loginResponse),
      twoFactorPending: twoFactorPendingResponse ? summarizeLiveResponse(twoFactorPendingResponse) : null,
      twoFactorComplete: twoFactorCompleteResponse ? summarizeLiveResponse(twoFactorCompleteResponse) : null,
      session: summarizeLiveResponse(sessionResponse),
      observedSetCookies: jar.history,
      activeCookieNames: jar.activeNames(),
    },
  };
}

async function liveJsonRequest(path, { body, jar, method }) {
  const headers = buildLiveAuthHeaders({
    accept: 'application/json',
    origin: BASE_URL,
    referer: `${BASE_URL}/${LOCALE}/dashboard`,
  });

  if (body !== undefined) {
    headers['content-type'] = 'application/json';
  }

  const cookieHeader = jar.header(path);
  if (cookieHeader) {
    headers.cookie = cookieHeader;
  }

  const response = await liveFetch(path, {
    body: body === undefined ? undefined : JSON.stringify(body),
    headers,
    method,
    redirect: 'manual',
  });
  jar.apply(getSetCookieHeaders(response), path);

  const text = await response.text();
  return {
    payload: parseJsonOrText(text),
    status: response.status,
  };
}

async function liveFetch(path, init) {
  if (AUTH_HOST_HEADER) {
    return nodeHttpRequest(new URL(path, AUTH_CONNECT_BASE_URL).toString(), init);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), LIVE_AUTH_TIMEOUT_MS);
  try {
    return await fetch(new URL(path, AUTH_CONNECT_BASE_URL), {
      ...init,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

function nodeHttpRequest(url, init) {
  return new Promise((resolve, reject) => {
    const target = new URL(url);
    const transport = target.protocol === 'https:' ? https : http;
    const headers = { ...(init.headers ?? {}) };
    const body = init.body;
    if (body !== undefined && !Object.keys(headers).some((key) => key.toLowerCase() === 'content-length')) {
      headers['content-length'] = Buffer.byteLength(body);
    }

    const request = transport.request({
      headers,
      hostname: target.hostname,
      method: init.method ?? 'GET',
      path: `${target.pathname}${target.search}`,
      port: target.port || (target.protocol === 'https:' ? 443 : 80),
      protocol: target.protocol,
    }, (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(Buffer.from(chunk)));
      response.on('end', () => {
        const responseHeaders = new Headers();
        for (let index = 0; index < response.rawHeaders.length; index += 2) {
          responseHeaders.append(response.rawHeaders[index], response.rawHeaders[index + 1]);
        }
        const status = response.statusCode ?? 599;
        const nullBodyStatus = status === 101 || status === 103 || status === 204 || status === 205 || status === 304;
        resolve(new Response(nullBodyStatus ? null : Buffer.concat(chunks), {
          headers: responseHeaders,
          status,
          statusText: response.statusMessage,
        }));
      });
    });

    request.setTimeout(LIVE_AUTH_TIMEOUT_MS, () => {
      request.destroy(new Error(`Timed out after ${LIVE_AUTH_TIMEOUT_MS}ms`));
    });
    request.on('error', reject);
    if (body !== undefined) {
      request.write(body);
    }
    request.end();
  });
}

function buildLiveAuthHeaders(headers) {
  if (!AUTH_HOST_HEADER) {
    return headers;
  }
  return {
    ...headers,
    host: AUTH_HOST_HEADER,
  };
}

function assertRealmPayload(payload, label) {
  assert(payload && typeof payload === 'object', `Expected ${label} to be an object.`);
  assert(
    payload.auth_realm_key === CONFIG.expectedRealm,
    `Expected ${label} auth_realm_key=${CONFIG.expectedRealm}, got ${String(payload.auth_realm_key)}.`,
  );
  assert(
    payload.principal_type === CONFIG.expectedPrincipalType,
    `Expected ${label} principal_type=${CONFIG.expectedPrincipalType}, got ${String(payload.principal_type)}.`,
  );
  assert(
    payload.scope_family === CONFIG.expectedScopeFamily,
    `Expected ${label} scope_family=${CONFIG.expectedScopeFamily}, got ${String(payload.scope_family)}.`,
  );
}

function assertNoTokenFields(payload, label) {
  if (!payload || typeof payload !== 'object') {
    return;
  }
  for (const key of ['access_token', 'refresh_token', 'token_type', 'expires_in']) {
    assert(!(key in payload), `Expected ${label} to hide ${key} from JSON payload.`);
  }
}

function summarizeLiveResponse(response) {
  return {
    status: response.status,
    payload: summarizeLivePayload(response.payload),
  };
}

function summarizeLivePayload(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return payload;
  }
  const summary = {};
  for (const key of ['requires_2fa', 'auth_realm_key', 'audience', 'principal_type', 'scope_family']) {
    if (key in payload) {
      summary[key] = payload[key];
    }
  }
  if ('detail' in payload) {
    summary.detail = typeof payload.detail === 'string' ? payload.detail : '<redacted>';
  }
  return summary;
}

function formatLivePayload(payload) {
  return JSON.stringify(summarizeLivePayload(payload));
}

function getSetCookieHeaders(response) {
  if (typeof response.headers.getSetCookie === 'function') {
    return response.headers.getSetCookie().flatMap(splitSetCookieHeader);
  }
  const setCookie = response.headers.get('set-cookie');
  return setCookie ? splitSetCookieHeader(setCookie) : [];
}

function splitSetCookieHeader(headerValue) {
  const boundaryNames = [
    '__Host-cvpn_device_id',
    '__Host-cvpn_private_catalog_session',
    'access_token',
    'customer_access_token',
    'customer_refresh_token',
    'cv_partner_attribution',
    'cv_ref_attribution',
    'partner_access_token',
    'partner_refresh_token',
    'refresh_token',
  ];
  const cookies = [];
  let start = 0;
  for (let index = 0; index < headerValue.length; index += 1) {
    if (headerValue[index] !== ',') continue;
    const candidate = headerValue.slice(index + 1).trimStart();
    if (!boundaryNames.some((name) => candidate.startsWith(`${name}=`))) continue;
    cookies.push(headerValue.slice(start, index).trim());
    start = index + 1;
  }
  cookies.push(headerValue.slice(start).trim());
  return cookies.filter(Boolean);
}

function parseSetCookie(header, requestPath = '/') {
  const parts = header.split(';').map((part) => part.trim()).filter(Boolean);
  const [nameValue, ...attributeParts] = parts;
  const separator = nameValue?.indexOf('=');
  if (!nameValue || !separator || separator < 1) {
    return null;
  }

  const attributes = new Map();
  for (const part of attributeParts) {
    const index = part.indexOf('=');
    if (index === -1) {
      attributes.set(part.toLowerCase(), true);
    } else {
      attributes.set(part.slice(0, index).toLowerCase(), part.slice(index + 1));
    }
  }

  return {
    attributes,
    domain: normalizeCookieDomain(attributes.get('domain') ?? null),
    hostOnly: !attributes.has('domain'),
    httpOnly: attributes.has('httponly'),
    name: nameValue.slice(0, separator),
    path: attributes.get('path') ?? defaultCookiePath(requestPath),
    secure: attributes.has('secure'),
    value: nameValue.slice(separator + 1),
  };
}

function normalizeCookieDomain(domain) {
  if (!domain) return null;
  return domain.replace(/^\./, '').toLowerCase();
}

function defaultCookiePath(requestPath) {
  if (!requestPath || requestPath[0] !== '/') return '/';
  if (requestPath === '/') return '/';
  const lastSlash = requestPath.lastIndexOf('/');
  return lastSlash <= 0 ? '/' : requestPath.slice(0, lastSlash);
}

function pathMatches(requestPath, cookiePath) {
  if (requestPath === cookiePath) return true;
  if (!requestPath.startsWith(cookiePath)) return false;
  return cookiePath.endsWith('/') || requestPath[cookiePath.length] === '/';
}

function domainMatchesCookie(cookie, host) {
  if (cookie.hostOnly) {
    return cookie.domain === host;
  }
  return host === cookie.domain || host.endsWith(`.${cookie.domain}`);
}

function parseJsonOrText(text) {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function assertLocalUrl(value) {
  const url = new URL(value);
  const host = url.hostname.toLowerCase();
  const isLocal =
    host === 'localhost'
    || host === '127.0.0.1'
    || host === '::1'
    || host.endsWith('.localhost');
  assert(isLocal, `Refusing to run live route smoke against non-local URL ${value}.`);
}

function trimTrailingSlash(value) {
  return value.replace(/\/$/, '');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function logVerbose(message) {
  if (VERBOSE) {
    console.error(`[web-route-smoke:${SURFACE}] ${message}`);
  }
}

function encodeJsonBody(data) {
  return Buffer.from(JSON.stringify(data)).toString('base64');
}

function findChromium() {
  const candidates = [
    process.env.CHROME_BIN,
    process.env.GOOGLE_CHROME_BIN,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Chromium\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }

  const result = spawnSync(
    'sh',
    ['-lc', 'command -v chromium || command -v chromium-browser || command -v google-chrome || command -v google-chrome-stable'],
    { encoding: 'utf8' },
  );
  return result.stdout.trim();
}

async function walkFiles(root, predicate) {
  const entries = await readdir(root, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const absolutePath = join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...await walkFiles(absolutePath, predicate));
      continue;
    }
    if (!predicate || predicate(absolutePath)) {
      files.push(absolutePath);
    }
  }
  return files;
}

function getRouteGroup(rawSegments) {
  if (rawSegments.includes('(auth)')) return 'auth';
  if (rawSegments.includes('(dashboard)')) return 'dashboard';
  if (rawSegments.includes('(marketing)')) return 'marketing';
  if (rawSegments.includes('(storefront)')) return 'storefront';
  if (rawSegments.includes('miniapp')) return 'miniapp';
  return 'app';
}

function routeSamplesForSegments(cleanSegments) {
  const dynamicIndex = cleanSegments.findIndex((segment) => /^\[.+]$/.test(segment));
  if (dynamicIndex === -1) {
    return [cleanSegments];
  }

  const dynamicName = cleanSegments[dynamicIndex];
  if (dynamicName === '[section]') {
    const samples = SURFACE_SECTION_SAMPLES[SURFACE] || [];
    return samples.map((sample) => [
      ...cleanSegments.slice(0, dynamicIndex),
      sample,
      ...cleanSegments.slice(dynamicIndex + 1),
    ]);
  }

  const parent = cleanSegments[dynamicIndex - 1] ?? '';
  const samples = LIVE_ROUTE_SAMPLE_OVERRIDES[parent] || DYNAMIC_SEGMENT_SAMPLES[parent] || ['smoke-id'];
  return samples.map((sample) => [
    ...cleanSegments.slice(0, dynamicIndex),
    sample,
    ...cleanSegments.slice(dynamicIndex + 1),
  ]);
}

function adminSectionConcretePageFile(appRoot, rawSegments, section) {
  return join(
    appRoot,
    ...rawSegments.map((segment) => (segment === '[section]' ? section : segment)),
    'page.tsx',
  );
}

function missingConcreteAdminSectionSlugs(appRoot, rawSegments) {
  if (SURFACE !== 'admin') {
    return [];
  }
  return ADMIN_SECTION_SLUGS.filter((section) => !existsSync(adminSectionConcretePageFile(appRoot, rawSegments, section)));
}

function adminSectionCatchAllSkipReason(appRoot, rawSegments) {
  const missingSections = missingConcreteAdminSectionSlugs(appRoot, rawSegments);
  if (missingSections.length > 0) {
    return `admin section catch-all is covered for missing concrete section routes: ${missingSections.join(', ')}`;
  }
  return `admin section catch-all is shadowed by concrete route files for registered sections: ${ADMIN_SECTION_SLUGS.join(', ')}`;
}

function toRoutePath(cleanSegments) {
  return cleanSegments.length === 0 ? `/${LOCALE}` : `/${LOCALE}/${cleanSegments.join('/')}`;
}

async function discoverRoutes() {
  const appRoot = join(REPO_ROOT, CONFIG.workspace, 'src', 'app', '[locale]');
  const pageFiles = await walkFiles(appRoot, (filePath) => filePath.endsWith(`${sep}page.tsx`));
  const routes = [];
  const skipped = [];

  for (const pageFile of pageFiles.sort()) {
    const rawSegments = relative(appRoot, pageFile).split(sep);
    rawSegments.pop();
    const group = getRouteGroup(rawSegments);
    const cleanSegments = rawSegments.filter((segment) => !/^\(.+\)$/.test(segment));
    const baseRoute = { rawSegments, cleanSegments, group, pageFile };

    if (CONFIG.skipRoute?.(baseRoute)) {
      skipped.push({
        group,
        pageFile: relative(REPO_ROOT, pageFile),
        reason: 'explicitly excluded non-production or catch-all route',
      });
      continue;
    }

    let samples = routeSamplesForSegments(cleanSegments);
    if (SURFACE === 'admin' && cleanSegments.includes('[section]')) {
      samples = missingConcreteAdminSectionSlugs(appRoot, rawSegments).map((section) =>
        cleanSegments.map((segment) => (segment === '[section]' ? section : segment)),
      );
    }
    if (samples.length === 0) {
      const isRetiredPartnerSection =
        SURFACE === 'partner' && cleanSegments.includes('[section]');
      const isCoveredAdminSection =
        SURFACE === 'admin' && cleanSegments.includes('[section]');
      skipped.push({
        group,
        pageFile: relative(REPO_ROOT, pageFile),
        reason: isCoveredAdminSection
          ? adminSectionCatchAllSkipReason(appRoot, rawSegments)
          : isRetiredPartnerSection
            ? 'retired generic partner section route intentionally returns notFound; canonical concrete partner sections are discovered separately'
            : 'unsupported dynamic catch-all sample',
      });
      continue;
    }

    for (const sampleSegments of samples) {
      const path = toRoutePath(sampleSegments);
      const baseUrl = SURFACE === 'partner' && group === 'storefront' ? STOREFRONT_BASE_URL : BASE_URL;
      routes.push({
        id: `${group}:${path}:${relative(REPO_ROOT, pageFile).replace(/\\/g, '/')}`,
        group,
        path,
        url: new URL(path, baseUrl).toString(),
        pageFile: relative(REPO_ROOT, pageFile),
        tags: collectRouteTags(SURFACE, group, sampleSegments),
      });
    }
  }

  const filteredRoutes = routes.filter((route) => {
    if (ROUTE_FILTERS.length > 0 && !ROUTE_FILTERS.some((filter) => routeMatchesFilter(route, filter))) {
      return false;
    }
    if (GROUP_FILTER && route.group !== GROUP_FILTER) {
      return false;
    }
    return true;
  });

  return {
    routes: ROUTE_LIMIT > 0 ? filteredRoutes.slice(0, ROUTE_LIMIT) : filteredRoutes,
    skipped,
    discoveredRouteCount: routes.length,
  };
}

function routeMatchesFilter(route, filter) {
  return route.path === filter || route.path.endsWith(`/${filter.replace(/^\//, '')}`);
}

function collectRouteTags(surface, group, segments) {
  const joined = `/${segments.join('/')}`;
  const tags = [surface, group];
  if (/commerce|payment|wallet|withdraw|pricebook|subscription|finance|checkout|codes|conversions|analytics|reseller/.test(joined)) {
    tags.push('money');
  }
  if (/login|register|forgot-password|reset-password|verify|magic-link|oauth|telegram-link/.test(joined)) {
    tags.push('auth');
  }
  if (/security|passkeys|two-factor|sessions/.test(joined)) {
    tags.push('security');
  }
  if (joined.includes('_legacy-admin-routes')) {
    tags.push('legacy-retirement');
  }
  return tags;
}

function npmSpawn(commandArgs) {
  if (process.platform !== 'win32') {
    return {
      command: 'npm',
      args: commandArgs,
    };
  }

  return {
    command: 'cmd.exe',
    args: ['/d', '/s', '/c', `npm ${commandArgs.join(' ')}`],
  };
}

async function startDevServer() {
  if (!START_SERVER) {
    return null;
  }

  const env = {
    ...process.env,
    NEXT_TELEMETRY_DISABLED: '1',
    PORT: String(DEV_PORT),
    HOST: '127.0.0.1',
  };

  if (SURFACE === 'partner') {
    const portalHosts = [
      `localhost:${DEV_PORT}`,
      `127.0.0.1:${DEV_PORT}`,
      `portal.localhost:${DEV_PORT}`,
    ].join(',');
    env.NEXT_PUBLIC_PARTNER_PORTAL_HOSTS = [env.NEXT_PUBLIC_PARTNER_PORTAL_HOSTS, portalHosts]
      .filter(Boolean)
      .join(',');
    env.NEXT_PUBLIC_PARTNER_PORTAL_SIMULATION_ENABLED =
      env.NEXT_PUBLIC_PARTNER_PORTAL_SIMULATION_ENABLED || (LIVE_API ? 'false' : 'true');
    if (LIVE_API && !env.PARTNER_API_URL && env.API_INTERNAL_ORIGIN) {
      env.PARTNER_API_URL = env.API_INTERNAL_ORIGIN;
    }
  }

  const npm = npmSpawn(['run', 'dev', '-w', CONFIG.workspace]);
  const processRef = spawn(npm.command, npm.args, {
    cwd: REPO_ROOT,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  const logs = [];
  const pushLog = (chunk) => {
    const text = chunk.toString();
    logs.push(text);
    while (logs.join('').length > 20_000) {
      logs.shift();
    }
  };
  processRef.stdout.on('data', pushLog);
  processRef.stderr.on('data', pushLog);

  try {
    await waitForServerReady(new URL(`/${LOCALE}/login`, BASE_URL).toString(), logs);
  } catch (error) {
    stopProcessTree(processRef);
    throw error;
  }

  return {
    process: processRef,
    logs,
    async stop() {
      stopProcessTree(processRef);
      await new Promise((resolve) => {
        processRef.once('exit', resolve);
        setTimeout(resolve, 2_500);
      });
    },
  };
}

function stopProcessTree(processRef) {
  if (!processRef.pid || processRef.killed) {
    return;
  }

  if (process.platform === 'win32') {
    spawnSync('taskkill.exe', ['/PID', String(processRef.pid), '/T', '/F'], {
      stdio: 'ignore',
    });
    return;
  }

  processRef.kill('SIGTERM');
}

async function waitForServerReady(url, logs) {
  const deadline = Date.now() + SERVER_READY_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const response = await fetchWithConnectBase(url, { method: 'GET' }).catch(() => null);
    if (response && response.status < 500) {
      return;
    }
    await sleep(750);
  }
  throw new Error(`Timed out waiting for ${url}.\nRecent dev server logs:\n${logs.join('').slice(-8000)}`);
}

async function fetchWithConnectBase(displayUrl, init = {}) {
  const display = new URL(displayUrl);
  const connect = new URL(`${display.pathname}${display.search}`, CONNECT_BASE_URL);
  const headers = { ...(init.headers ?? {}) };
  if (connect.origin !== display.origin && !Object.keys(headers).some((key) => key.toLowerCase() === 'host')) {
    headers.host = display.host;
  }
  return nodeHttpRequest(connect.toString(), {
    ...init,
    headers,
  });
}

class CdpClient {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();

    socket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data.toString());

      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) {
          reject(new Error(message.error.message));
        } else {
          resolve(message.result);
        }
        return;
      }

      const listeners = this.listeners.get(message.method);
      if (listeners) {
        for (const listener of listeners) {
          listener(message);
        }
      }
    });

    const rejectPending = (error) => {
      const pending = [...this.pending.values()];
      this.pending.clear();
      for (const { reject } of pending) {
        reject(error);
      }
    };
    socket.addEventListener('close', () => {
      rejectPending(new Error('CDP socket closed before command completed'));
    });
    socket.addEventListener('error', (event) => {
      rejectPending(new Error(`CDP socket error before command completed: ${event.message || 'unknown error'}`));
    });
  }

  send(method, params = {}, sessionId, timeoutMs = CDP_COMMAND_TIMEOUT_MS) {
    const id = this.nextId;
    this.nextId += 1;
    const payload = { id, method, params };
    if (sessionId) {
      payload.sessionId = sessionId;
    }

    return new Promise((resolve, reject) => {
      let timer = null;
      const settle = (callback, value) => {
        if (timer) {
          clearTimeout(timer);
        }
        callback(value);
      };
      this.pending.set(id, {
        resolve: (value) => settle(resolve, value),
        reject: (error) => settle(reject, error),
      });
      if (timeoutMs > 0) {
        timer = setTimeout(() => {
          if (this.pending.delete(id)) {
            reject(new Error(`Timed out waiting for CDP command ${method}`));
          }
        }, timeoutMs);
      }
      this.socket.send(JSON.stringify(payload));
    });
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) || new Set();
    listeners.add(listener);
    this.listeners.set(method, listeners);
    return () => listeners.delete(listener);
  }
}

async function waitForWebSocketUrl(processRef) {
  let stderr = '';
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`Timed out waiting for Chromium DevTools endpoint. Stderr:\n${stderr}`));
    }, 15_000);

    processRef.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
      const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) {
        clearTimeout(timer);
        resolve(match[1]);
      }
    });

    processRef.once('exit', (code) => {
      clearTimeout(timer);
      reject(new Error(`Chromium exited before DevTools was ready with code ${code}. Stderr:\n${stderr}`));
    });
  });
}

async function waitForEvent(client, method, predicate, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      dispose();
      reject(new Error(`Timed out waiting for CDP event ${method}`));
    }, timeoutMs);

    const dispose = client.on(method, (message) => {
      if (predicate(message)) {
        clearTimeout(timer);
        dispose();
        resolve(message);
      }
    });
  });
}

async function evaluate(client, sessionId, expression, timeoutMs = ASSERTION_TIMEOUT_MS) {
  const result = await client.send(
    'Runtime.evaluate',
    {
      expression,
      awaitPromise: true,
      returnByValue: true,
    },
    sessionId,
    timeoutMs,
  );

  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || 'Runtime evaluation failed');
  }

  return result.result?.value;
}

async function waitForExpression(client, sessionId, expression, timeoutMs, message) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const remainingMs = Math.max(250, deadline - Date.now());
      if (await evaluate(client, sessionId, expression, Math.min(1_000, remainingMs))) {
        return;
      }
    } catch (error) {
      lastError = error;
    }
    await sleep(100);
  }
  const details = lastError instanceof Error ? ` Last evaluation error: ${lastError.message}` : '';
  throw new Error(`${message}.${details}`);
}

async function fulfillJson(client, sessionId, requestId, data, status = 200) {
  await client.send('Fetch.fulfillRequest', {
    requestId,
    responseCode: status,
    responseHeaders: [{ name: 'content-type', value: 'application/json' }],
    body: encodeJsonBody(data),
  }, sessionId);
}

async function fulfillNoContent(client, sessionId, requestId) {
  await client.send('Fetch.fulfillRequest', { requestId, responseCode: 204 }, sessionId);
}

function buildCustomerSessionFixture() {
  return {
    id: 'smoke-customer',
    email: 'customer-smoke@example.invalid',
    login: 'customer-smoke',
    is_active: true,
    is_email_verified: true,
    role: 'viewer',
    language: LOCALE,
    created_at: '2026-06-03T00:00:00.000Z',
  };
}

function buildAdminSessionFixture() {
  return {
    id: 'smoke-admin',
    email: 'admin-smoke@example.invalid',
    login: 'admin-smoke',
    is_active: true,
    is_email_verified: true,
    role: 'super_admin',
    permissions: ['*'],
    created_at: '2026-06-03T00:00:00.000Z',
  };
}

function buildPartnerSessionFixture() {
  return {
    id: 'smoke-partner',
    email: 'partner-smoke@example.invalid',
    login: 'partner-smoke',
    is_active: true,
    is_email_verified: true,
    role: 'partner_operator',
    auth_realm_key: 'partner',
    audience: 'cybervpn:partner',
    principal_type: 'partner_operator',
    created_at: '2026-06-03T00:00:00.000Z',
  };
}

function buildPartnerWorkspaceFixture() {
  return {
    id: PARTNER_SMOKE_WORKSPACE_UUID,
    workspace_id: PARTNER_SMOKE_WORKSPACE_UUID,
    slug: 'northstar-smoke',
    display_name: 'Northstar Smoke Workspace',
    status: 'active',
    role: 'workspace_owner',
    release_ring: 'R4',
    primary_lane: 'reseller_api',
    finance_readiness: 'ready',
    compliance_readiness: 'approved',
    technical_readiness: 'ready',
    governance_state: 'clear',
    current_role_key: 'owner',
    current_permission_keys: [...PARTNER_SMOKE_ROLE_PERMISSIONS],
    members: [
      {
        id: 'member-smoke-owner',
        role_key: 'owner',
        role_display_name: 'Owner',
        membership_status: 'active',
        operator_display_name: 'Smoke Partner',
        operator_login: 'partner-smoke',
        operator_email: 'partner-smoke@example.invalid',
        admin_user_id: 'smoke-partner',
        permission_keys: [...PARTNER_SMOKE_ROLE_PERMISSIONS],
      },
    ],
    created_at: '2026-06-03T00:00:00.000Z',
    updated_at: '2026-06-03T00:00:00.000Z',
  };
}

function clientCapabilitiesFixture() {
  return {
    auth: {
      email_password: true,
      magic_link: true,
      telegram: true,
    },
    payments: {
      web_checkout: true,
      telegram_stars: SURFACE === 'frontend',
      cryptobot: true,
      manual_invoice: true,
      autorenewal: false,
    },
    growth: {
      invites: true,
      referral: true,
      promo_codes: true,
      gift_codes: true,
      checkout_code_discounts: true,
      growth_hub: true,
    },
    subscriptions: {
      multi_subscription: true,
      selected_subscription_required: true,
      addons: true,
      upgrade: true,
      trial: true,
      paid_provisioning: true,
    },
    partner: {
      portal: true,
      applications: true,
      codes: true,
      attribution: true,
      storefronts: true,
      reporting: true,
      settlement_sandbox: true,
      webhooks: true,
      payouts: true,
      event_backbone: true,
    },
    site: {
      customer_site_mode: 'full_site',
      cabinet_only: false,
      version: 1,
      public_hosts: ['127.0.0.1', 'localhost'],
      cabinet_hosts: ['127.0.0.1', 'localhost'],
      cabinet_destination_path: '/dashboard',
      cabinet_marketing_route_action: 'redirect_public',
      public_marketing_destination_path: '/',
      allowed_path_prefixes: [],
      preserve_query_keys: [],
      registration_policy_independent: true,
    },
    onboarding: {
      post_registration_code_prompt: true,
      web_otp: true,
      telegram_miniapp: SURFACE === 'frontend',
      state_store: true,
      telegram_bot_code_apply: true,
      connection_bootstrap: true,
      flow_key: 'post_registration_growth_code_v1',
      version: 1,
      allowed_code_types: ['invite', 'promo', 'gift', 'referral'],
      allow_referral_input: true,
      allow_partner_input: true,
      available: true,
    },
  };
}

function publicCatalogFixture() {
  const context = publicCatalogContextFixture();
  const billingPeriod = {
    planId: 'plan-smoke-monthly',
    catalogItemKey: 'official-web:smoke-monthly:30d',
    durationDays: 30,
    displayPrice: {
      amount: '9.99',
      currency: 'USD',
      minorUnits: 2,
    },
    version: 'smoke-v1',
    quote: {
      planId: 'plan-smoke-monthly',
      planCode: 'smoke-monthly',
      billingPeriodDays: 30,
      currency: 'USD',
      catalogItemKey: 'official-web:smoke-monthly:30d',
      contextCacheKey: context.cacheKey,
    },
    includedAddonCodes: [],
    availability: ['web', 'partner_storefront'],
    metadata: {},
  };
  const publicPlan = {
    id: 'plan-smoke-monthly',
    uuid: 'plan-smoke-monthly',
    name: 'Smoke Monthly',
    display_name: 'Smoke Monthly',
    description: 'Synthetic route smoke plan',
    duration_days: 30,
    price: 9.99,
    currency: 'USD',
    is_active: true,
    features: ['Private access', 'Smoke fixture'],
    planCode: 'smoke-monthly',
    displayName: 'Smoke Monthly',
    version: 'smoke-v1',
    billingPeriods: [billingPeriod],
    devicesIncluded: 5,
    trafficLimitBytes: null,
    trafficPolicy: { mode: 'fair_use' },
    connectionModes: ['vless-reality', 'wireguard'],
    serverPool: ['global'],
    supportSla: 'standard',
    dedicatedIp: { included: false },
    inviteBundle: {},
    trialEligible: true,
    promoEligible: true,
    metadata: {},
  };
  const publicAddon = publicCatalogAddonFixture();

  return {
    catalogVersion: 'public-commercial-smoke-v1',
    cacheKey: context.cacheKey,
    context,
    plans: [publicPlan],
    addons: [publicAddon],
    trialEligible: true,
    promoEligible: true,
    metadata: {
      policyIds: ['smoke-policy'],
      source: 'route_smoke',
      channel: 'official_web',
      storefrontKey: SURFACE === 'partner' ? 'northstar-smoke' : null,
      addonsEnabled: true,
      promoCodesEnabled: true,
      checkoutCodeDiscountsEnabled: true,
      invalidationEvents: [],
    },
    offers: [
      {
        id: 'offer-smoke-monthly',
        offer_key: 'smoke-monthly',
        display_name: 'Smoke Monthly',
        offer_display_name: 'Smoke Monthly',
        subscription_plan_id: 'plan-smoke-monthly',
        status: 'active',
        sale_channels: ['web', 'partner_storefront'],
      },
    ],
    pricebooks: [
      {
        id: 'pricebook-smoke',
        pricebook_key: 'smoke-usd',
        currency_code: 'USD',
        region_code: 'US',
        status: 'active',
        entries: [
          {
            offer_id: 'offer-smoke-monthly',
            visible_price: 9.99,
            compare_at_price: 14.99,
            included_addon_codes: [],
          },
        ],
      },
    ],
  };
}

function publicCatalogContextFixture() {
  return {
    uiLocale: LOCALE,
    displayCountry: 'US',
    pricingCountry: 'US',
    paymentCountry: 'US',
    currency: 'USD',
    confidence: 'explicit',
    selectableCountries: ['US', 'DE', 'NL'],
    selectableCurrencies: ['USD', 'EUR'],
    paymentMethods: {
      availableMethods: ['cryptobot', 'manual_invoice'],
      webCheckout: true,
      cryptobot: true,
      telegramStars: SURFACE === 'frontend',
      manualInvoice: true,
      autorenewal: false,
    },
    cacheKey: 'route-smoke-context-us-usd',
    resolutionTrace: ['route-smoke'],
  };
}

function publicCatalogAddonFixture() {
  return {
    addonId: 'addon-smoke-priority',
    code: 'PRIORITY_SUPPORT',
    displayName: 'Priority Support',
    durationMode: 'subscription_period',
    isStackable: true,
    quantityStep: 1,
    displayPrice: {
      amount: '2.50',
      currency: 'USD',
      minorUnits: 2,
    },
    maxQuantityByPlan: { 'smoke-monthly': 1 },
    deltaEntitlements: { support_priority: true },
    requiresLocation: false,
    saleChannels: ['web', 'partner_storefront'],
    metadata: {},
  };
}

function adminPlanFixture() {
  return {
    id: 'plan-smoke-monthly',
    uuid: 'plan-smoke-monthly',
    name: 'Smoke Monthly',
    plan_code: 'smoke-monthly',
    display_name: 'Smoke Monthly',
    description: 'Synthetic route smoke plan',
    duration_days: 30,
    price: 9.99,
    price_usd: 9.99,
    currency: 'USD',
    catalog_visibility: 'public',
    devices_included: 5,
    traffic_limit_bytes: null,
    traffic_policy: { mode: 'fair_use' },
    connection_modes: ['vless-reality', 'wireguard'],
    server_pool: ['global'],
    support_sla: 'standard',
    dedicated_ip: { included: false },
    invite_bundle: {
      count: 0,
      friend_days: 0,
      expiry_days: 0,
    },
    trial_eligible: true,
    promo_eligible: true,
    sort_order: 10,
    is_active: true,
    sale_channels: ['web', 'miniapp', 'telegram_bot', 'admin'],
    features: ['Private access', 'Smoke fixture'],
    created_at: '2026-06-03T00:00:00.000Z',
    updated_at: '2026-06-03T00:00:00.000Z',
  };
}

function adminAddonFixture() {
  return {
    uuid: 'addon-smoke-priority',
    code: 'PRIORITY_SUPPORT',
    display_name: 'Priority Support',
    description: 'Synthetic route smoke addon',
    price_usd: 2.5,
    price_rub: null,
    quantity_step: 1,
    sale_channels: ['web', 'miniapp', 'telegram_bot', 'admin'],
    delta_entitlements: { device_limit: 1, support_priority: true },
    max_quantity_by_plan: {
      'smoke-monthly': 1,
    },
    requires_location: false,
    is_stackable: true,
    is_active: true,
    created_at: '2026-06-03T00:00:00.000Z',
    updated_at: '2026-06-03T00:00:00.000Z',
  };
}

function commercialContextOptionsFixture() {
  return {
    source: 'system_config',
    countries: [
      {
        country_code: 'US',
        default_currency_code: 'USD',
        supported_currency_codes: ['USD'],
        payment_country_code: 'US',
        is_enabled: true,
      },
      {
        country_code: 'DE',
        default_currency_code: 'EUR',
        supported_currency_codes: ['EUR'],
        payment_country_code: 'DE',
        is_enabled: true,
      },
    ],
    currencies: [
      {
        currency_code: 'USD',
        minor_units: 2,
        is_enabled: true,
      },
      {
        currency_code: 'EUR',
        minor_units: 2,
        is_enabled: true,
      },
    ],
  };
}

function storefrontPreviewFixture() {
  return {
    storefront_key: 'northstar-smoke',
    status: 'preview',
    route_contract: {
      host: new URL(STOREFRONT_BASE_URL).host,
      customer_entry_path: `/${LOCALE}/checkout`,
      route_status: 'preview',
      checkout_side_effects: false,
    },
    attribution_contract: {
      owner_type: 'partner_workspace',
      owner_source: 'storefront',
      partner_code: 'NORTHSTAR',
    },
    analytics_contract: {
      expected_dimensions: ['storefront_key', 'partner_code', 'currency'],
    },
    pricing_boundary: {
      offers: [
        {
          offer_id: 'offer-smoke-monthly',
          offer_display_name: 'Smoke Monthly',
          pricebook_key: 'smoke-usd',
          region_code: 'US',
          currency_code: 'USD',
          visible_price: 9.99,
        },
      ],
    },
    preview_api_path: '/api/v1/storefronts/northstar-smoke/preview',
  };
}

function partnerBootstrapFixture() {
  const workspace = API_ROUTE_FIXTURES.workspace;
  return {
    active_workspace_id: workspace.id,
    active_workspace: workspace,
    workspaces: [workspace],
    programs: [],
    counters: {
      unread_notifications: 1,
      open_cases: 0,
      pending_tasks: 0,
    },
    pending_tasks: [],
    blocked_reasons: [],
  };
}

function partnerRemnawaveResourceFixture(resourceType) {
  const isProfile = resourceType === 'profile';
  assert(isProfile || resourceType === 'integration', `Unsupported Partner Remnawave smoke resource: ${resourceType}`);
  return {
    workspace_id: PARTNER_SMOKE_WORKSPACE_UUID,
    resource_type: resourceType,
    resource_uuid: isProfile ? PARTNER_SMOKE_PROFILE_UUID : PARTNER_SMOKE_INTEGRATION_UUID,
    effective_permissions: ['remnawave_read', 'remnawave_write'],
    available_operations: ['inspect_assignment', 'mutate_resource'],
    unavailable_operations: ['execute_resource'],
    forbidden_operations: ['browser_ssh'],
    provider_details_available: false,
    safe_mutations: [isProfile ? 'profile_tags' : 'integration_metadata'],
  };
}

function partnerRemnawaveResourceListFixture() {
  return {
    workspace_id: PARTNER_SMOKE_WORKSPACE_UUID,
    items: [
      partnerRemnawaveResourceFixture('profile'),
      partnerRemnawaveResourceFixture('integration'),
    ],
    total: 2,
    next_offset: null,
    capabilities: {
      inspect_assignment: true,
      mutate_resource: true,
      execute_resource: false,
      browser_ssh: false,
      mutation_unavailable_reason: 'limited_to_explicit_profile_and_integration_grants',
      safe_mutations: ['profile_tags', 'integration_metadata'],
    },
  };
}

function partnerRemnawaveStatusFixture() {
  return {
    workspace_id: PARTNER_SMOKE_WORKSPACE_UUID,
    capabilities: {
      connections: true,
      usage: true,
      devices: true,
    },
    assigned_resources: 2,
    degraded: false,
    degraded_reason: null,
  };
}

function parseFixtureRequestBody(postData) {
  if (typeof postData !== 'string' || postData.length === 0) {
    return null;
  }
  try {
    return JSON.parse(postData);
  } catch {
    throw new Error('Route smoke received a non-JSON mutation body');
  }
}

function paymentHistoryFixture() {
  return {
    payments: [],
    total: 0,
    limit: 50,
    offset: 0,
  };
}

function publicDpiScoreFixture() {
  return {
    schemaVersion: 'public-network-dpi-score.v1',
    generatedAt: '2026-06-03T00:00:00.000Z',
    expiresAt: '2026-06-03T00:05:00.000Z',
    freshnessStatus: 'fresh',
    methodologyVersion: 'dpi-score.methodology.v3.reachability-baseline',
    measurementWindow: {
      hours: 24,
      minimumProbeCount: 12,
    },
    enabled: true,
    confidence: 'medium',
    lastUpdatedAt: '2026-06-03T00:00:00.000Z',
    reasonCode: null,
    countriesTracked: 2,
    countries: [
      {
        countryCode: 'de',
        publicName: 'DE',
        score: 92,
        confidence: 'high',
        lastUpdatedAt: '2026-06-03T00:00:00.000Z',
        protocols: [
          {
            protocol: 'vless-tls-ws-tls',
            successRate: 100,
            httpsBaselineSuccessRate: 100,
            medianHandshakeMs: 120,
            medianHttpsBaselineMs: 180,
            lastProbeAt: '2026-06-03T00:00:00.000Z',
          },
        ],
      },
      {
        countryCode: 'nl',
        publicName: 'NL',
        score: 88,
        confidence: 'medium',
        lastUpdatedAt: '2026-06-03T00:00:00.000Z',
        protocols: [
          {
            protocol: 'wireguard',
            successRate: 95,
            httpsBaselineSuccessRate: 90,
            medianHandshakeMs: 160,
            medianHttpsBaselineMs: 220,
            lastProbeAt: '2026-06-03T00:00:00.000Z',
          },
        ],
      },
    ],
  };
}

function walletFixture() {
  return {
    balance: 0,
    frozen: 0,
    frozen_balance: 0,
    available_balance: 0,
    currency: 'USD',
    transactions: [],
  };
}

function notificationPreferencesFixture() {
  return {
    email_security: true,
    email_marketing: false,
    push_connection: true,
    push_payment: true,
    push_subscription: true,
  };
}

function adminSettingFixture() {
  return {
    id: 1,
    key: 'miniapp.runtime',
    value: { enabled: true, mode: 'canary' },
    description: 'Synthetic route smoke setting',
    isPublic: false,
  };
}

function privacyRequestFixture() {
  return {
    allowed_actions: ['start_review', 'approve'],
    assigned_admin_id: null,
    canceled_at: null,
    fulfilled_at: null,
    manual_fulfillment_target_days: 30,
    overdue: false,
    privacy_request_reference: 'PRIV-2026-001',
    request_type: 'account_deletion',
    safe_customer_reference: 'customer-smoke',
    scheduled_for: null,
    status: 'submitted',
    submitted_at: '2026-06-03T00:00:00.000Z',
    ticket_reference: 'SUP-2026-001',
    updated_at: '2026-06-03T00:00:00.000Z',
    customer_account_public_uid: 14677650,
    decision_at: null,
    decision_reason: null,
    events: [],
    identity_verified_at: null,
    last_error_code: null,
    last_error_redacted: null,
    notes_redacted: null,
    policy_snapshot: {},
    principal_subject: 'customer-smoke',
    reason_code: null,
    review_started_at: null,
    support_ticket_reference: 'SUP-2026-001',
    version: 1,
  };
}

function supportTicketFixture() {
  return {
    assigned_admin_id: null,
    category: 'account',
    closed_at: null,
    created_at: '2026-06-03T00:00:00.000Z',
    customer_account_id: 'smoke-customer',
    id: 'support-ticket-smoke',
    last_customer_message_at: '2026-06-03T00:00:00.000Z',
    last_message_preview: 'Route smoke support ticket',
    last_support_message_at: null,
    owner_type: 'customer',
    partner_workspace_id: null,
    priority: 'normal',
    public_id: 'SUP-2026-001',
    resolved_at: null,
    source: 'customer_web',
    status: 'open',
    subject: 'Route smoke support ticket',
    updated_at: '2026-06-03T00:00:00.000Z',
    events: [],
    messages: [
      {
        author_id: 'smoke-customer',
        author_type: 'customer',
        body: 'Route smoke public support message.',
        created_at: '2026-06-03T00:00:00.000Z',
        id: 'support-message-smoke',
        ticket_id: 'support-ticket-smoke',
        visibility: 'public',
      },
    ],
  };
}

function messagingConversationFixture() {
  return {
    assigned_admin_id: null,
    category: 'support',
    closed_at: null,
    created_at: '2026-06-03T00:00:00.000Z',
    created_by_admin_id: null,
    customer_account_id: 'smoke-customer',
    id: 'messaging-conversation-smoke',
    last_message_at: '2026-06-03T00:00:00.000Z',
    priority: 'normal',
    public_id: 'smoke-conversation-001',
    related_support_ticket_id: 'support-ticket-smoke',
    response_state: 'waiting_admin',
    status: 'open',
    subject: 'Route smoke conversation',
    updated_at: '2026-06-03T00:00:00.000Z',
    messages: [
      {
        body: 'Route smoke public conversation message.',
        body_format: 'plain_text',
        client_message_id: null,
        conversation_id: 'messaging-conversation-smoke',
        created_at: '2026-06-03T00:00:00.000Z',
        id: 'messaging-message-smoke',
        public_id: 'MSG-2026-001',
        sender_id: 'smoke-customer',
        sender_type: 'customer',
        updated_at: '2026-06-03T00:00:00.000Z',
        visibility: 'public',
      },
    ],
    read_states: [],
  };
}

function adminMobileUserFixture() {
  return {
    id: 'smoke-user-001',
    email: 'customer-smoke@example.invalid',
    username: 'customer-smoke',
    status: 'active',
    is_active: true,
    is_partner: false,
    telegram_id: 123456,
    telegram_username: 'customer_smoke',
    remnawave_uuid: 'remna-smoke',
    referral_code: 'SMOKE',
    referred_by_user_id: null,
    partner_user_id: null,
    partner_promoted_at: null,
    created_at: '2026-06-03T00:00:00.000Z',
    last_login_at: '2026-06-03T00:00:00.000Z',
    device_count: 1,
    subscription_url: 'https://subscription.example.invalid/smoke',
    updated_at: '2026-06-03T00:00:00.000Z',
    devices: [
      {
        id: 'device-row-smoke',
        device_id: 'device-smoke',
        platform: 'ios',
        platform_id: 'apple',
        os_version: '18.1',
        app_version: '1.4.0',
        device_model: 'iPhone Smoke',
        push_token: null,
        registered_at: '2026-06-03T00:00:00.000Z',
        last_active_at: '2026-06-03T00:00:00.000Z',
      },
    ],
  };
}

function adminCustomerSubscriptionsFixture() {
  return {
    customer_account_id: 'smoke-customer',
    auth_realm_id: 'customer',
    selected_subscription_key: 'smoke-subscription',
    default_subscription_key: 'smoke-subscription',
    items: [
      {
        subscription_key: 'smoke-subscription',
        kind: 'trial',
        status: 'active',
        display_name: 'Smoke Monthly',
        plan_uuid: 'plan-smoke-monthly',
        plan_code: 'smoke-monthly',
        source_type: 'route_smoke',
        source_order_id: null,
        entitlement_grant_id: null,
        service_identity_id: 'service-smoke',
        provider_name: 'route-smoke',
        expires_at: '2026-12-31T00:00:00.000Z',
        created_at: '2026-06-03T00:00:00.000Z',
        effective_entitlements: {
          devices_included: 5,
          traffic_limit_bytes: null,
        },
        invite_bundle: {},
        is_trial: true,
        addons: [],
        can_manage: true,
        can_deliver_config: true,
        management_scope: 'subscription_vpn_identity',
      },
    ],
    limitations: [],
  };
}

function customerSubscriptionConfigFixture() {
  const subscriptionUrl = 'https://subscription.example.invalid/smoke';
  return {
    config: '',
    isFound: true,
    is_found: true,
    links: [],
    ssConfLinks: {},
    ss_conf_links: {},
    subscriptionUrl,
    subscription_url: subscriptionUrl,
    xhttpEnabled: false,
    xhttp_enabled: false,
  };
}

function currentEntitlementFixture() {
  return {
    status: 'active',
    display_name: 'Smoke Monthly',
    plan_code: 'smoke-monthly',
    plan_uuid: 'plan-smoke-monthly',
    period_days: 30,
    expires_at: '2026-12-31T00:00:00.000Z',
    is_trial: false,
    invite_bundle: {},
    addons: [],
    effective_entitlements: {
      connection_modes: ['standard', 'stealth'],
      device_limit: 5,
      display_traffic_label: 'Unlimited',
      support_sla: 'standard',
      traffic_limit_bytes: null,
    },
  };
}

function customerSubscriptionsFixture() {
  return {
    customer_account_id: 'smoke-customer',
    auth_realm_id: 'customer',
    selected_subscription_key: 'smoke-subscription',
    default_subscription_key: 'smoke-subscription',
    items: [
      {
        subscription_key: 'smoke-subscription',
        kind: 'paid',
        status: 'active',
        display_name: 'Smoke Monthly',
        plan_uuid: 'plan-smoke-monthly',
        plan_code: 'smoke-monthly',
        source_type: 'route_smoke',
        source_order_id: null,
        entitlement_grant_id: 'grant-smoke',
        service_identity_id: 'service-smoke',
        provider_name: 'route-smoke',
        expires_at: '2026-12-31T00:00:00.000Z',
        created_at: '2026-06-03T00:00:00.000Z',
        effective_entitlements: currentEntitlementFixture().effective_entitlements,
        invite_bundle: {},
        is_trial: false,
        addons: [],
        can_manage: true,
        can_deliver_config: true,
        management_scope: 'subscription_vpn_identity',
      },
    ],
    limitations: [],
  };
}

function growthNotificationCountersFixture() {
  return {
    total_notifications: 0,
    unread_notifications: 0,
    action_required_notifications: 0,
  };
}

function growthNotificationPreferencesFixture() {
  return {
    growth_in_app_invites: true,
    growth_email_invites: false,
    growth_telegram_invites: false,
    growth_in_app_referral_rewards: true,
    growth_email_referral_rewards: false,
    growth_telegram_referral_rewards: false,
    growth_in_app_gifts: true,
    growth_email_gifts: false,
    growth_telegram_gifts: false,
    growth_in_app_admin_updates: true,
    growth_email_admin_updates: false,
    growth_telegram_admin_updates: false,
  };
}

function referralStatusFixture() {
  return {
    enabled: true,
    commission_rate: 10,
  };
}

function referralCodeFixture() {
  return {
    referral_code: 'SMOKE',
  };
}

function referralStatsFixture() {
  return {
    total_referrals: 0,
    total_earned: 0,
    available_rewards_usd: 0,
    pending_rewards_usd: 0,
    commission_rate: 10,
  };
}

function referralRewardFixture() {
  return {
    id: 'reward-smoke',
    referred_user_id: null,
    reward_amount: 0,
    currency: 'USD',
    reward_status: 'available',
    created_at: '2026-06-03T00:00:00.000Z',
    available_at: '2026-06-03T00:00:00.000Z',
    hold_until: null,
  };
}

function adminReferralUserDetailFixture() {
  return {
    user: {
      id: 'smoke-user-001',
      email: 'customer-smoke@example.invalid',
      username: 'customer-smoke',
      telegram_username: 'customer_smoke',
      referral_code: 'SMOKE',
      is_partner: false,
    },
    referred_by_user_id: null,
    commission_count: 0,
    referred_users: 0,
    total_earned: 0,
    recent_commissions: [],
  };
}

function miniAppRuntimeFixture() {
  return {
    enabled: true,
    mode: 'canary',
    trial_enabled: true,
    checkout_enabled: true,
    config_enabled: true,
    maintenance_message: null,
    canary_telegram_user_ids: [123456789],
  };
}

function miniAppReadinessFixture() {
  return {
    observability_acknowledged: true,
    incident_runbook_acknowledged: true,
    checkout_canary_passed: true,
    config_delivery_canary_passed: true,
    rollback_drill_acknowledged: true,
    support_window_confirmed: true,
    customer_comms_ready: true,
    status_page_template_ready: true,
    incident_channel: '#miniapp-war-room',
    rollback_commander: '@ops-lead',
    primary_oncall_contact: '@backend-oncall',
    release_window_note: 'Route smoke launch window',
    is_ready: true,
  };
}

function miniAppRuntimeConfigFixture() {
  return {
    key: 'miniapp.runtime',
    rollout: miniAppRuntimeFixture(),
    description: 'Operator-controlled mini app runtime policy.',
    updated_at: '2026-06-03T00:00:00.000Z',
    updated_by: 'admin-smoke',
  };
}

function miniAppLaunchReadinessConfigFixture() {
  return {
    key: 'miniapp.launch_readiness',
    readiness: miniAppReadinessFixture(),
    description: 'Mini app launch readiness gates.',
    updated_at: '2026-06-03T00:00:00.000Z',
    updated_by: 'admin-smoke',
  };
}

function miniAppLaunchSummaryFixture() {
  return {
    launch_state: 'ready_for_live',
    live_switch_allowed: true,
    next_action: 'keep_canary',
    primary_action: 'promote_to_live',
    available_actions: ['promote_to_live', 'enter_maintenance', 'start_rollback', 'return_to_canary'],
    blockers: [],
    runtime: miniAppRuntimeFixture(),
    readiness: miniAppReadinessFixture(),
  };
}

function miniAppLaunchTimelineFixture() {
  return [
    {
      id: 'miniapp-timeline-smoke',
      created_at: '2026-06-03T00:00:00.000Z',
      admin_id: 'admin-smoke',
      action: 'system_config.miniapp_launch_action.executed',
      event_type: 'launch_action',
      action_name: 'promote_to_live',
      resulting_runtime_mode: 'canary',
      resulting_launch_state: 'ready_for_live',
      readiness_ready: true,
      change_reason: 'Route smoke fixture',
      entity_id: 'miniapp.runtime',
    },
  ];
}

function adminPartnerWorkspaceFixture() {
  return {
    ...buildPartnerWorkspaceFixture(),
    account_key: 'northstar-smoke',
    legacy_owner_user_id: null,
    created_by_admin_user_id: 'admin-smoke',
    code_count: 1,
    active_code_count: 1,
    total_clients: 12,
    total_earned: 120,
    last_activity_at: '2026-06-03T00:00:00.000Z',
  };
}

function adminPartnerApplicationSummaryFixture() {
  return {
    workspace: {
      id: 'workspace-smoke',
      account_key: 'northstar-smoke',
      display_name: 'Northstar Smoke Workspace',
      status: 'submitted',
      current_role_key: null,
      current_permission_keys: [],
    },
    applicant: {
      id: 'smoke-partner',
      login: 'partner-smoke',
      email: 'partner-smoke@example.invalid',
      is_email_verified: true,
    },
    primary_lane: 'reseller_api',
    review_ready: true,
    submitted_at: '2026-06-03T00:00:00.000Z',
    updated_at: '2026-06-03T00:00:00.000Z',
    open_review_request_count: 0,
    lane_statuses: ['submitted'],
  };
}

function adminPartnerApplicationDetailFixture() {
  return {
    ...adminPartnerApplicationSummaryFixture(),
    draft: {
      id: 'partner-draft-smoke',
      partner_account_id: 'workspace-smoke',
      applicant_admin_user_id: 'smoke-partner',
      workspace: adminPartnerApplicationSummaryFixture().workspace,
      draft_payload: {
        workspace_name: 'Northstar Smoke Workspace',
        contact_name: 'Smoke Partner',
        contact_email: 'partner-smoke@example.invalid',
        country: 'US',
        website: 'https://example.invalid',
        primary_lane: 'reseller_api',
        business_description: 'Route smoke partner workspace.',
        acquisition_channels: 'SEO',
        operating_regions: 'Global',
        languages: 'en',
        support_contact: 'support@example.invalid',
        technical_contact: 'tech@example.invalid',
        finance_contact: 'finance@example.invalid',
        compliance_accepted: true,
      },
      review_ready: true,
      submitted_at: '2026-06-03T00:00:00.000Z',
      withdrawn_at: null,
      created_at: '2026-06-03T00:00:00.000Z',
      updated_at: '2026-06-03T00:00:00.000Z',
    },
    lane_applications: [],
    review_requests: [],
    attachments: [],
  };
}

function partnerWorkspaceProgramsFixture() {
  return {
    lane_memberships: [],
    commercial_capabilities: {
      partner_cash_payout_allowed: true,
      payout_account_required: false,
      reseller_storefront_allowed: true,
      pricebook_preview_allowed: true,
    },
  };
}

function partnerWorkspaceRolesFixture() {
  return [
    {
      id: 'role-owner',
      role_key: 'owner',
      display_name: 'Owner',
      description: 'Workspace owner',
      permission_keys: [...PARTNER_SMOKE_ROLE_PERMISSIONS],
      is_system: true,
      created_at: '2026-06-03T00:00:00.000Z',
      updated_at: '2026-06-03T00:00:00.000Z',
    },
    {
      id: 'role-finance',
      role_key: 'finance',
      display_name: 'Finance',
      description: 'Finance operator',
      permission_keys: ['workspace_read'],
      is_system: true,
      created_at: '2026-06-03T00:00:00.000Z',
      updated_at: '2026-06-03T00:00:00.000Z',
    },
  ];
}

function partnerWorkspaceSettingsFixture() {
  return {
    is_email_verified: true,
    operator_email: 'partner-smoke@example.invalid',
    operator_role: 'owner',
    payout_status_emails: true,
    prefer_passkeys: true,
    preferred_currency: 'USD',
    preferred_language: LOCALE,
    product_announcements: false,
    require_mfa_for_workspace: true,
    reviewed_active_sessions: true,
    updated_at: '2026-06-03T00:00:00.000Z',
    workspace_security_alerts: true,
  };
}

function partnerWorkspaceOrganizationProfileFixture() {
  return {
    workspace_name: 'Northstar Smoke Workspace',
    primary_lane: 'reseller_api',
    country: 'US',
    website: 'https://example.invalid',
    contact_name: 'Smoke Partner',
    contact_email: 'partner-smoke@example.invalid',
    business_description: 'Route smoke partner workspace.',
    acquisition_channels: 'SEO, referrals',
    operating_regions: 'US, EU',
    languages: 'en, ru',
    support_contact: 'support@example.invalid',
    technical_contact: 'tech@example.invalid',
    finance_contact: 'finance@example.invalid',
    updated_at: '2026-06-03T00:00:00.000Z',
  };
}

function partnerWorkspacePasskeyPolicyFixture() {
  return {
    operatorCompliance: {
      activeMembers: 1,
      operatorsMissingActivePasskeys: 0,
      operatorsWithActivePasskeys: 1,
      workspaceId: 'workspace-smoke',
    },
    policy: {
      adminCountsAsMfa: false,
      allowedOrigins: [BASE_URL, STOREFRONT_BASE_URL],
      authenticationEnabled: true,
      browserTimeoutMs: 60_000,
      challengeTtlSeconds: 120,
      conditionalUiEnabled: true,
      enabled: true,
      freshAuthTtlSeconds: 300,
      realm_key: 'partner',
      reauthenticationEnabled: true,
      registrationEnabled: true,
      rp_id: 'localhost',
      rp_name: 'CyberVPN Partner',
      surface: 'partner',
      userVerification: 'required',
      workspacePolicyEnabled: true,
    },
    workspaceId: 'workspace-smoke',
    workspaceKey: 'northstar-smoke',
    workspaceMfaRequired: true,
    workspacePasskeysPreferred: true,
    workspacePolicyUpdatedAt: '2026-06-03T00:00:00.000Z',
    workspaceStatus: 'active',
  };
}

function adminGrowthReportingOverviewFixture() {
  const totals = {
    issued_total: 0,
    resolution_attempts_total: 0,
    resolution_accepted_total: 0,
    resolution_rejected_total: 0,
    redemption_total: 0,
    reservations_reserved_total: 0,
    reservations_consumed_total: 0,
    reservations_released_total: 0,
    reservations_expired_total: 0,
    rewards_created_total: 0,
    rewards_available_total: 0,
    rewards_reversed_total: 0,
    reward_created_amount_usd: 0,
    reward_available_amount_usd: 0,
    reward_reversed_amount_usd: 0,
  };
  return {
    generated_at: '2026-06-03T00:00:00.000Z',
    window_start: '2026-06-01',
    window_end: '2026-06-03',
    family_summaries: [],
    daily_points: [],
    totals,
    health: {
      freshness_status: 'fresh',
      stale_reason: null,
      refresh_age_seconds: 60,
      expected_refresh_interval_seconds: 3600,
      stale_after_seconds: 10800,
      auto_refresh_enabled: true,
      latest_attempt_at: '2026-06-03T00:00:00.000Z',
      latest_success_at: '2026-06-03T00:00:00.000Z',
      latest_failure_at: null,
      latest_failure_message: null,
      latest_run: null,
    },
    executive_summary: {
      total_issued: 0,
      total_redemptions: 0,
      total_reward_available_usd: 0,
      total_reward_reversed_usd: 0,
      resolution_acceptance_rate_pct: 0,
      dominant_family: null,
      highlights: [],
    },
    coverage_notes: [],
  };
}

function adminGrowthReportingGovernanceFixture() {
  return {
    generated_at: '2026-06-03T00:00:00.000Z',
    active_subscription_count: 0,
    paused_subscription_count: 0,
    coverage_gap_count: 0,
    followup_open_count: 0,
    followup_overdue_count: 0,
    coverage_counts: [],
    followup_queue: [],
    recent_decisions: [],
    recent_audit_events: [],
    notes: [],
  };
}

function growthRuleCatalogFixture() {
  return {
    catalog: {
      catalog_version: 'route-smoke-v1',
      schema_version: 'growth-rule-catalog.v1',
      limits: {
        max_nodes: 12,
        max_depth: 4,
        max_actions: 3,
        max_regex_length: 64,
      },
      fields: {
        'code.code_type': {
          type: 'string',
          operators: ['eq', 'in'],
        },
        'risk.score': {
          type: 'number',
          operators: ['gte', 'lte'],
        },
      },
      operators: {
        eq: {
          value_types: ['string', 'number', 'boolean'],
          safe_regex: false,
        },
        in: {
          value_types: ['array'],
          safe_regex: false,
        },
        gte: {
          value_types: ['number'],
          safe_regex: false,
        },
        lte: {
          value_types: ['number'],
          safe_regex: false,
        },
      },
      actions: {
        challenge: {
          result: 'challenge',
          params: ['challenge_type', 'message_key'],
        },
        reject: {
          result: 'reject',
          params: ['reason_code'],
        },
      },
    },
  };
}

function vpnTesterOverviewFixture() {
  return {
    enabled: true,
    runtime_enabled: true,
    scheduled_enabled: false,
    balancer_recommendations_enabled: false,
    counts: {
      total: 0,
      pass: 0,
      fail: 0,
      degraded: 0,
      queued: 0,
    },
    latest_runs: [],
    schedules: [],
  };
}

function emptyMatrixFixture() {
  return {
    registry_key: 'route-smoke',
    total: 0,
    rows: [],
  };
}

function releaseGateFixture() {
  return {
    status: 'pass',
    blocking: false,
    reason: null,
    checked_at: '2026-06-03T00:00:00.000Z',
    summary: 'Route smoke release gate',
  };
}

function checkoutQuoteFixture() {
  return {
    id: 'quote-smoke',
    quote_session_id: 'quote-smoke',
    pricebook_key: 'smoke-usd',
    currency: 'USD',
    subtotal: 9.99,
    total: 9.99,
    wallet_amount: 0,
    expires_at: '2026-06-03T00:10:00.000Z',
  };
}

function orderFixture() {
  return {
    id: 'order-smoke',
    status: 'pending_payment',
    currency: 'USD',
    total: 9.99,
    created_at: '2026-06-03T00:00:00.000Z',
  };
}

function paymentAttemptFixture() {
  return {
    id: 'payment-attempt-smoke',
    status: 'pending',
    provider: 'cryptobot',
    invoice: {
      invoice_id: 'invoice-smoke',
      payment_url: 'https://pay.example.invalid/smoke',
      status: 'pending',
    },
  };
}

function listEnvelope(items = []) {
  return {
    items,
    results: items,
    data: items,
    total: items.length,
    total_count: items.length,
    limit: 100,
    offset: 0,
  };
}

function fixtureForApiRequest(rawUrl, method, postData = null) {
  const url = new URL(rawUrl);
  const path = url.pathname.replace(/^\/api\/v1/, '').replace(/^\/api\/v3/, '');
  const lowerPath = path.toLowerCase();
  const normalizedMethod = method.toUpperCase();
  const partnerRemnawaveBasePath = `/partner-workspaces/${PARTNER_SMOKE_WORKSPACE_UUID}/remnawave`;
  const sessionFixture =
    SURFACE === 'admin'
      ? API_ROUTE_FIXTURES.admin
      : SURFACE === 'partner'
        ? API_ROUTE_FIXTURES.partner
        : API_ROUTE_FIXTURES.customer;

  if (url.pathname.startsWith('/api/analytics/') || lowerPath.includes('/client-errors')) {
    return { kind: 'empty' };
  }

  if (lowerPath.includes('/client/capabilities')) {
    return { kind: 'json', data: clientCapabilitiesFixture() };
  }
  if (lowerPath.includes('/public/network/dpi-score')) {
    return { kind: 'json', data: publicDpiScoreFixture() };
  }
  if (lowerPath.includes('/users/me/notifications')) {
    return { kind: 'json', data: notificationPreferencesFixture() };
  }
  if (lowerPath.includes('/users/me/fcm-token')) {
    return {
      kind: 'json',
      data: {
        id: 'fcm-smoke',
        device_id: 'admin-device-01',
        platform: 'ios',
        created_at: '2026-06-03T00:00:00.000Z',
      },
      status: normalizedMethod === 'POST' ? 201 : 200,
    };
  }

  if (lowerPath.includes('/auth/session') || lowerPath.includes('/auth/me') || rawUrl.includes('/api/auth/optional-session')) {
    return { kind: 'json', data: sessionFixture };
  }
  if (lowerPath.includes('/auth/passkeys/policy')) {
    return {
      kind: 'json',
      data: {
        enabled: true,
        surface: SURFACE,
        realm_key: SURFACE === 'partner' ? 'partner' : SURFACE === 'admin' ? 'admin' : 'customer',
        rp_id: 'localhost',
        rp_name: 'CyberVPN',
        allowedOrigins: [BASE_URL, STOREFRONT_BASE_URL],
        userVerification: 'required',
        conditionalUiEnabled: true,
        registrationEnabled: true,
        authenticationEnabled: true,
        reauthenticationEnabled: true,
        adminCountsAsMfa: false,
        challengeTtlSeconds: 120,
        browserTimeoutMs: 60_000,
      },
    };
  }
  if (lowerPath.includes('/auth/passkeys/authentication/options')) {
    return {
      kind: 'json',
      data: {
        challengeId: 'route-smoke-challenge',
        expiresAt: '2026-06-03T00:02:00.000Z',
        publicKey: {
          challenge: 'cm91dGUtc21va2UtY2hhbGxlbmdl',
          rpId: 'localhost',
          allowCredentials: [],
          timeout: 60_000,
          userVerification: 'required',
        },
      },
    };
  }
  if (lowerPath.includes('/auth/login') || lowerPath.includes('/auth/register') || lowerPath.includes('/auth/refresh')) {
    return {
      kind: 'json',
      data: {
        access_token: 'cookie-managed',
        refresh_token: 'cookie-managed',
        token_type: 'bearer',
        expires_in: 3600,
        requires_2fa: false,
        tfa_token: null,
      },
    };
  }
  if (lowerPath.includes('/auth/logout')) {
    return { kind: 'json', data: { message: 'Signed out' } };
  }
  if (lowerPath.includes('/users/me/profile') || lowerPath === '/profile') {
    return {
      kind: 'json',
      data: {
        ...sessionFixture,
        display_name: 'Smoke Operator',
        avatar_url: null,
        language: LOCALE,
        timezone: 'UTC',
        public_uid: 14677650,
      },
    };
  }

  if (lowerPath === '/admin/partner-workspaces') {
    return { kind: 'json', data: [adminPartnerWorkspaceFixture()] };
  }
  if (/\/admin\/partner-workspaces\/[^/]+$/.test(lowerPath)) {
    return { kind: 'json', data: adminPartnerWorkspaceFixture() };
  }
  if (lowerPath === '/admin/partner-applications') {
    return { kind: 'json', data: [adminPartnerApplicationSummaryFixture()] };
  }
  if (/\/admin\/partner-applications\/[^/]+$/.test(lowerPath)) {
    return { kind: 'json', data: adminPartnerApplicationDetailFixture() };
  }

  if (lowerPath.includes('/partner-session/bootstrap')) {
    return { kind: 'json', data: partnerBootstrapFixture() };
  }
  if (lowerPath.includes('/partner-workspaces/me')) {
    return { kind: 'json', data: [API_ROUTE_FIXTURES.workspace] };
  }
  if (/\/partner-workspaces\/[^/]+$/.test(lowerPath)) {
    return { kind: 'json', data: API_ROUTE_FIXTURES.workspace };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/members')) {
    return { kind: 'json', data: API_ROUTE_FIXTURES.workspace.members };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/roles')) {
    return { kind: 'json', data: partnerWorkspaceRolesFixture() };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/programs')) {
    return { kind: 'json', data: partnerWorkspaceProgramsFixture() };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/lane-applications')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/review-requests')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/cases')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/finance-summary')) {
    return {
      kind: 'json',
      data: {
        availableEarnings: '$120',
        onHoldEarnings: '$0',
        reserves: '$0',
        nextPayoutForecast: '$120',
        currency: 'USD',
        available_earnings: '120.00',
        on_hold_earnings: '0.00',
        total: '120.00',
      },
    };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/commercial-capabilities')) {
    return {
      kind: 'json',
      data: {
        partner_cash_payout_allowed: true,
        payout_account_required: false,
        reseller_storefront_allowed: true,
        pricebook_preview_allowed: true,
      },
    };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/settings')) {
    return { kind: 'json', data: partnerWorkspaceSettingsFixture() };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/organization-profile')) {
    return { kind: 'json', data: partnerWorkspaceOrganizationProfileFixture() };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/security/passkeys/policy')) {
    return { kind: 'json', data: partnerWorkspacePasskeyPolicyFixture() };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/security/passkeys/compliance')) {
    return {
      kind: 'json',
      data: {
        ...partnerWorkspacePasskeyPolicyFixture(),
        credentials: [],
        summary: {
          activeCredentials: 1,
          cloneSuspectedCredentials: 0,
          generatedAt: '2026-06-03T00:00:00.000Z',
          principalsWithActivePasskeys: 1,
          revokedCredentials: 0,
          staleCredentials: 0,
        },
      },
    };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/payout-accounts')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/partner-workspaces/') && lowerPath.includes('/payout-history')) {
    return { kind: 'json', data: listEnvelope([]) };
  }
  if (lowerPath.includes('/partner-notifications/counters')) {
    return { kind: 'json', data: { unread: 1, archived: 0, total: 1 } };
  }
  if (lowerPath.includes('/partner-notifications/preferences')) {
    return { kind: 'json', data: { email: true, in_app: true, payout_status_emails: true } };
  }
  if (lowerPath.includes('/partner-notifications')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/partner-application-drafts/current')) {
    return { kind: 'json', data: null };
  }
  if (lowerPath.includes('/partner-bots')) {
    return { kind: 'json', data: [] };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath.includes('/partner-workspaces/')
    && [
      '/reseller-voucher-batches',
      '/analytics-metrics',
      '/report-exports',
      '/integration-credentials',
      '/integration-delivery-logs',
    ].some((suffix) => lowerPath.endsWith(suffix))
  ) {
    return { kind: 'json', data: [] };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath === `/partner-workspaces/${PARTNER_SMOKE_WORKSPACE_UUID}/vpn-service-status`
  ) {
    return { kind: 'json', data: partnerRemnawaveStatusFixture() };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath === `${partnerRemnawaveBasePath}/resources`
  ) {
    return { kind: 'json', data: partnerRemnawaveResourceListFixture() };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath === `${partnerRemnawaveBasePath}/resources/profile/${PARTNER_SMOKE_PROFILE_UUID}`
  ) {
    return { kind: 'json', data: partnerRemnawaveResourceFixture('profile') };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath === `${partnerRemnawaveBasePath}/resources/integration/${PARTNER_SMOKE_INTEGRATION_UUID}`
  ) {
    return { kind: 'json', data: partnerRemnawaveResourceFixture('integration') };
  }
  if (
    normalizedMethod === 'PATCH'
    && lowerPath === `${partnerRemnawaveBasePath}/resources/profile/${PARTNER_SMOKE_PROFILE_UUID}/tags`
  ) {
    const body = parseFixtureRequestBody(postData);
    assert(
      JSON.stringify(body) === JSON.stringify({ tags: ['EDGE:RU', 'VISION'] }),
      'Partner profile-tags smoke must submit only the expected bounded tag list',
    );
    return {
      kind: 'json',
      data: {
        resource_uuid: PARTNER_SMOKE_PROFILE_UUID,
        tags: body.tags,
      },
      status: 200,
    };
  }
  if (
    normalizedMethod === 'PATCH'
    && lowerPath === `${partnerRemnawaveBasePath}/resources/integration/${PARTNER_SMOKE_INTEGRATION_UUID}/metadata`
  ) {
    const body = parseFixtureRequestBody(postData);
    assert(
      JSON.stringify(body) === JSON.stringify({ name: 'Route Smoke Metrics' }),
      'Partner integration-metadata smoke must submit only the expected bounded display name',
    );
    return {
      kind: 'json',
      data: {
        attempt_id: PARTNER_SMOKE_MUTATION_ATTEMPT_UUID,
        state: 'reconciliation_required',
        resource_type: 'integration',
        resource_uuid: PARTNER_SMOKE_INTEGRATION_UUID,
        requires_reconciliation: true,
      },
      status: 202,
    };
  }

  if (lowerPath.includes('/admin/audit-log')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/admin/privacy-requests/queue-count')) {
    return { kind: 'json', data: { count: 0 } };
  }
  if (/\/admin\/privacy-requests\/[^/]+$/.test(lowerPath)) {
    return { kind: 'json', data: privacyRequestFixture() };
  }
  if (lowerPath.includes('/admin/privacy-requests')) {
    const request = privacyRequestFixture();
    return {
      kind: 'json',
      data: {
        requests: [request],
        next_cursor: null,
      },
    };
  }
  if (lowerPath.includes('/security/risk-reviews/queue')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/admin/growth-signals/abuse-queue')) {
    return { kind: 'json', data: { items: [], total: 0, count: 0, next_cursor: null } };
  }
  if (lowerPath.includes('/admin/growth-reporting/overview')) {
    return { kind: 'json', data: adminGrowthReportingOverviewFixture() };
  }
  if (lowerPath.includes('/admin/growth-reporting/governance')) {
    return { kind: 'json', data: adminGrowthReportingGovernanceFixture() };
  }
  if (lowerPath.includes('/admin/growth-reporting/subscriptions') || lowerPath.includes('/admin/growth-reporting/deliveries')) {
    return { kind: 'json', data: { items: [], total: 0 } };
  }
  if (lowerPath.includes('/admin/growth/rule-catalog')) {
    return { kind: 'json', data: growthRuleCatalogFixture() };
  }
  if (lowerPath.includes('/admin/promo-codes')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/admin/partners')) {
    return { kind: 'json', data: { items: [], total: 0, offset: 0, limit: 100 } };
  }
  if (lowerPath.includes('/admin/commercial-context/options')) {
    return { kind: 'json', data: commercialContextOptionsFixture() };
  }
  if (/\/admin\/support\/tickets\/[^/]+$/.test(lowerPath)) {
    return { kind: 'json', data: supportTicketFixture() };
  }
  if (lowerPath.includes('/admin/support/tickets')) {
    const ticket = supportTicketFixture();
    if (normalizedMethod !== 'GET') {
      return { kind: 'json', data: ticket };
    }
    return { kind: 'json', data: { tickets: [ticket], items: [ticket], total: 1, limit: 50, offset: 0 } };
  }
  if (/\/admin\/messaging\/conversations\/[^/]+$/.test(lowerPath)) {
    return { kind: 'json', data: messagingConversationFixture() };
  }
  if (lowerPath.includes('/admin/messaging/conversations')) {
    const conversation = messagingConversationFixture();
    if (normalizedMethod !== 'GET') {
      return { kind: 'json', data: conversation };
    }
    return {
      kind: 'json',
      data: {
        conversations: [conversation],
        items: [conversation],
        total: 1,
        limit: 50,
        offset: 0,
      },
    };
  }
  if (lowerPath.includes('/admin/webhook-log')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/admin/system-config/miniapp-launch-readiness')) {
    return { kind: 'json', data: miniAppLaunchReadinessConfigFixture() };
  }
  if (lowerPath.includes('/admin/system-config/miniapp-launch-summary')) {
    return { kind: 'json', data: miniAppLaunchSummaryFixture() };
  }
  if (lowerPath.includes('/admin/system-config/miniapp-launch-timeline')) {
    return { kind: 'json', data: miniAppLaunchTimelineFixture() };
  }
  if (lowerPath.includes('/admin/system-config/miniapp-launch-actions')) {
    return { kind: 'json', data: miniAppLaunchSummaryFixture() };
  }
  if (lowerPath.includes('/admin/system-config/miniapp-runtime')) {
    return { kind: 'json', data: miniAppRuntimeConfigFixture() };
  }
  if (lowerPath.includes('/admin/referrals/users/')) {
    return { kind: 'json', data: adminReferralUserDetailFixture() };
  }
  if (lowerPath.includes('/admin/mobile-users/') && lowerPath.includes('/customer-subscriptions')) {
    return { kind: 'json', data: adminCustomerSubscriptionsFixture() };
  }
  if (lowerPath.includes('/admin/mobile-users/') && lowerPath.includes('/subscription')) {
    return {
      kind: 'json',
      data: {
        exists: true,
        remnawave_uuid: 'remna-smoke',
        status: 'active',
        short_uuid: 'vpn-smoke',
        subscription_uuid: 'subscription-smoke',
        expires_at: '2026-12-31T00:00:00.000Z',
        days_left: 177,
        traffic_limit_bytes: null,
        used_traffic_bytes: 0,
        download_bytes: 0,
        upload_bytes: 0,
        lifetime_used_traffic_bytes: 0,
        online_at: '2026-06-03T00:00:00.000Z',
      },
    };
  }
  if (lowerPath.includes('/admin/mobile-users/') && lowerPath.includes('/payment-attempts')) {
    return { kind: 'json', data: listEnvelope([]) };
  }
  if (lowerPath.includes('/admin/mobile-users/') && lowerPath.includes('/notes')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/admin/mobile-users/') && lowerPath.includes('/timeline')) {
    return { kind: 'json', data: { items: [] } };
  }
  if (lowerPath.includes('/admin/mobile-users/') && lowerPath.includes('/operations-insight')) {
    return {
      kind: 'json',
      data: {
        section_access: {
          finance_visible: true,
          finance_actions_visible: false,
          risk_visible: true,
        },
        order_insights: [],
        service_access_insights: [],
        settlement_workspaces: [],
        risk_subject_insights: [],
      },
    };
  }
  if (lowerPath.includes('/admin/mobile-users/') && lowerPath.includes('/vpn-user')) {
    return {
      kind: 'json',
      data: {
        exists: true,
        status: 'active',
        username: 'customer-smoke',
        email: 'customer-smoke@example.invalid',
        short_uuid: 'vpn-smoke',
        subscription_uuid: 'subscription-smoke',
        expire_at: '2026-12-31T00:00:00.000Z',
        created_at: '2026-06-03T00:00:00.000Z',
        telegram_id: 123456,
        used_traffic_bytes: 0,
        traffic_limit_bytes: null,
      },
    };
  }
  if (/\/admin\/mobile-users\/[^/]+$/.test(lowerPath)) {
    return { kind: 'json', data: adminMobileUserFixture() };
  }
  if (lowerPath.includes('/admin/mobile-users')) {
    const user = adminMobileUserFixture();
    return { kind: 'json', data: { items: [user], total: 1, offset: 0, limit: 50 } };
  }
  if (lowerPath.includes('/storefronts/') && lowerPath.includes('/preview')) {
    return { kind: 'json', data: storefrontPreviewFixture() };
  }
  if (lowerPath.includes('/growth-notifications/preferences')) {
    return { kind: 'json', data: growthNotificationPreferencesFixture() };
  }
  if (lowerPath.includes('/growth-notifications/counters')) {
    return { kind: 'json', data: growthNotificationCountersFixture() };
  }
  if (lowerPath.includes('/growth-notifications')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/referral/status')) {
    return { kind: 'json', data: referralStatusFixture() };
  }
  if (lowerPath.includes('/referral/code')) {
    return { kind: 'json', data: referralCodeFixture() };
  }
  if (lowerPath.includes('/referral/stats')) {
    return { kind: 'json', data: referralStatsFixture() };
  }
  if (lowerPath.includes('/referral/recent')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/referral/rewards')) {
    return { kind: 'json', data: [referralRewardFixture()] };
  }
  if (lowerPath.includes('/referral/attribution') || lowerPath.includes('/referral/claim')) {
    return { kind: 'json', data: { status: 'captured', masked_code: 'SMOK****' } };
  }
  if (lowerPath.includes('/gifts/my') || lowerPath.includes('/invites/my')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath === '/settings/' || lowerPath === '/settings') {
    return { kind: 'json', data: [adminSettingFixture()] };
  }
  if (lowerPath.includes('/addons')) {
    return { kind: 'json', data: [adminAddonFixture()] };
  }
  if (lowerPath.includes('/catalog/context')) {
    return { kind: 'json', data: publicCatalogContextFixture() };
  }
  if (lowerPath.includes('/catalog')) {
    return { kind: 'json', data: publicCatalogFixture() };
  }
  if (lowerPath.includes('/pricebooks/resolve')) {
    return { kind: 'json', data: publicCatalogFixture().pricebooks };
  }
  if (lowerPath === '/customer-subscriptions/' || lowerPath === '/customer-subscriptions') {
    return { kind: 'json', data: customerSubscriptionsFixture() };
  }
  if (lowerPath.includes('/customer-subscriptions/') && lowerPath.includes('/entitlements')) {
    return { kind: 'json', data: currentEntitlementFixture() };
  }
  if (lowerPath.includes('/customer-subscriptions/') && lowerPath.includes('/service-state')) {
    return {
      kind: 'json',
      data: {
        entitlement_snapshot: currentEntitlementFixture(),
        consumption_context: { credential_subject_key: 'smoke-subject' },
        access_delivery_channel: { channel_type: 'web' },
        service_identity: {
          id: 'service-smoke',
          provider_subject_ref: null,
          provider_name: 'route-smoke',
        },
      },
    };
  }
  if (lowerPath.includes('/customer-subscriptions/') && lowerPath.includes('/usage')) {
    return { kind: 'json', data: { used_traffic_bytes: 0, traffic_limit_bytes: null, reset_at: null } };
  }
  if (lowerPath.includes('/customer-subscriptions/') && lowerPath.includes('/config')) {
    return { kind: 'json', data: customerSubscriptionConfigFixture() };
  }
  if (/\/customer-subscriptions\/[^/]+$/.test(lowerPath)) {
    return { kind: 'json', data: customerSubscriptionsFixture().items[0] };
  }
  if (lowerPath === '/orders/' || lowerPath === '/orders') {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/orders/commit') || /\/orders\/[^/]+$/.test(lowerPath)) {
    return { kind: 'json', data: orderFixture(), status: normalizedMethod === 'POST' ? 201 : 200 };
  }
  if (lowerPath.includes('/offers')) {
    return { kind: 'json', data: publicCatalogFixture().offers };
  }
  if (lowerPath.includes('/addons')) {
    return { kind: 'json', data: [adminAddonFixture()] };
  }
  if (lowerPath.includes('/plans')) {
    return { kind: 'json', data: [adminPlanFixture()] };
  }
  if (lowerPath.includes('/subscription')) {
    return { kind: 'json', data: publicCatalogFixture().plans };
  }
  if (lowerPath.includes('/payments/history')) {
    return { kind: 'json', data: paymentHistoryFixture() };
  }
  if (lowerPath.includes('/payments/checkout/quote')) {
    return { kind: 'json', data: checkoutQuoteFixture() };
  }
  if (lowerPath.includes('/payments/checkout/commit') || lowerPath.endsWith('/payments/checkout')) {
    return { kind: 'json', data: orderFixture() };
  }
  if (lowerPath.includes('/payments/crypto/invoice') || lowerPath.includes('/payments/create')) {
    return { kind: 'json', data: paymentAttemptFixture(), status: normalizedMethod === 'POST' ? 201 : 200 };
  }
  if (lowerPath.includes('/payments')) {
    return { kind: 'json', data: paymentHistoryFixture() };
  }
  if (lowerPath.includes('/wallet/transactions')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/wallet') || lowerPath.includes('/withdrawal')) {
    return { kind: 'json', data: lowerPath.includes('/withdrawals') ? [] : walletFixture() };
  }
  if (lowerPath.includes('/entitlements')) {
    return { kind: 'json', data: currentEntitlementFixture() };
  }
  if (lowerPath.includes('/service-state')) {
    return {
      kind: 'json',
      data: {
        entitlement_snapshot: { status: 'active' },
        consumption_context: { credential_subject_key: 'smoke-subject' },
        access_delivery_channel: { channel_type: 'web' },
      },
    };
  }
  if (lowerPath.includes('/admin/vpn-tester/overview')) {
    return { kind: 'json', data: vpnTesterOverviewFixture() };
  }
  if (lowerPath.includes('/admin/vpn-tester/tariffs') || lowerPath.includes('/admin/vpn-tester/route-matrix')) {
    return { kind: 'json', data: emptyMatrixFixture() };
  }
  if (lowerPath.includes('/admin/vpn-tester/release-gate')) {
    return { kind: 'json', data: releaseGateFixture() };
  }
  if (
    lowerPath.includes('/admin/vpn-tester/runs') ||
    lowerPath.includes('/admin/vpn-tester/schedules') ||
    lowerPath.includes('/admin/vpn-tester/balancer/recommendations')
  ) {
    return { kind: 'json', data: [] };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath === '/admin/remnawave/capabilities-and-streams'
  ) {
    return {
      kind: 'json',
      data: {
        panel_version: '3.4.3',
        target_panel_version: '3.4.3',
        target_node_version: '3.4.1',
        contract_version: '3.4.13',
        capabilities: {
          numeric_user_ids: true,
          connections: true,
          geo_check: true,
          node_integrations: true,
          shared_lists: true,
          node_ssh: true,
          tags: true,
          host_mapper: true,
          root_snippets: true,
          redis_stream_export: true,
        },
        streams: [],
        degraded_reason: null,
      },
    };
  }
  if (
    normalizedMethod === 'GET'
    && /^\/admin\/remnawave-operator\/tags\/[^/]+$/.test(lowerPath)
  ) {
    return {
      kind: 'json',
      data: {
        resource: lowerPath.split('/').at(-1),
        tags: ['EDGE_EU', 'EDGE_RU'],
      },
    };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath === '/admin/remnawave-operator/node-integrations'
  ) {
    return {
      kind: 'json',
      data: {
        total: 1,
        items: [
          {
            uuid: '550e8400-e29b-41d4-a716-446655440000',
            name: 'route-smoke-metrics',
            description: 'Redacted route-smoke integration',
            config: {
              endpoint: 'https://example.invalid/metrics',
              token: '<redacted>',
            },
          },
        ],
      },
    };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath === '/admin/remnawave-operator/shared-lists/by-name'
  ) {
    return {
      kind: 'json',
      data: {
        name: url.searchParams.get('name') ?? 'route-smoke-routing',
        config: { type: 'cidr', items: ['192.0.2.0/24'] },
      },
    };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath === '/admin/remnawave-operator/shared-lists'
  ) {
    return {
      kind: 'json',
      data: {
        total: 1,
        items: [{ name: 'route-smoke-routing', type: 'cidr', itemsCount: 1 }],
      },
    };
  }
  if (
    normalizedMethod === 'GET'
    && lowerPath === '/admin/remnawave-operator/snippets'
  ) {
    return {
      kind: 'json',
      data: {
        total: 1,
        items: [
          {
            name: 'route-smoke-headers',
            snippet: [{ name: 'X-Route-Smoke', value: '<redacted>' }],
          },
        ],
      },
    };
  }
  if (
    normalizedMethod === 'GET'
    && /^\/admin\/remnawave-operator\/geocheck\/jobs\/[^/]+$/.test(lowerPath)
  ) {
    return {
      kind: 'json',
      data: {
        isCompleted: true,
        isFailed: false,
        result: {
          success: true,
          nodeUuid: '550e8400-e29b-41d4-a716-446655440001',
          image: null,
          rawReport: { status: 'ok' },
          message: 'Deterministic route-smoke result',
        },
      },
    };
  }
  if (lowerPath.includes('/config-profiles') || lowerPath.includes('/hosts') || lowerPath.includes('/inbounds') || lowerPath.includes('/servers') || lowerPath.includes('/snippets') || lowerPath.includes('/squads/') || lowerPath.includes('/squads/internal') || lowerPath.includes('/squads/external') || lowerPath.includes('/helix/admin/nodes')) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/xray/config')) {
    return { kind: 'json', data: { config: '{}', updated_at: '2026-06-03T00:00:00.000Z' } };
  }
  if (lowerPath.includes('/support') || lowerPath.includes('/tickets') || lowerPath.includes('/cases') || lowerPath.includes('/messaging')) {
    return { kind: 'json', data: listEnvelope([]) };
  }
  if (
    lowerPath.includes('/traffic-declarations') ||
    lowerPath.includes('/creative-approvals') ||
    lowerPath.includes('/partner-payout-accounts') ||
    lowerPath.includes('/payouts/instructions') ||
    lowerPath.includes('/payouts/executions') ||
    lowerPath.includes('/security/governance-actions')
  ) {
    return { kind: 'json', data: [] };
  }
  if (lowerPath.includes('/analytics') || lowerPath.includes('/reporting') || lowerPath.includes('/metrics')) {
    return { kind: 'json', data: listEnvelope([]) };
  }
  if (lowerPath.includes('/codes') || lowerPath.includes('/campaign') || lowerPath.includes('/conversion') || lowerPath.includes('/statements')) {
    return { kind: 'json', data: [] };
  }

  return { kind: 'json', data: listEnvelope([]) };
}

function installBrowserMocksSource() {
  return `
    class MockPublicKeyCredential {}
    MockPublicKeyCredential.isConditionalMediationAvailable = async () => true;
    MockPublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable = async () => true;
    Object.defineProperty(window, 'PublicKeyCredential', { configurable: true, value: MockPublicKeyCredential });
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true });
    Object.defineProperty(navigator, 'credentials', {
      configurable: true,
      value: { get: () => new Promise(() => {}) },
    });
    if (location.pathname.includes('/miniapp')) {
      window.Telegram = window.Telegram || {};
      window.Telegram.WebApp = window.Telegram.WebApp || {
        initData: 'query_id=smoke&user=%7B%22id%22%3A1001%7D&auth_date=1783017600&hash=smoke',
        initDataUnsafe: { user: { id: 1001, first_name: 'Smoke' } },
        platform: 'tdesktop',
        colorScheme: 'dark',
        ready() {},
        expand() {},
        close() {},
        showAlert(message) { console.info('Telegram alert', message); },
        showConfirm(_message, callback) { callback(true); },
        MainButton: { show() {}, hide() {}, setText() {}, onClick() {}, offClick() {} },
        BackButton: { show() {}, hide() {}, onClick() {}, offClick() {} },
        HapticFeedback: { impactOccurred() {}, notificationOccurred() {}, selectionChanged() {} },
      };
    }
    window.EventSource = class MockEventSource extends EventTarget {
      constructor(url) {
        super();
        this.url = url;
        this.readyState = 1;
      }
      close() { this.readyState = 2; }
    };
  `;
}

function isPartnerDashboardRoute(route) {
  return SURFACE === 'partner'
    && !LIVE_API
    && route.group === 'dashboard'
    && /\/dashboard\/?$/.test(new URL(route.url).pathname);
}

async function clickPartnerRemnawaveResource(client, sessionId, resourceUuid) {
  const resourceUuidLiteral = JSON.stringify(resourceUuid);
  await waitForExpression(
    client,
    sessionId,
    `Array.from(document.querySelectorAll('code')).some((item) => item.textContent?.trim() === ${resourceUuidLiteral})`,
    ASSERTION_TIMEOUT_MS,
    `Partner Remnawave resource did not render: ${resourceUuid}`,
  );
  const clicked = await evaluate(
    client,
    sessionId,
    `
      (() => {
        const resource = Array.from(document.querySelectorAll('code'))
          .find((item) => item.textContent?.trim() === ${resourceUuidLiteral});
        const button = resource?.closest('li')?.querySelector('button');
        if (!(button instanceof HTMLButtonElement) || button.disabled) return false;
        button.click();
        return true;
      })()
    `,
  );
  assert(clicked, `Partner Remnawave inspect control was unavailable for ${resourceUuid}`);
}

async function setPartnerRemnawaveInput(client, sessionId, inputId, value) {
  const inputIdLiteral = JSON.stringify(inputId);
  const valueLiteral = JSON.stringify(value);
  try {
    await waitForExpression(
      client,
      sessionId,
      `document.getElementById(${inputIdLiteral}) instanceof HTMLInputElement`,
      ASSERTION_TIMEOUT_MS,
      `Partner Remnawave mutation input did not render: ${inputId}`,
    );
  } catch (error) {
    const renderedContext = await evaluate(
      client,
      sessionId,
      `
        JSON.stringify({
          inputs: Array.from(document.querySelectorAll('input')).map((item) => item.id).filter(Boolean),
          remnawaveSection: document.getElementById('partner-remnawave-resources-title')
            ?.closest('section')
            ?.innerText
            ?.replace(/\\s+/g, ' ')
            .trim()
            .slice(0, 1600) ?? null,
        })
      `,
    );
    throw new Error(`${error instanceof Error ? error.message : String(error)} Context: ${renderedContext}`);
  }
  const changed = await evaluate(
    client,
    sessionId,
    `
      (() => {
        const input = document.getElementById(${inputIdLiteral});
        const valueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
        if (!(input instanceof HTMLInputElement) || !valueSetter || input.disabled) return false;
        valueSetter.call(input, ${valueLiteral});
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return input.value === ${valueLiteral};
      })()
    `,
  );
  assert(changed, `Partner Remnawave mutation input could not be changed: ${inputId}`);
  await sleep(100);
}

async function submitPartnerRemnawaveForm(client, sessionId, inputId) {
  const inputIdLiteral = JSON.stringify(inputId);
  const submitted = await evaluate(
    client,
    sessionId,
    `
      (() => {
        const input = document.getElementById(${inputIdLiteral});
        const form = input?.closest('form');
        const button = form?.querySelector('button[type="submit"]');
        if (!(form instanceof HTMLFormElement) || !(button instanceof HTMLButtonElement) || button.disabled) return false;
        form.requestSubmit(button);
        return true;
      })()
    `,
  );
  assert(submitted, `Partner Remnawave mutation form could not be submitted: ${inputId}`);
}

async function runPartnerRemnawaveDashboardInteractions(client, sessionId, diagnostics) {
  const workspace = API_ROUTE_FIXTURES.workspace;
  assert(!workspace.current_permission_keys.includes('*'), 'Partner Remnawave smoke role must never use wildcard permissions');
  assert(
    workspace.current_permission_keys.includes('remnawave_read')
      && workspace.current_permission_keys.includes('remnawave_write'),
    'Partner Remnawave smoke role must explicitly include remnawave_read and remnawave_write',
  );
  assert(
    !workspace.current_permission_keys.includes('remnawave_execute')
      && !workspace.current_permission_keys.includes('remnawave_ssh'),
    'Partner Remnawave safe-mutation smoke must not inherit execute or SSH permissions',
  );

  await clickPartnerRemnawaveResource(client, sessionId, PARTNER_SMOKE_PROFILE_UUID);
  const profileInputId = `profile-tags-${PARTNER_SMOKE_PROFILE_UUID}`;
  await setPartnerRemnawaveInput(client, sessionId, profileInputId, 'EDGE:RU, VISION');
  await submitPartnerRemnawaveForm(client, sessionId, profileInputId);
  await waitForExpression(
    client,
    sessionId,
    `
      document.getElementById(${JSON.stringify(profileInputId)})
        ?.closest('form')
        ?.querySelector('[role="status"]')
        ?.textContent
        ?.includes('Scoped mutation confirmed') === true
    `,
    ASSERTION_TIMEOUT_MS,
    'Partner profile-tags mutation did not render its verified 200 outcome',
  );

  await clickPartnerRemnawaveResource(client, sessionId, PARTNER_SMOKE_INTEGRATION_UUID);
  const integrationInputId = `integration-name-${PARTNER_SMOKE_INTEGRATION_UUID}`;
  await setPartnerRemnawaveInput(client, sessionId, integrationInputId, 'Route Smoke Metrics');
  await submitPartnerRemnawaveForm(client, sessionId, integrationInputId);
  await waitForExpression(
    client,
    sessionId,
    `
      (() => {
        const input = document.getElementById(${JSON.stringify(integrationInputId)});
        const status = input?.closest('form')?.querySelector('[role="status"]');
        return input instanceof HTMLInputElement
          && input.disabled
          && status?.textContent?.includes('Mutation requires reconciliation') === true;
      })()
    `,
    ASSERTION_TIMEOUT_MS,
    'Partner integration-metadata mutation did not render and lock its 202 reconciliation outcome',
  );

  const boundary = await evaluate(
    client,
    sessionId,
    `
      (() => {
        const interactive = Array.from(document.querySelectorAll('a[href], button, [role="button"], input[type="submit"]'))
          .map((item) => ({
            label: (item.getAttribute('aria-label') || item.textContent || '').replace(/\\s+/g, ' ').trim(),
            href: item instanceof HTMLAnchorElement ? item.getAttribute('href') : null,
          }));
        const forbiddenLabel = /(?:\\b(?:open|launch|connect|manage|configure)\\s+(?:browser\\s+)?ssh\\b|\\bnode\\s+ssh\\b|\\bglobal(?:\\s+remnawave)?\\s+(?:settings|controls|configuration)\\b|\\bplatform\\s+tokens?\\b)/i;
        const forbiddenHref = /(?:^|\\/)(?:admin|node-ssh|browser-ssh)(?:\\/|$)/i;
        return {
          sshBoundaryRendered: document.body?.innerText?.toLowerCase().includes('browser ssh prohibited') === true,
          forbiddenInteractiveControls: interactive.filter((item) => (
            forbiddenLabel.test(item.label) || (typeof item.href === 'string' && forbiddenHref.test(item.href))
          )),
        };
      })()
    `,
  );
  assert(boundary.sshBoundaryRendered, 'Partner dashboard did not render the explicit browser SSH prohibition');
  assert(
    boundary.forbiddenInteractiveControls.length === 0,
    `Partner dashboard exposed SSH/global interactive controls: ${JSON.stringify(boundary.forbiddenInteractiveControls)}`,
  );

  const profilePath = `/api/v1/partner-workspaces/${PARTNER_SMOKE_WORKSPACE_UUID}/remnawave/resources/profile/${PARTNER_SMOKE_PROFILE_UUID}/tags`;
  const integrationPath = `/api/v1/partner-workspaces/${PARTNER_SMOKE_WORKSPACE_UUID}/remnawave/resources/integration/${PARTNER_SMOKE_INTEGRATION_UUID}/metadata`;
  const capturedMutations = diagnostics.partnerRemnawaveMutationRequests;
  assert(capturedMutations.length === 2, `Expected exactly two Partner Remnawave PATCH requests, received ${capturedMutations.length}`);
  assert(
    capturedMutations.every((request) => request.idempotencyKeyPresent),
    'Every Partner Remnawave safe mutation must carry a bounded Idempotency-Key',
  );
  const profileResponse = diagnostics.apiResponses.find((response) => (
    response.method === 'PATCH' && response.path === profilePath
  ));
  const integrationResponse = diagnostics.apiResponses.find((response) => (
    response.method === 'PATCH' && response.path === integrationPath
  ));
  assert(profileResponse?.status === 200, 'Partner profile-tags PATCH did not complete with HTTP 200');
  assert(integrationResponse?.status === 202, 'Partner integration-metadata PATCH did not complete with HTTP 202');
  const forbiddenApiRequests = diagnostics.apiRequests.filter((request) => (
    request.path.includes('/ssh')
    || request.path.includes('/node-ssh')
    || request.path.startsWith('/api/v1/admin/remnawave')
  ));
  assert(
    forbiddenApiRequests.length === 0,
    `Partner dashboard issued forbidden SSH/global API requests: ${JSON.stringify(forbiddenApiRequests)}`,
  );

  return {
    status: 'passed',
    rolePermissions: [...workspace.current_permission_keys],
    wildcardPermission: false,
    objectGrants: partnerRemnawaveResourceListFixture().items.map((resource) => ({
      resourceType: resource.resource_type,
      resourceUuid: resource.resource_uuid,
      effectivePermissions: resource.effective_permissions,
      safeMutations: resource.safe_mutations,
      browserSsh: false,
    })),
    mutations: capturedMutations.map((request) => ({
      method: request.method,
      path: request.path,
      status: diagnostics.apiResponses.find((response) => (
        response.method === request.method && response.path === request.path
      ))?.status ?? null,
      body: request.body,
      idempotencyKeyPresent: request.idempotencyKeyPresent,
    })),
    renderedOutcomes: ['Scoped mutation confirmed', 'Mutation requires reconciliation'],
    boundary: {
      sshProhibitionRendered: true,
      forbiddenInteractiveControlCount: 0,
      forbiddenApiRequestCount: 0,
    },
  };
}

async function setAuthCookies(client, sessionId, urls, liveCookieJar = null) {
  for (const url of urls) {
    const cookieUrl = new URL(url).origin;
    if (liveCookieJar) {
      for (const cookie of liveCookieJar.cookiesForOrigin(url)) {
        if (!canMirrorLiveCookieToChromium(cookie)) {
          continue;
        }
        const params = {
          name: cookie.name,
          value: cookie.value,
          url: cookieUrl,
          path: cookie.path,
          httpOnly: cookie.httpOnly,
          secure: cookie.secure,
          sameSite: cdpSameSite(cookie),
        };
        if (!cookie.hostOnly && cookie.domain) {
          params.domain = cookie.domain;
        }
        const result = await client.send('Network.setCookie', params, sessionId);
        assert(result.success !== false, `Chromium rejected live auth cookie ${cookie.name} for ${cookieUrl}.`);
      }
      continue;
    }

    for (const name of [
      'access_token',
      'refresh_token',
      'customer_access_token',
      'customer_refresh_token',
      'partner_access_token',
      'partner_refresh_token',
    ]) {
      await client.send('Network.setCookie', {
        name,
        value: 'route-smoke',
        url: cookieUrl,
        path: '/',
        httpOnly: true,
        secure: false,
        sameSite: 'Lax',
      }, sessionId).catch(() => null);
    }
    if (SURFACE === 'partner') {
      await client.send('Network.setCookie', {
        name: 'DEV_BYPASS_AUTH',
        value: 'true',
        url: cookieUrl,
        path: '/',
        secure: false,
        sameSite: 'Lax',
      }, sessionId).catch(() => null);
    }
  }
}

function canMirrorLiveCookieToChromium(cookie) {
  if (cookie.name.startsWith('__Host-')) {
    return cookie.secure && cookie.hostOnly && cookie.path === '/';
  }
  if (cookie.name.startsWith('__Secure-')) {
    return cookie.secure;
  }
  return true;
}

function cdpSameSite(cookie) {
  const raw = String(cookie.attributes.get('samesite') || 'Lax').toLowerCase();
  if (raw === 'strict') return 'Strict';
  if (raw === 'none') return 'None';
  return 'Lax';
}

function buildHostResolverRules() {
  const configured = process.env.WEB_ROUTE_SMOKE_HOST_RESOLVER_RULES?.trim();
  if (configured) {
    return configured;
  }

  const connect = new URL(CONNECT_BASE_URL);
  const connectHost = connect.hostname;
  const rules = [];
  for (const rawUrl of [BASE_URL, STOREFRONT_BASE_URL]) {
    const url = new URL(rawUrl);
    if (url.hostname !== connectHost && isLoopbackHost(connectHost)) {
      rules.push(`MAP ${url.hostname} ${connectHost}`);
    }
  }
  return [...new Set(rules)].join(',');
}

function isLoopbackHost(hostname) {
  return hostname === '127.0.0.1' || hostname === 'localhost' || hostname === '::1';
}

function isBenignConsoleError(message) {
  const text = String(message || '');
  return (
    text.includes('ResizeObserver loop') ||
    text.includes('net::ERR_ABORTED') ||
    text.includes('Failed to load resource: the server responded with a status of 404') && text.includes('favicon')
  );
}

function isBadBodyText(text) {
  return /application error|this page could not be found|500 internal server error|unhandled runtime error|hydration failed/i.test(text);
}

function isApiRequestUrl(rawUrl) {
  try {
    return new URL(rawUrl).pathname.startsWith('/api/');
  } catch {
    return false;
  }
}

function sanitizedApiPath(rawUrl) {
  const url = new URL(rawUrl);
  const queryKeys = [...url.searchParams.keys()].sort();
  return `${url.pathname}${queryKeys.length > 0 ? `?${queryKeys.map((key) => `${key}=<redacted>`).join('&')}` : ''}`;
}

function capturePartnerRemnawaveMutationRequest(request) {
  const path = sanitizedApiPath(request.url);
  if (
    request.method.toUpperCase() !== 'PATCH'
    || !path.includes('/remnawave/resources/')
  ) {
    return null;
  }
  const idempotencyKey = Object.entries(request.headers ?? {}).find(
    ([name]) => name.toLowerCase() === 'idempotency-key',
  )?.[1];
  return {
    method: 'PATCH',
    path,
    body: parseFixtureRequestBody(request.postData),
    idempotencyKeyPresent: typeof idempotencyKey === 'string'
      && /^[A-Za-z0-9._:-]{16,160}$/.test(idempotencyKey),
  };
}

function apiStatusBucket(status) {
  if (status >= 500) return '5xx';
  if (status >= 400) return '4xx';
  if (status >= 300) return '3xx';
  if (status >= 200) return '2xx';
  return 'other';
}

function isLoginRedirect(pathname) {
  return /\/login\/?$/.test(pathname || '');
}

async function runBrowserRoutes(routes, liveCookieJar = null) {
  assert(CHROMIUM_BIN, 'Chromium executable was not found. Set CHROMIUM_BIN to run this smoke.');
  assert(!LIVE_API || liveCookieJar, 'Live API route smoke requires an authenticated live cookie jar.');

  const batchSize =
    BROWSER_ROUTE_BATCH_SIZE > 0
      ? Math.max(1, BROWSER_ROUTE_BATCH_SIZE)
      : routes.length;
  if (batchSize < routes.length) {
    const results = [];
    for (let start = 0; start < routes.length; start += batchSize) {
      const batch = routes.slice(start, start + batchSize);
      logVerbose(
        `browser batch ${Math.floor(start / batchSize) + 1}/${Math.ceil(routes.length / batchSize)} covers route ${start + 1}-${start + batch.length}`,
      );
      results.push(...await runBrowserRouteBatch(batch, liveCookieJar, start, routes.length));
      await sleep(500);
    }
    return results;
  }

  return runBrowserRouteBatch(routes, liveCookieJar, 0, routes.length);
}

async function runBrowserRouteBatch(routes, liveCookieJar = null, routeOffset = 0, totalRouteCount = routes.length) {
  const userDataDir = await mkdtemp(join(tmpdir(), `cybervpn-${SURFACE}-route-smoke-`));
  logVerbose(`launching Chromium for ${routes.length} route(s), offset ${routeOffset}`);
  const browserProcess = spawn(CHROMIUM_BIN, [
    '--headless=new',
    '--use-gl=swiftshader',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--remote-debugging-port=0',
    ...(
      buildHostResolverRules()
        ? [`--host-resolver-rules=${buildHostResolverRules()}`]
        : []
    ),
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ], {
    stdio: ['ignore', 'ignore', 'pipe'],
  });

  let socket;
  const results = [];

  try {
    const webSocketUrl = await waitForWebSocketUrl(browserProcess);
    socket = new WebSocket(webSocketUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', reject, { once: true });
    });

    const client = new CdpClient(socket);

    for (const [index, route] of routes.entries()) {
      const { targetId } = await client.send('Target.createTarget', { url: 'about:blank' });
      const { sessionId } = await client.send('Target.attachToTarget', { targetId, flatten: true });
      const requestById = new Map();
      const diagnostics = {
        apiRequests: [],
        apiResponses: [],
        apiFailures: [],
        apiStatusCounts: {},
        partnerRemnawaveMutationRequests: [],
        consoleErrors: [],
        pageErrors: [],
        failedRequests: [],
        serverErrors: [],
        documentStatuses: [],
      };
      const disposers = [
        client.on('Runtime.exceptionThrown', (message) => {
          if (message.sessionId !== sessionId) return;
          const details = message.params.exceptionDetails;
          diagnostics.pageErrors.push(
            details.exception?.description || details.exception?.value || details.text || JSON.stringify(details),
          );
        }),
        client.on('Runtime.consoleAPICalled', (message) => {
          if (message.sessionId !== sessionId || message.params.type !== 'error') return;
          const text = message.params.args.map((arg) => arg.value || arg.description || '').join(' ');
          if (!isBenignConsoleError(text)) {
            diagnostics.consoleErrors.push(text);
          }
        }),
        client.on('Network.loadingFailed', (message) => {
          if (message.sessionId !== sessionId) return;
          const { errorText, canceled, type } = message.params;
          if (!canceled && type !== 'Image') {
            diagnostics.failedRequests.push({ errorText, type });
          }
        }),
        client.on('Network.requestWillBeSent', (message) => {
          if (message.sessionId !== sessionId) return;
          const { requestId, request } = message.params;
          requestById.set(requestId, {
            method: request.method,
            url: request.url,
          });
          if (isApiRequestUrl(request.url)) {
            diagnostics.apiRequests.push({
              method: request.method,
              path: sanitizedApiPath(request.url),
            });
          }
        }),
        client.on('Network.responseReceived', (message) => {
          if (message.sessionId !== sessionId) return;
          const { requestId, response, type } = message.params;
          const trackedRequest = requestById.get(requestId) ?? { method: 'GET', url: response.url };
          if (type === 'Document') {
            diagnostics.documentStatuses.push({
              status: response.status,
              url: response.url,
            });
          }
          if (isApiRequestUrl(response.url)) {
            const apiResponse = {
              method: trackedRequest.method,
              path: sanitizedApiPath(response.url),
              status: response.status,
            };
            diagnostics.apiResponses.push(apiResponse);
            const bucket = apiStatusBucket(response.status);
            diagnostics.apiStatusCounts[bucket] = (diagnostics.apiStatusCounts[bucket] ?? 0) + 1;
            if (LIVE_API && response.status >= 400) {
              diagnostics.apiFailures.push(apiResponse);
            }
          }
          if (response.status >= 500 && !response.url.includes('/_next/')) {
            diagnostics.serverErrors.push({
              status: response.status,
              url: response.url,
            });
          }
        }),
        client.on('Fetch.requestPaused', async (message) => {
          if (message.sessionId !== sessionId) return;
          const { requestId, request } = message.params;

          try {
            const partnerMutationRequest = capturePartnerRemnawaveMutationRequest(request);
            if (partnerMutationRequest) {
              diagnostics.partnerRemnawaveMutationRequests.push(partnerMutationRequest);
            }
            const fixture = fixtureForApiRequest(request.url, request.method, request.postData);
            if (fixture.kind === 'empty') {
              await fulfillNoContent(client, sessionId, requestId);
              return;
            }
            await fulfillJson(client, sessionId, requestId, fixture.data, fixture.status || 200);
          } catch (error) {
            diagnostics.pageErrors.push(error instanceof Error ? error.message : String(error));
            await fulfillJson(client, sessionId, requestId, { detail: 'route_smoke_fixture_error' }, 500);
          }
        }),
      ];
      const startedAt = Date.now();
      const routeNumber = routeOffset + index + 1;
      let interactionEvidence = null;
      logVerbose(`route ${routeNumber}/${totalRouteCount} start ${route.path} (${relative(REPO_ROOT, route.pageFile).replace(/\\/g, '/')})`);
      try {
        await client.send('Page.enable', {}, sessionId);
        await client.send('Runtime.enable', {}, sessionId);
        await client.send('Network.enable', {}, sessionId);
        if (!LIVE_API) {
          await client.send('Fetch.enable', {
            patterns: [{ urlPattern: '*://*/api/*', requestStage: 'Request' }],
          }, sessionId);
          await client.send('Page.addScriptToEvaluateOnNewDocument', {
            source: installBrowserMocksSource(),
          }, sessionId);
        }
        await setAuthCookies(client, sessionId, [...new Set([route.url, BASE_URL, STOREFRONT_BASE_URL])], liveCookieJar);

        const loadEvent = waitForEvent(
          client,
          'Page.loadEventFired',
          (message) => message.sessionId === sessionId,
          NAVIGATION_TIMEOUT_MS,
        ).catch(() => null);

        await client.send('Page.navigate', { url: route.url }, sessionId, NAVIGATION_TIMEOUT_MS).catch((error) => {
          diagnostics.pageErrors.push(
            error instanceof Error ? error.message : String(error),
          );
        });
        await loadEvent;
        await waitForExpression(
          client,
          sessionId,
          'document.readyState === "complete" || document.readyState === "interactive"',
          ASSERTION_TIMEOUT_MS,
          `Route did not become interactive: ${route.url}`,
        ).catch((error) => {
          diagnostics.pageErrors.push(
            error instanceof Error ? error.message : String(error),
          );
        });
        await sleep(ROUTE_SETTLE_MS);
        await waitForExpression(
          client,
          sessionId,
          `
            (document.body?.innerText?.replace(/\\s+/g, ' ').trim().length ?? 0) >= 20
          `,
          Math.min(ASSERTION_TIMEOUT_MS, 5_000),
          `Route body did not render enough text before snapshot: ${route.url}`,
        ).catch(() => undefined);

        if (isPartnerDashboardRoute(route)) {
          try {
            interactionEvidence = await runPartnerRemnawaveDashboardInteractions(
              client,
              sessionId,
              diagnostics,
            );
          } catch (error) {
            diagnostics.pageErrors.push(
              `Partner Remnawave dashboard interaction failed: ${error instanceof Error ? error.message : String(error)}`,
            );
          }
        }

        const snapshot = await evaluate(
          client,
          sessionId,
          `
            JSON.stringify({
              href: location.href,
              pathname: location.pathname,
              title: document.title,
              readyState: document.readyState,
              bodyText: document.body?.innerText?.replace(/\\s+/g, ' ').trim().slice(0, 2400) ?? '',
              bodyTextLength: document.body?.innerText?.replace(/\\s+/g, ' ').trim().length ?? 0,
              h1: Array.from(document.querySelectorAll('h1')).map((item) => item.textContent?.replace(/\\s+/g, ' ').trim()).filter(Boolean).slice(0, 5),
              alerts: Array.from(document.querySelectorAll('[role="alert"]')).map((item) => item.textContent?.replace(/\\s+/g, ' ').trim()).filter(Boolean).slice(0, 5),
              hasRoot: Boolean(document.body),
              menuTriggerCount: document.querySelectorAll('button[aria-haspopup="menu"]').length,
              navLinkCount: document.querySelectorAll('a[href]').length
            })
          `,
        ).then(JSON.parse).catch((error) => {
          diagnostics.pageErrors.push(
            error instanceof Error ? error.message : String(error),
          );
          return {
            href: null,
            pathname: null,
            title: null,
            readyState: null,
            bodyText: '',
            bodyTextLength: 0,
            h1: [],
            alerts: [],
            hasRoot: false,
            menuTriggerCount: 0,
            navLinkCount: 0,
          };
        });

        const failedReasons = [];
        if (snapshot.bodyTextLength < 20) {
          failedReasons.push(`body text too short (${snapshot.bodyTextLength})`);
        }
        if (isBadBodyText(snapshot.bodyText)) {
          failedReasons.push(`body contains route error text: ${snapshot.bodyText.slice(0, 180)}`);
        }
        if (LIVE_API && route.group === 'dashboard' && isLoginRedirect(snapshot.pathname)) {
          failedReasons.push(`live authenticated route redirected to login: ${snapshot.pathname}`);
        }
        if (diagnostics.pageErrors.length > 0) {
          failedReasons.push(`runtime exceptions: ${diagnostics.pageErrors.join(' | ')}`);
        }
        if (diagnostics.consoleErrors.length > 0) {
          failedReasons.push(`console errors: ${diagnostics.consoleErrors.join(' | ')}`);
        }
        if (diagnostics.failedRequests.length > 0) {
          failedReasons.push(`failed requests: ${JSON.stringify(diagnostics.failedRequests.slice(0, 5))}`);
        }
        if (diagnostics.serverErrors.length > 0) {
          failedReasons.push(`5xx responses: ${JSON.stringify(diagnostics.serverErrors.slice(0, 5))}`);
        }
        if (diagnostics.apiFailures.length > 0) {
          failedReasons.push(`live API 4xx/5xx responses: ${JSON.stringify(diagnostics.apiFailures.slice(0, 8))}`);
        }
        if (diagnostics.documentStatuses.some((item) => item.status >= 400)) {
          failedReasons.push(`document status >= 400: ${JSON.stringify(diagnostics.documentStatuses)}`);
        }

        results.push({
          ...route,
          finalUrl: snapshot.href,
          finalPathname: snapshot.pathname,
          durationMs: Date.now() - startedAt,
          title: snapshot.title,
          h1: snapshot.h1,
          bodyTextLength: snapshot.bodyTextLength,
          menuTriggerCount: snapshot.menuTriggerCount,
          navLinkCount: snapshot.navLinkCount,
          apiRequestCount: diagnostics.apiRequests.length,
          apiStatusCounts: diagnostics.apiStatusCounts,
          apiResponses: diagnostics.apiResponses,
          interactionEvidence,
          status: failedReasons.length === 0 ? 'passed' : 'failed',
          failedReasons,
          diagnostics: failedReasons.length > 0 ? diagnostics : undefined,
        });
        logVerbose(`route ${routeNumber}/${totalRouteCount} ${failedReasons.length === 0 ? 'pass' : 'fail'} ${route.path} ${Date.now() - startedAt}ms`);
      } finally {
        for (const dispose of disposers) {
          dispose();
        }
        await client.send('Page.stopLoading', {}, sessionId).catch(() => null);
        await client.send('Target.detachFromTarget', { sessionId }).catch(() => null);
        await client.send('Target.closeTarget', { targetId }).catch(() => null);
      }
    }

    return results;
  } finally {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
    if (!browserProcess.killed) {
      browserProcess.kill('SIGTERM');
    }
    await new Promise((resolve) => {
      browserProcess.once('exit', resolve);
      setTimeout(resolve, 2_000);
    });
    await rm(userDataDir, {
      recursive: true,
      force: true,
      maxRetries: 3,
      retryDelay: 100,
    });
  }
}

function summarizeResults(discovery, routeResults, localeRedirects, liveAuthSummary = null) {
  const failedRoutes = routeResults.filter((route) => route.status !== 'passed');
  const passedRoutes = routeResults.filter((route) => route.status === 'passed');
  const byGroup = {};
  const byTag = {};
  const apiResponses = [];
  for (const route of routeResults) {
    byGroup[route.group] = byGroup[route.group] || { total: 0, passed: 0, failed: 0 };
    byGroup[route.group].total += 1;
    byGroup[route.group][route.status === 'passed' ? 'passed' : 'failed'] += 1;
    for (const tag of route.tags) {
      byTag[tag] = byTag[tag] || { total: 0, passed: 0, failed: 0 };
      byTag[tag].total += 1;
      byTag[tag][route.status === 'passed' ? 'passed' : 'failed'] += 1;
    }
    for (const response of route.apiResponses ?? []) {
      apiResponses.push({
        route: route.path,
        ...response,
      });
    }
  }

  const apiStatusCounts = {};
  for (const response of apiResponses) {
    const bucket = apiStatusBucket(response.status);
    apiStatusCounts[bucket] = (apiStatusCounts[bucket] ?? 0) + 1;
  }
  const expectedApiCoverage = EXPECTED_API_SUBSTRINGS.map((expected) => {
    const matches = apiResponses.filter((response) => response.path.includes(expected));
    return {
      expected,
      status: matches.length > 0 ? 'passed' : 'failed',
      matches: matches.slice(0, 8),
    };
  });
  const missingExpectedApi = expectedApiCoverage.filter((item) => item.status !== 'passed');
  const localeRedirectStatus =
    LIVE_API && ROUTE_FILTERS.length > 0
      ? true
      : localeRedirects.every((item) => item.status === 'passed');
  const partnerRemnawaveDashboardSmoke = routeResults
    .map((route) => route.interactionEvidence)
    .find(Boolean) ?? null;

  return {
    status: failedRoutes.length === 0 && localeRedirectStatus && missingExpectedApi.length === 0 ? 'passed' : 'failed',
    surface: SURFACE,
    locale: LOCALE,
    liveApi: LIVE_API,
    intercepted: !LIVE_API,
    devBypassAuth: !LIVE_API && SURFACE === 'partner',
    baseUrl: BASE_URL,
    connectBaseUrl: CONNECT_BASE_URL,
    authConnectBaseUrl: LIVE_API ? AUTH_CONNECT_BASE_URL : null,
    routeCount: routeResults.length,
    discoveredRouteCount: discovery.discoveredRouteCount,
    passedRouteCount: passedRoutes.length,
    failedRouteCount: failedRoutes.length,
    skipped: discovery.skipped,
    byGroup,
    byTag,
    localeRedirects,
    liveAuth: liveAuthSummary,
    partnerRemnawaveDashboardSmoke,
    expectedApiCoverage,
    missingExpectedApi,
    apiStatusCounts,
    apiResponseCount: apiResponses.length,
    apiResponses: apiResponses.slice(0, 200),
    failedRoutes,
    samplePassedRoutes: passedRoutes.slice(0, 12).map((route) => ({
      path: route.path,
      group: route.group,
      durationMs: route.durationMs,
      apiRequestCount: route.apiRequestCount,
    })),
  };
}

async function runLocaleRedirectChecks() {
  const routes = [
    {
      input: new URL('/login', BASE_URL).toString(),
      expectedPathPattern: /^\/[a-z]{2,3}-[A-Z]{2}\/login\/?$/,
    },
  ];
  if (SURFACE === 'partner') {
    routes.push({
      input: new URL('/checkout', BASE_URL).toString(),
      displayInput: new URL('/checkout', STOREFRONT_BASE_URL).toString(),
      headers: { host: new URL(STOREFRONT_BASE_URL).host },
      expectedPathPattern: /^\/[a-z]{2,3}-[A-Z]{2}\/checkout\/?$/,
    });
  }

  const results = [];
  for (const route of routes) {
    const response = await fetchWithConnectBase(route.input, {
      redirect: 'manual',
      headers: route.headers,
    }).catch((error) => error);
    if (response instanceof Error) {
      results.push({
        input: route.displayInput ?? route.input,
        connectInput: route.displayInput ? route.input : undefined,
        status: 'failed',
        reason: response.message,
      });
      continue;
    }
    const location = response.headers.get('location');
    const status = response.status;
    const resolved = location ? new URL(location, route.input) : new URL(route.input);
    const pathHasLocale = LOCALE_PATH_PATTERN.test(resolved.pathname);
    results.push({
      input: route.displayInput ?? route.input,
      connectInput: route.displayInput ? route.input : undefined,
      status: status >= 300 && status < 400 && pathHasLocale && route.expectedPathPattern.test(resolved.pathname) ? 'passed' : 'failed',
      httpStatus: status,
      location,
      expectedPathPattern: String(route.expectedPathPattern),
    });
  }
  return results;
}

async function main() {
  const devServer = await startDevServer();
  try {
    const discovery = await discoverRoutes();
    assert(discovery.routes.length > 0, 'No routes selected for browser smoke.');
    const liveAuth = LIVE_API ? await authenticateLiveSession() : null;
    const routeResults = await runBrowserRoutes(discovery.routes, liveAuth?.jar ?? null);
    const localeRedirects = LIVE_API && ROUTE_FILTERS.length > 0 ? [] : await runLocaleRedirectChecks();
    const summary = summarizeResults(discovery, routeResults, localeRedirects, liveAuth?.summary ?? null);

    if (OUTPUT_PATH) {
      const outputPath = join(REPO_ROOT, OUTPUT_PATH);
      await mkdir(dirname(outputPath), { recursive: true });
      await writeFile(outputPath, `${JSON.stringify({ summary, routes: routeResults }, null, 2)}\n`, 'utf8');
    }

    process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);

    if (summary.status !== 'passed') {
      process.exitCode = 1;
    }
  } finally {
    await devServer?.stop();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
