import http from 'node:http';
import https from 'node:https';

const SURFACE_CONFIGS = {
  frontend: {
    defaultBaseUrl: 'http://127.0.0.1:9001',
    expectedCookies: ['customer_access_token', 'customer_refresh_token'],
    expectedRealm: 'customer',
    expectedPrincipalType: 'customer',
    expectedScopeFamily: 'customer',
    optionalSessionPath: '/api/auth/optional-session',
  },
  admin: {
    defaultBaseUrl: 'http://127.0.0.1:13001',
    expectedCookies: ['access_token', 'refresh_token'],
    expectedRealm: 'admin',
    expectedPrincipalType: 'admin',
    expectedScopeFamily: 'admin',
  },
  partner: {
    defaultBaseUrl: 'http://portal.localhost:3002',
    expectedCookies: ['partner_access_token', 'partner_refresh_token'],
    expectedRealm: 'partner',
    expectedPrincipalType: 'partner_operator',
    expectedScopeFamily: 'partner',
  },
};
const SET_COOKIE_BOUNDARY_NAMES = [
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

const SURFACE = readCliOption('surface') || process.env.AUTH_BFF_SMOKE_SURFACE || 'frontend';
const SURFACE_CONFIG = SURFACE_CONFIGS[SURFACE];

assert(
  SURFACE_CONFIG,
  `Unknown BFF cookie smoke surface "${SURFACE}". Expected one of: ${Object.keys(SURFACE_CONFIGS).join(', ')}.`,
);

const BASE_URL = normalizeBaseUrl(
  readCliOption('base-url')
    || process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_BASE_URL`]
    || process.env.AUTH_BFF_SMOKE_BASE_URL
    || SURFACE_CONFIG.defaultBaseUrl,
);
const CONNECT_BASE_URL = normalizeBaseUrl(
  readCliOption('connect-base-url')
    || process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_CONNECT_BASE_URL`]
    || process.env.AUTH_BFF_SMOKE_CONNECT_BASE_URL
    || BASE_URL,
);
const HOST_HEADER =
  readCliOption('host-header')
  || process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_HOST_HEADER`]
  || process.env.AUTH_BFF_SMOKE_HOST_HEADER
  || (CONNECT_BASE_URL !== BASE_URL ? new URL(BASE_URL).host : null);
const IDENTIFIER =
  readCliOption('identifier')
  || process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_IDENTIFIER`]
  || process.env.AUTH_BFF_SMOKE_IDENTIFIER;
const PASSWORD =
  readCliOption('password')
  || process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_PASSWORD`]
  || process.env.AUTH_BFF_SMOKE_PASSWORD;
const TOTP_CODE =
  readCliOption('totp-code')
  || process.env[`AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_TOTP_CODE`]
  || process.env.AUTH_BFF_SMOKE_TOTP_CODE;
const EXPECT_REALM = readCliOption('expect-realm') || SURFACE_CONFIG.expectedRealm;
const EXPECT_PRINCIPAL_TYPE =
  readCliOption('expect-principal-type') || SURFACE_CONFIG.expectedPrincipalType;
const EXPECT_SCOPE_FAMILY =
  readCliOption('expect-scope-family') || SURFACE_CONFIG.expectedScopeFamily;
const SKIP_LOGOUT = booleanFromEnv('AUTH_BFF_SMOKE_SKIP_LOGOUT', false) || hasCliFlag('skip-logout');
const ALLOW_NON_LOCAL = booleanFromEnv('AUTH_BFF_SMOKE_ALLOW_NON_LOCAL', false) || hasCliFlag('allow-non-local');
const TIMEOUT_MS = numberFromEnv('AUTH_BFF_SMOKE_TIMEOUT_MS', 15_000);

class CookieJar {
  constructor(baseUrl = BASE_URL) {
    this.baseUrl = new URL(baseUrl);
    this.host = this.baseUrl.hostname.toLowerCase();
    this.isHttps = this.baseUrl.protocol === 'https:';
    this.cookies = new Map();
    this.history = [];
  }

  apply(setCookieHeaders, requestPath = '/') {
    for (const header of setCookieHeaders) {
      const parsed = parseSetCookie(header, requestPath);
      if (!parsed) continue;
      if (parsed.hostOnly) {
        parsed.domain = this.host;
      }

      const rejectionReason = this.getRejectionReason(parsed);
      if (rejectionReason) {
        this.history.push(this.historyEntry(parsed, 'rejected', rejectionReason));
        continue;
      }

      const key = this.keyFor(parsed);
      const maxAge = parsed.attributes.get('max-age');
      if (maxAge === '0') {
        this.cookies.delete(key);
        this.history.push(this.historyEntry(parsed, 'deleted'));
      } else {
        this.cookies.set(key, parsed);
        this.history.push(this.historyEntry(parsed, 'stored'));
      }
    }
  }

  keyFor(cookie) {
    return `${cookie.name};${cookie.hostOnly ? 'host' : 'domain'}=${cookie.domain ?? this.host};${cookie.path}`;
  }

  header(requestPath = '/') {
    return [...this.cookies.values()]
      .filter((cookie) => (
        pathMatches(requestPath, cookie.path)
        && this.domainMatches(cookie)
        && (!cookie.secure || this.isHttps)
      ))
      .sort((left, right) => right.path.length - left.path.length)
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join('; ');
  }

  has(name, requestPath = '/') {
    return [...this.cookies.values()].some((cookie) => (
      cookie.name === name
      && pathMatches(requestPath, cookie.path)
      && this.domainMatches(cookie)
      && (!cookie.secure || this.isHttps)
    ));
  }

  activeNames() {
    return [...this.cookies.values()].map((cookie) => cookie.name).sort();
  }

  getRejectionReason(cookie) {
    if (cookie.secure && !this.isHttps) {
      return 'secure-cookie-on-http-origin';
    }

    if (!this.domainMatches(cookie)) {
      return 'domain-mismatch';
    }

    return null;
  }

  domainMatches(cookie) {
    if (cookie.hostOnly) {
      return cookie.domain === this.host;
    }

    return this.host === cookie.domain || this.host.endsWith(`.${cookie.domain}`);
  }

  historyEntry(cookie, action, rejectionReason = null) {
    const entry = {
      action,
      attributes: Object.fromEntries(cookie.attributes.entries()),
      domain: cookie.hostOnly ? '<host-only>' : cookie.domain,
      name: cookie.name,
      path: cookie.path,
    };

    if (rejectionReason) {
      entry.rejectionReason = rejectionReason;
    }

    return entry;
  }
}

if (hasCliFlag('self-test')) {
  runSelfTest();
  process.exit(0);
}

assert(IDENTIFIER, 'Set AUTH_BFF_SMOKE_IDENTIFIER or a surface-specific identifier env var before running this smoke.');
assert(PASSWORD, 'Set AUTH_BFF_SMOKE_PASSWORD or a surface-specific password env var before running this smoke.');
assertLocalUrl(BASE_URL, ALLOW_NON_LOCAL);
assertLocalUrl(CONNECT_BASE_URL, ALLOW_NON_LOCAL);

async function main() {
  const jar = new CookieJar();

  const healthProbe = await fetchWithTimeout(urlFor('/api/v1/auth/session'), {
    headers: buildBaseHeaders({ accept: 'application/json' }),
    method: 'GET',
  }).catch((error) => {
    throw new Error(`BFF route is not reachable at ${CONNECT_BASE_URL}: ${error.message}`);
  });
  await healthProbe.arrayBuffer().catch(() => null);

  const loginResponse = await jsonRequest('/api/v1/auth/login', {
    body: {
      login_or_email: IDENTIFIER,
      password: PASSWORD,
    },
    jar,
    method: 'POST',
  });
  assert(loginResponse.status === 200, `Expected login status 200, got ${loginResponse.status}: ${formatPayload(loginResponse.payload)}`);
  assertNoTokenFields(loginResponse.payload, 'login response');
  let twoFactorPendingResponse = null;
  let twoFactorCompleteResponse = null;

  if (loginResponse.payload?.requires_2fa === true) {
    assertTwoFactorChallengePayload(loginResponse.payload, 'login response');
    for (const cookie of SURFACE_CONFIG.expectedCookies) {
      assert(
        !jar.has(cookie, '/api/v1/auth/session'),
        `Expected 2FA challenge not to set ${cookie} before verification.`,
      );
    }
    assert(TOTP_CODE, `Set AUTH_BFF_SMOKE_${SURFACE.toUpperCase()}_TOTP_CODE or AUTH_BFF_SMOKE_TOTP_CODE for a 2FA-enabled account.`);

    twoFactorPendingResponse = await jsonRequest('/api/auth/2fa/pending', {
      body: {
        token: loginResponse.payload.tfa_token,
        locale: 'en-EN',
        return_to: '/en-EN/dashboard',
        is_new_user: false,
      },
      jar,
      method: 'POST',
    });
    assert(
      twoFactorPendingResponse.status === 204,
      `Expected 2FA pending status 204, got ${twoFactorPendingResponse.status}: ${formatPayload(twoFactorPendingResponse.payload)}`,
    );

    twoFactorCompleteResponse = await jsonRequest('/api/auth/2fa/complete', {
      body: {
        code: TOTP_CODE,
      },
      jar,
      method: 'POST',
    });
    assert(
      twoFactorCompleteResponse.status === 200,
      `Expected 2FA complete status 200, got ${twoFactorCompleteResponse.status}: ${formatPayload(twoFactorCompleteResponse.payload)}`,
    );
    assertNoTokenFields(twoFactorCompleteResponse.payload, '2FA complete response');
  } else {
    assertNoTwoFactorChallengeToken(loginResponse.payload, 'login response');
    assertRealmPayload(loginResponse.payload, 'login response');
  }

  for (const cookie of SURFACE_CONFIG.expectedCookies) {
    assert(
      jar.has(cookie, '/api/v1/auth/session'),
      `Expected authenticated flow to set ${cookie}; active cookies: ${jar.activeNames().join(', ') || '<none>'}.`,
    );
  }

  const sessionResponse = await jsonRequest('/api/v1/auth/session', {
    jar,
    method: 'GET',
  });
  assert(
    sessionResponse.status === 200,
    `Expected session status 200 after login, got ${sessionResponse.status}: ${formatPayload(sessionResponse.payload)}`,
  );
  assertNoTokenFields(sessionResponse.payload, 'session response');
  assertRealmPayload(sessionResponse.payload, 'session response');

  let optionalSessionResponse = null;
  if (SURFACE_CONFIG.optionalSessionPath) {
    optionalSessionResponse = await jsonRequest(SURFACE_CONFIG.optionalSessionPath, {
      jar,
      method: 'GET',
    });
    assert(
      optionalSessionResponse.status === 200,
      `Expected optional-session status 200, got ${optionalSessionResponse.status}: ${formatPayload(optionalSessionResponse.payload)}`,
    );
    assertNoTokenFields(optionalSessionResponse.payload, 'optional-session response');
    assert(optionalSessionResponse.payload !== null, 'Expected optional-session to return the logged-in session payload.');
    assertRealmPayload(optionalSessionResponse.payload, 'optional-session response');
  }

  let logoutResponse = null;
  let sessionAfterLogoutResponse = null;
  if (!SKIP_LOGOUT) {
    logoutResponse = await jsonRequest('/api/v1/auth/logout', {
      body: {},
      jar,
      method: 'POST',
    });
    assert(
      [200, 204].includes(logoutResponse.status),
      `Expected logout status 200 or 204, got ${logoutResponse.status}: ${formatPayload(logoutResponse.payload)}`,
    );

    sessionAfterLogoutResponse = await jsonRequest('/api/v1/auth/session', {
      jar,
      method: 'GET',
    });
    assert(
      sessionAfterLogoutResponse.status === 401 || sessionAfterLogoutResponse.status === 403,
      `Expected session after logout to be 401/403, got ${sessionAfterLogoutResponse.status}: ${formatPayload(sessionAfterLogoutResponse.payload)}`,
    );
  }

  process.stdout.write(`${JSON.stringify({
    status: 'passed',
    surface: SURFACE,
    baseUrl: BASE_URL,
    login: summarizeResponse(loginResponse),
    twoFactorPending: twoFactorPendingResponse ? summarizeResponse(twoFactorPendingResponse) : null,
    twoFactorComplete: twoFactorCompleteResponse ? summarizeResponse(twoFactorCompleteResponse) : null,
    session: summarizeResponse(sessionResponse),
    optionalSession: optionalSessionResponse ? summarizeResponse(optionalSessionResponse) : null,
    logout: logoutResponse ? summarizeResponse(logoutResponse) : null,
    sessionAfterLogout: sessionAfterLogoutResponse ? summarizeResponse(sessionAfterLogoutResponse) : null,
    observedSetCookies: jar.history,
    activeCookieNames: jar.activeNames(),
    intercepted: false,
    devBypassAuth: false,
  }, null, 2)}\n`);
}

async function jsonRequest(path, { body, jar, method }) {
  const headers = buildBaseHeaders({
    accept: 'application/json',
    origin: BASE_URL,
    referer: `${BASE_URL}/en-EN/dashboard`,
  });

  if (body !== undefined) {
    headers['content-type'] = 'application/json';
  }

  const cookieHeader = jar.header(path);
  if (cookieHeader) {
    headers.cookie = cookieHeader;
  }

  const response = await fetchWithTimeout(urlFor(path), {
    body: body === undefined ? undefined : JSON.stringify(body),
    headers,
    method,
    redirect: 'manual',
  });

  const setCookies = getSetCookieHeaders(response);
  jar.apply(setCookies, path);

  const text = await response.text();
  return {
    headers: {
      setCookie: setCookies.map(redactSetCookie),
    },
    payload: parseJsonOrText(text),
    status: response.status,
  };
}

async function fetchWithTimeout(url, init) {
  if (HOST_HEADER) {
    return nodeHttpRequest(url, init);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    return await fetch(url, {
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
    if (body !== undefined && !hasHeader(headers, 'content-length')) {
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

    request.setTimeout(TIMEOUT_MS, () => {
      request.destroy(new Error(`Timed out after ${TIMEOUT_MS}ms`));
    });
    request.on('error', reject);
    if (body !== undefined) {
      request.write(body);
    }
    request.end();
  });
}

function buildBaseHeaders(headers) {
  if (!HOST_HEADER) {
    return headers;
  }

  return {
    ...headers,
    host: HOST_HEADER,
  };
}

function hasHeader(headers, name) {
  const normalizedName = name.toLowerCase();
  return Object.keys(headers).some((key) => key.toLowerCase() === normalizedName);
}

function assertRealmPayload(payload, label) {
  if (!payload || typeof payload !== 'object') {
    throw new Error(`Expected ${label} to be an object, got ${formatPayload(payload)}.`);
  }

  assert(
    payload.auth_realm_key === EXPECT_REALM,
    `Expected ${label} auth_realm_key=${EXPECT_REALM}, got ${String(payload.auth_realm_key)}.`,
  );
  assert(
    payload.principal_type === EXPECT_PRINCIPAL_TYPE,
    `Expected ${label} principal_type=${EXPECT_PRINCIPAL_TYPE}, got ${String(payload.principal_type)}.`,
  );
  assert(
    payload.scope_family === EXPECT_SCOPE_FAMILY,
    `Expected ${label} scope_family=${EXPECT_SCOPE_FAMILY}, got ${String(payload.scope_family)}.`,
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

function assertNoTwoFactorChallengeToken(payload, label) {
  if (!payload || typeof payload !== 'object') {
    return;
  }

  assert(payload.requires_2fa === false, `Expected ${label} to complete without a 2FA challenge.`);
  assert(
    payload.tfa_token === null || payload.tfa_token === undefined,
    `Expected ${label} to omit tfa_token when 2FA is not required.`,
  );
}

function assertTwoFactorChallengePayload(payload, label) {
  if (!payload || typeof payload !== 'object') {
    throw new Error(`Expected ${label} to be a 2FA challenge object, got ${formatPayload(payload)}.`);
  }

  assert(payload.requires_2fa === true, `Expected ${label} to require 2FA.`);
  assert(
    typeof payload.tfa_token === 'string' && payload.tfa_token.length > 0,
    `Expected ${label} to include a pending 2FA token for the browser staging endpoint.`,
  );
}

function getSetCookieHeaders(response) {
  if (typeof response.headers.getSetCookie === 'function') {
    return response.headers.getSetCookie().flatMap(splitSetCookieHeader);
  }

  const setCookie = response.headers.get('set-cookie');
  if (!setCookie) return [];

  return splitSetCookieHeader(setCookie);
}

function splitSetCookieHeader(headerValue) {
  const cookies = [];
  let start = 0;

  for (let index = 0; index < headerValue.length; index += 1) {
    if (headerValue[index] !== ',') continue;

    const candidate = headerValue.slice(index + 1).trimStart();
    if (!SET_COOKIE_BOUNDARY_NAMES.some((name) => candidate.startsWith(`${name}=`))) {
      continue;
    }

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

  const domain = normalizeCookieDomain(attributes.get('domain') ?? null);

  return {
    attributes,
    domain,
    hostOnly: !attributes.has('domain'),
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

function parseJsonOrText(text) {
  if (!text) return null;

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function summarizeResponse(response) {
  return {
    status: response.status,
    payload: summarizePayload(response.payload),
    setCookie: response.headers.setCookie,
  };
}

function summarizePayload(payload) {
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
    summary.detail = summarizeDetail(payload.detail);
  }

  return summary;
}

function summarizeDetail(detail) {
  if (typeof detail === 'string') {
    return detail;
  }

  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) {
    return '<redacted>';
  }

  const safe = {};
  for (const key of ['code', 'message']) {
    if (typeof detail[key] === 'string') {
      safe[key] = detail[key];
    }
  }
  return Object.keys(safe).length > 0 ? safe : '<redacted>';
}

function sanitizePayload(payload) {
  if (Array.isArray(payload)) {
    return payload.map(sanitizePayload);
  }

  if (!payload || typeof payload !== 'object') {
    return payload;
  }

  return Object.fromEntries(
    Object.entries(payload).map(([key, value]) => {
      if (key.toLowerCase().includes('token') || key.toLowerCase().includes('password')) {
        return [key, value === null || value === undefined ? value : '<redacted>'];
      }
      return [key, sanitizePayload(value)];
    }),
  );
}

function redactSetCookie(header) {
  const parsed = parseSetCookie(header);
  if (!parsed) return '<unparseable-set-cookie>';

  const attributes = [...parsed.attributes.entries()].map(([key, value]) => (
    value === true ? key : `${key}=${value}`
  ));
  return `${parsed.name}=<redacted>; ${attributes.join('; ')}`;
}

function runSelfTest() {
  const jar = new CookieJar('http://app.localhost:3000');
  jar.apply([
    'access_token=secure-token; Secure; Path=/api; HttpOnly',
    'refresh_token=wrong-domain; Domain=.cyber-vpn.net; Path=/api; HttpOnly',
  ], '/api/v1/auth/login');

  assert(!jar.has('access_token', '/api/v1/auth/session'), 'Expected Secure cookie to be rejected on an HTTP smoke origin.');
  assert(!jar.has('refresh_token', '/api/v1/auth/session'), 'Expected incompatible Domain cookie to be rejected.');

  jar.apply([
    'access_token=accepted; Path=/api; HttpOnly',
    'refresh_token=accepted; Domain=app.localhost; Path=/api; HttpOnly',
  ], '/api/v1/auth/login');
  assert(jar.has('access_token', '/api/v1/auth/session'), 'Expected host-only cookie to be accepted for the smoke origin.');
  assert(jar.has('refresh_token', '/api/v1/auth/session'), 'Expected matching Domain cookie to be accepted for the smoke origin.');

  const summary = summarizeResponse({
    headers: { setCookie: [] },
    payload: {
      auth_realm_key: 'partner',
      audience: 'cybervpn:partner',
      created_at: '2026-07-04T00:00:00Z',
      current_sign_in_ip: '127.0.0.1',
      email: 'partner@example.test',
      id: 'b62f4c1e-6610-480b-8a4a-5120fdda1417',
      login: 'partner_login',
      principal_type: 'partner_operator',
      requires_2fa: false,
      scope_family: 'partner',
      sign_in_count: 7,
      tfa_token: null,
    },
    status: 200,
  });
  const output = JSON.stringify(summary);
  const formattedFailure = formatPayload({
    created_at: '2026-07-04T00:00:00Z',
    current_sign_in_ip: '127.0.0.1',
    email: 'partner@example.test',
    id: 'b62f4c1e-6610-480b-8a4a-5120fdda1417',
    login: 'partner_login',
    sign_in_count: 7,
  });

  for (const forbidden of [
    'partner@example.test',
    'partner_login',
    '127.0.0.1',
    'b62f4c1e-6610-480b-8a4a-5120fdda1417',
    'sign_in_count',
    'created_at',
    'tfa_token',
  ]) {
    assert(!output.includes(forbidden), `Expected self-test summary to omit ${forbidden}.`);
    assert(!formattedFailure.includes(forbidden), `Expected self-test failure formatting to omit ${forbidden}.`);
  }

  process.stdout.write(`${JSON.stringify({
    status: 'passed',
    checks: [
      'secure-cookie-rejected-on-http',
      'domain-mismatch-cookie-rejected',
      'auth-summary-omits-session-pii',
      'failure-format-omits-session-pii',
    ],
    observedCookies: jar.history,
    summary,
  }, null, 2)}\n`);
}

function normalizeBaseUrl(value) {
  const url = new URL(value);
  url.pathname = '';
  url.search = '';
  url.hash = '';
  return url.toString().replace(/\/$/, '');
}

function urlFor(path) {
  return `${CONNECT_BASE_URL}${path}`;
}

function assertLocalUrl(value, allowNonLocal) {
  if (allowNonLocal) return;

  const url = new URL(value);
  const host = url.hostname.toLowerCase();
  const isLocal =
    host === 'localhost'
    || host === '127.0.0.1'
    || host === '::1'
    || host.endsWith('.localhost');

  assert(
    isLocal,
    `Refusing to run BFF cookie smoke against non-local URL ${value}. Set AUTH_BFF_SMOKE_ALLOW_NON_LOCAL=1 only for an explicitly approved environment.`,
  );
}

function formatPayload(payload) {
  return JSON.stringify(summarizePayload(payload));
}

function readCliOption(name) {
  const prefix = `--${name}=`;
  const exact = `--${name}`;
  const index = process.argv.findIndex((arg) => arg === exact || arg.startsWith(prefix));
  if (index === -1) {
    return null;
  }

  const arg = process.argv[index];
  if (arg.startsWith(prefix)) {
    return arg.slice(prefix.length);
  }

  return process.argv[index + 1] ?? null;
}

function hasCliFlag(name) {
  return process.argv.includes(`--${name}`);
}

function numberFromEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }

  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function booleanFromEnv(name, fallback) {
  const raw = process.env[name]?.trim().toLowerCase();
  if (!raw) {
    return fallback;
  }

  return raw === '1' || raw === 'true' || raw === 'yes';
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.stack || error.message : String(error)}\n`);
  process.exit(1);
});
