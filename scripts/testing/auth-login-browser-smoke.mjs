import { existsSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import http from 'node:http';
import https from 'node:https';

const SURFACE_CONFIGS = {
	  frontend: {
	    defaultUrl: 'http://localhost:9001/en-EN/login',
	    expectConditionalPasskey: true,
	    userMenuNavigationPath: '/settings/security',
	    postLoginNavigationBudgetMs: 2000,
    sessionResponseDelayMs: 2500,
    sessionUser: {
      id: 'synthetic-customer',
      email: 'neo@example.com',
      login: 'neo',
      is_active: true,
      is_email_verified: true,
      role: 'viewer',
      created_at: '2026-06-03T00:00:00.000Z',
    },
  },
	  admin: {
	    defaultUrl: 'http://localhost:3001/en-EN/login',
	    expectConditionalPasskey: false,
	    userMenuNavigationPath: '/security/sessions',
	    postLoginNavigationBudgetMs: 2000,
    sessionResponseDelayMs: 0,
    sessionUser: {
      id: 'synthetic-admin',
      email: 'admin@example.com',
      login: 'admin',
      is_active: true,
      is_email_verified: true,
      role: 'admin',
      created_at: '2026-06-03T00:00:00.000Z',
    },
  },
	  partner: {
	    defaultUrl: 'http://localhost:3002/en-EN/login',
	    expectConditionalPasskey: false,
	    userMenuNavigationPath: '/settings',
	    postLoginNavigationBudgetMs: 2000,
    sessionResponseDelayMs: 0,
    sessionUser: {
      id: 'synthetic-partner',
      email: 'partner@example.com',
      login: 'partner',
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

const SURFACE = readCliOption('surface') || process.env.AUTH_LOGIN_SMOKE_SURFACE || 'frontend';
const SURFACE_CONFIG = SURFACE_CONFIGS[SURFACE];

assert(SURFACE_CONFIG, `Unknown smoke surface "${SURFACE}". Expected one of: ${Object.keys(SURFACE_CONFIGS).join(', ')}.`);

const SURFACE_URL_ENV = `AUTH_LOGIN_SMOKE_${SURFACE.toUpperCase()}_URL`;
const SMOKE_URL =
  readCliOption('url') ||
  process.env[SURFACE_URL_ENV] ||
  process.env.AUTH_LOGIN_SMOKE_URL ||
  (SURFACE === 'frontend' ? process.env.FRONTEND_LOGIN_SMOKE_URL : null) ||
  SURFACE_CONFIG.defaultUrl;
const LIVE_API = readCliOption('live-api') !== null || booleanFromEnv('AUTH_LOGIN_SMOKE_LIVE_API', false);
const CONNECT_BASE_URL = trimTrailingSlash(
  readCliOption('connect-base-url') ||
    process.env[`AUTH_LOGIN_SMOKE_${SURFACE.toUpperCase()}_CONNECT_BASE_URL`] ||
    process.env.AUTH_LOGIN_SMOKE_CONNECT_BASE_URL ||
    new URL(SMOKE_URL).origin,
);
const HOST_HEADER =
  readCliOption('host-header') ||
  process.env[`AUTH_LOGIN_SMOKE_${SURFACE.toUpperCase()}_HOST_HEADER`] ||
  process.env.AUTH_LOGIN_SMOKE_HOST_HEADER ||
  (CONNECT_BASE_URL !== new URL(SMOKE_URL).origin ? new URL(SMOKE_URL).host : null);
const EXPECT_UNREACHABLE_URL =
  readCliOption('expect-unreachable-url') ||
  process.env.AUTH_LOGIN_SMOKE_EXPECT_UNREACHABLE_URL ||
  null;
const CHROMIUM_BIN = process.env.CHROMIUM_BIN || findChromium();
const NAVIGATION_TIMEOUT_MS = numberFromEnv('AUTH_LOGIN_SMOKE_NAVIGATION_TIMEOUT_MS', 60_000);
const ASSERTION_TIMEOUT_MS = numberFromEnv('AUTH_LOGIN_SMOKE_ASSERTION_TIMEOUT_MS', 10_000);
const SESSION_RESPONSE_DELAY_MS = numberFromEnv(
  'AUTH_LOGIN_SMOKE_SESSION_RESPONSE_DELAY_MS',
  SURFACE_CONFIG.sessionResponseDelayMs,
);
const POST_LOGIN_NAVIGATION_BUDGET_MS = numberFromEnv(
  'AUTH_LOGIN_SMOKE_POST_LOGIN_BUDGET_MS',
  SURFACE_CONFIG.postLoginNavigationBudgetMs,
);
const EXPECT_CONDITIONAL_PASSKEY = booleanFromEnv(
  'AUTH_LOGIN_SMOKE_EXPECT_CONDITIONAL_PASSKEY',
  SURFACE_CONFIG.expectConditionalPasskey,
);
const EXPECT_PASSKEY_LOGIN_UI = booleanFromEnv(
  'AUTH_LOGIN_SMOKE_EXPECT_PASSKEY_LOGIN_UI',
  !LIVE_API || EXPECT_CONDITIONAL_PASSKEY,
);
const DASHBOARD_PATH = new URL(SMOKE_URL).pathname.replace(/\/login\/?$/, '/dashboard');
const DASHBOARD_URL = new URL(DASHBOARD_PATH, SMOKE_URL).toString();
const LOGIN_PATH = new URL(SMOKE_URL).pathname;
const LOCALE_PREFIX = LOGIN_PATH.match(/^\/([a-z]{2,3}-[A-Z]{2})(?:\/|$)/)?.[0].replace(/\/$/, '') ?? '';
const USER_MENU_NAVIGATION_PATH = `${LOCALE_PREFIX}${SURFACE_CONFIG.userMenuNavigationPath}`;
const LOGIN_IDENTIFIER = process.env.AUTH_LOGIN_SMOKE_IDENTIFIER || 'neo@example.com';
const LOGIN_PASSWORD = process.env.AUTH_LOGIN_SMOKE_PASSWORD || 'Password123!';

const PASSKEY_POLICY = {
  enabled: true,
  surface: SURFACE,
  realm_key: SURFACE === 'partner' ? 'partner' : SURFACE === 'admin' ? 'admin' : 'customer',
  rp_id: 'localhost',
  rp_name: 'CyberVPN',
  allowedOrigins: [new URL(SMOKE_URL).origin],
  userVerification: 'required',
  conditionalUiEnabled: true,
  registrationEnabled: true,
  authenticationEnabled: true,
  reauthenticationEnabled: true,
  adminCountsAsMfa: false,
  challengeTtlSeconds: 120,
  browserTimeoutMs: 60_000,
};

const LOGIN_RESPONSE = {
  access_token: 'cookie-managed',
  refresh_token: 'cookie-managed',
  token_type: 'bearer',
  expires_in: 3600,
  requires_2fa: false,
  tfa_token: null,
};

const PROFILE_RESPONSE = {
  id: SURFACE_CONFIG.sessionUser.id,
  email: SURFACE_CONFIG.sessionUser.email,
  login: SURFACE_CONFIG.sessionUser.login,
  display_name: 'Smoke Operator',
  avatar_url: null,
  language: 'en-EN',
  timezone: 'UTC',
  public_uid: 14677650,
  created_at: '2026-06-03T00:00:00.000Z',
  updated_at: '2026-06-03T00:00:00.000Z',
};

const LOGOUT_RESPONSE = {
  message: 'Signed out',
};

const PASSKEY_AUTHENTICATION_OPTIONS = {
  challengeId: 'conditional-challenge',
  expiresAt: '2026-06-03T00:02:00.000Z',
  publicKey: {
    challenge: 'Y3liZXJ2cG4tc21va2UtY2hhbGxlbmdl',
    rpId: 'localhost',
    allowCredentials: [],
    timeout: 60_000,
    userVerification: 'required',
  },
};

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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function trimTrailingSlash(value) {
  return value.replace(/\/$/, '');
}

function encodeJsonBody(data) {
  return Buffer.from(JSON.stringify(data)).toString('base64');
}

function parseJsonRequestBody(body) {
  try {
    return JSON.parse(body);
  } catch (error) {
    throw new Error(`Expected JSON request body, got ${JSON.stringify(body)}: ${error.message}`);
  }
}

async function readRequestPostData(client, sessionId, message) {
  const { networkId, request } = message.params;

  if (typeof request.postData === 'string') {
    return request.postData;
  }

  if (!request.hasPostData || !networkId) {
    return null;
  }

  const { base64Encoded, postData } = await client.send(
    'Network.getRequestPostData',
    { requestId: networkId },
    sessionId,
  );

  return base64Encoded
    ? Buffer.from(postData, 'base64').toString('utf8')
    : postData;
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function redactLoginRequest(request) {
  if (!request.body || typeof request.body !== 'object') {
    return request;
  }

  return {
    ...request,
    body: {
      ...request.body,
      password: request.body.password ? '<redacted>' : request.body.password,
    },
  };
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
  }

  send(method, params = {}, sessionId) {
    const id = this.nextId;
    this.nextId += 1;

    const payload = { id, method, params };
    if (sessionId) {
      payload.sessionId = sessionId;
    }

    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
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

async function waitForWebSocketUrl(process) {
  let stderr = '';

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`Timed out waiting for Chromium DevTools endpoint. Stderr:\n${stderr}`));
    }, 15_000);

    process.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
      const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) {
        clearTimeout(timer);
        resolve(match[1]);
      }
    });

    process.once('exit', (code) => {
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

async function waitForExpression(client, sessionId, expression, timeoutMs, message) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const result = await client.send(
      'Runtime.evaluate',
      {
        expression,
        awaitPromise: true,
        returnByValue: true,
      },
      sessionId,
    );

    if (result.result?.value) {
      return result.result.value;
    }

    await sleep(100);
  }

  throw new Error(message);
}

async function evaluate(client, sessionId, expression) {
  const result = await client.send(
    'Runtime.evaluate',
    {
      expression,
      awaitPromise: true,
      returnByValue: true,
    },
    sessionId,
  );

  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || 'Runtime evaluation failed');
  }

  return result.result?.value;
}

async function collectUserMenuDiagnostics(client, sessionId) {
  return evaluate(
    client,
    sessionId,
    `
      JSON.stringify({
        location: location.href,
        pathname: location.pathname,
        readyState: document.readyState,
        trigger: document.querySelector('button[aria-haspopup="menu"]')?.outerHTML?.slice(0, 500) ?? null,
        menuPresent: Boolean(document.querySelector('[role="menu"]')),
        menuText: document.querySelector('[role="menu"]')?.textContent?.replace(/\\s+/g, ' ').trim() ?? null,
        links: Array.from(document.querySelectorAll('[role="menu"] a[href]')).map((link) => ({
          href: link.href,
          pathname: new URL(link.href).pathname,
          text: link.textContent?.replace(/\\s+/g, ' ').trim() ?? '',
          role: link.getAttribute('role'),
          ariaCurrent: link.getAttribute('aria-current'),
        })),
        buttons: Array.from(document.querySelectorAll('button')).map((button) => ({
          text: button.textContent?.replace(/\\s+/g, ' ').trim() ?? '',
          ariaHaspopup: button.getAttribute('aria-haspopup'),
          ariaExpanded: button.getAttribute('aria-expanded'),
          disabled: button.disabled,
        })),
        activeElement: document.activeElement?.outerHTML?.slice(0, 500) ?? null,
        bodyText: document.body?.innerText?.slice(0, 1200) ?? null,
      }, null, 2)
    `,
  );
}

async function fulfillJson(client, sessionId, requestId, data, headers = []) {
  await client.send('Fetch.fulfillRequest', {
    requestId,
    responseCode: 200,
    responseHeaders: [
      { name: 'content-type', value: 'application/json' },
      ...headers,
    ],
    body: encodeJsonBody(data),
  }, sessionId);
}

async function fetchWithConnectBase(displayUrl, init = {}) {
  const display = new URL(displayUrl);
  const target = new URL(`${display.pathname}${display.search}`, CONNECT_BASE_URL);
  const headers = { ...(init.headers ?? {}) };
  if (HOST_HEADER && !Object.keys(headers).some((key) => key.toLowerCase() === 'host')) {
    headers.host = HOST_HEADER;
  }
  return nodeHttpRequest(target.toString(), {
    ...init,
    headers,
  });
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

    request.setTimeout(NAVIGATION_TIMEOUT_MS, () => {
      request.destroy(new Error(`Timed out after ${NAVIGATION_TIMEOUT_MS}ms`));
    });
    request.on('error', reject);
    if (body !== undefined) {
      request.write(body);
    }
    request.end();
  });
}

function buildHostResolverRules() {
  const configured = process.env.AUTH_LOGIN_SMOKE_HOST_RESOLVER_RULES?.trim();
  if (configured) {
    return configured;
  }

  const targetHost = new URL(SMOKE_URL).hostname;
  const connectHost = new URL(CONNECT_BASE_URL).hostname;
  if (targetHost !== connectHost && isLoopbackHost(connectHost)) {
    return `MAP ${targetHost} ${connectHost}`;
  }
  return '';
}

function isLoopbackHost(hostname) {
  return hostname === '127.0.0.1' || hostname === 'localhost' || hostname === '::1';
}

function isApiRequestUrl(rawUrl) {
  try {
    return new URL(rawUrl).pathname.startsWith('/api/');
  } catch {
    return false;
  }
}

async function main() {
  const response = await fetchWithConnectBase(SMOKE_URL, { method: 'GET' }).catch(() => null);
  if (EXPECT_UNREACHABLE_URL) {
    assert(
      SMOKE_URL === EXPECT_UNREACHABLE_URL,
      `Expected unreachable URL probe to target ${EXPECT_UNREACHABLE_URL}, got ${SMOKE_URL}.`,
    );
    assert(
      !response?.ok,
      `Expected ${SMOKE_URL} to be unreachable for the negative URL-selection probe, but it returned ${response?.status ?? 'network error'}.`,
    );
    process.stdout.write(`${JSON.stringify({
      status: 'passed',
      probe: 'expected-unreachable-url',
      surface: SURFACE,
      url: SMOKE_URL,
    }, null, 2)}\n`);
    return;
  }

  assert(CHROMIUM_BIN, 'Chromium executable was not found. Set CHROMIUM_BIN to run this smoke.');
  assert(response?.ok, `Login route is not reachable at ${SMOKE_URL}. Start the ${SURFACE} dev server before running this smoke.`);

  const dashboardResponse = await fetchWithConnectBase(DASHBOARD_URL, { method: 'GET' }).catch(() => null);
  assert(
    dashboardResponse?.ok,
    `Dashboard route is not reachable at ${DASHBOARD_URL}. Warm-up is required before measuring login latency.`,
  );

  const userDataDir = await mkdtemp(join(tmpdir(), `cybervpn-${SURFACE}-login-smoke-`));
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

  let client;
  let socket;

  try {
    const webSocketUrl = await waitForWebSocketUrl(browserProcess);
    socket = new WebSocket(webSocketUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', reject, { once: true });
    });

    client = new CdpClient(socket);

    const { targetId } = await client.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await client.send('Target.attachToTarget', {
      targetId,
      flatten: true,
    });

    const apiRequests = [];
    const authenticationOptionsBodies = [];
    const loginRequests = [];
    const interceptionErrors = [];
    const apiResponses = [];
    const apiFailures = [];
    const expectedLiveApiRejections = [];
    const consoleErrors = [];
    const pageErrors = [];
    let loginFulfilledAt = null;
    let dashboardObservedAt = null;
    let logoutClickedAt = null;

    client.on('Network.requestWillBeSent', (message) => {
      if (message.sessionId !== sessionId) return;
      const { request } = message.params;
      if (request.url.includes('/api/')) {
        apiRequests.push(`${request.method} ${request.url}`);
      }
      if (LIVE_API && request.url.includes('/api/v1/auth/login')) {
        loginRequests.push({
          method: request.method,
          body: request.postData ? parseJsonRequestBody(request.postData) : null,
        });
      }
      if (LIVE_API && request.url.includes('/api/v1/auth/passkeys/authentication/options') && request.postData) {
        authenticationOptionsBodies.push(parseJsonRequestBody(request.postData));
      }
    });

    client.on('Network.responseReceived', (message) => {
      if (message.sessionId !== sessionId) return;
      const { response } = message.params;
      if (!isApiRequestUrl(response.url)) return;
      const apiResponse = {
        status: response.status,
        url: response.url,
      };
      apiResponses.push(apiResponse);
      const expectedPostLogoutRejection =
        logoutClickedAt &&
        (response.status === 401 || response.status === 403);
      const expectedOptionalPasskeyPolicyRejection =
        LIVE_API &&
        !EXPECT_PASSKEY_LOGIN_UI &&
        response.url.includes('/api/v1/auth/passkeys/policy') &&
        (response.status === 401 || response.status === 403);
      if (expectedOptionalPasskeyPolicyRejection) {
        expectedLiveApiRejections.push(apiResponse);
      }
      if (
        LIVE_API &&
        response.status >= 400 &&
        !expectedPostLogoutRejection &&
        !expectedOptionalPasskeyPolicyRejection
      ) {
        apiFailures.push(apiResponse);
      }
    });

    client.on('Runtime.exceptionThrown', (message) => {
      if (message.sessionId !== sessionId) return;
      const details = message.params.exceptionDetails;
      pageErrors.push(
        details.exception?.description ||
        details.exception?.value ||
        details.text ||
        JSON.stringify(details),
      );
    });

    client.on('Runtime.consoleAPICalled', (message) => {
      if (message.sessionId !== sessionId || message.params.type !== 'error') return;
      consoleErrors.push(message.params.args.map((arg) => arg.value || arg.description || '').join(' '));
    });

    client.on('Fetch.requestPaused', async (message) => {
      if (message.sessionId !== sessionId) return;

      const { requestId, request } = message.params;
      const url = request.url;

      if (url.includes('/api/analytics/')) {
        await client.send('Fetch.fulfillRequest', { requestId, responseCode: 204 }, sessionId);
        return;
      }

      if (url.includes('/api/v1/auth/passkeys/policy')) {
        await fulfillJson(client, sessionId, requestId, PASSKEY_POLICY);
        return;
      }

      if (url.includes('/api/v1/auth/passkeys/authentication/options')) {
        try {
          const body = await readRequestPostData(client, sessionId, message);
          authenticationOptionsBodies.push(body === null ? null : parseJsonRequestBody(body));
        } catch (error) {
          interceptionErrors.push(error instanceof Error ? error.message : String(error));
        }

        await fulfillJson(client, sessionId, requestId, PASSKEY_AUTHENTICATION_OPTIONS);
        return;
      }

      if (url.includes('/api/v1/auth/passkeys/authentication/verify')) {
        await fulfillJson(client, sessionId, requestId, LOGIN_RESPONSE);
        loginFulfilledAt = Date.now();
        return;
      }

      if (url.includes('/api/v1/auth/login')) {
        try {
          const body = await readRequestPostData(client, sessionId, message);
          loginRequests.push({
            method: request.method,
            body: body === null ? null : parseJsonRequestBody(body),
          });
        } catch (error) {
          interceptionErrors.push(error instanceof Error ? error.message : String(error));
        }

        await fulfillJson(client, sessionId, requestId, LOGIN_RESPONSE, [
          { name: 'set-cookie', value: 'access_token=smoke; Path=/api; HttpOnly; SameSite=Lax' },
        ]);
        loginFulfilledAt = Date.now();
        return;
      }

      if (url.includes('/api/v1/auth/logout')) {
        await fulfillJson(client, sessionId, requestId, LOGOUT_RESPONSE, [
          { name: 'set-cookie', value: 'access_token=; Path=/api; Max-Age=0; HttpOnly; SameSite=Lax' },
        ]);
        return;
      }

      if (url.includes('/api/v1/auth/session') || url.includes('/api/auth/optional-session')) {
        await sleep(SESSION_RESPONSE_DELAY_MS);
        await fulfillJson(client, sessionId, requestId, SURFACE_CONFIG.sessionUser);
        return;
      }

      if (url.includes('/api/v1/users/me/profile')) {
        await fulfillJson(client, sessionId, requestId, PROFILE_RESPONSE);
        return;
      }

      await client.send('Fetch.continueRequest', { requestId }, sessionId);
    });

    await client.send('Page.enable', {}, sessionId);
    await client.send('Runtime.enable', {}, sessionId);
    await client.send('Network.enable', {}, sessionId);
    if (!LIVE_API) {
      await client.send('Fetch.enable', {
        patterns: [
          { urlPattern: '*://*/api/analytics/*', requestStage: 'Request' },
          { urlPattern: '*://*/api/v1/auth/passkeys/policy*', requestStage: 'Request' },
          { urlPattern: '*://*/api/v1/auth/passkeys/authentication/options*', requestStage: 'Request' },
          { urlPattern: '*://*/api/v1/auth/passkeys/authentication/verify*', requestStage: 'Request' },
          { urlPattern: '*://*/api/v1/auth/login*', requestStage: 'Request' },
          { urlPattern: '*://*/api/v1/auth/logout*', requestStage: 'Request' },
          { urlPattern: '*://*/api/v1/auth/session*', requestStage: 'Request' },
          { urlPattern: '*://*/api/auth/optional-session*', requestStage: 'Request' },
          { urlPattern: '*://*/api/v1/users/me/profile*', requestStage: 'Request' },
        ],
      }, sessionId);
    }

    await client.send('Page.addScriptToEvaluateOnNewDocument', {
      source: `
        class MockPublicKeyCredential {}
        MockPublicKeyCredential.isConditionalMediationAvailable = async () => true;
        MockPublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable = async () => true;
        Object.defineProperty(window, 'PublicKeyCredential', { configurable: true, value: MockPublicKeyCredential });
        Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true });
        Object.defineProperty(navigator, 'credentials', {
          configurable: true,
          value: {
            get: () => new Promise(() => {}),
          },
        });
      `,
    }, sessionId);

    const loadEvent = waitForEvent(
      client,
      'Page.loadEventFired',
      (message) => message.sessionId === sessionId,
      NAVIGATION_TIMEOUT_MS,
    );
    await client.send('Page.navigate', { url: SMOKE_URL }, sessionId);
    await loadEvent;

    const autocomplete = await evaluate(
      client,
      sessionId,
      `document.querySelector('input[autocomplete*="username"]')?.getAttribute('autocomplete')`,
    );
    if (EXPECT_PASSKEY_LOGIN_UI) {
      await waitForExpression(
        client,
        sessionId,
        `Boolean(document.querySelector('button[aria-label="Sign in with passkey"]'))`,
        ASSERTION_TIMEOUT_MS,
        'Passkey CTA did not render.',
      );

      assert(autocomplete === 'username webauthn', `Expected username webauthn autocomplete, got ${autocomplete}.`);
    }

    await waitForExpression(
      client,
      sessionId,
      `
        (() => {
          const form = document.querySelector('form');
          return Boolean(form && Object.keys(form).some((key) => key.startsWith('__reactProps$')));
        })()
      `,
      ASSERTION_TIMEOUT_MS,
      'Login form was not hydrated before submit.',
    );

    await evaluate(
      client,
      sessionId,
      `document.querySelector('input[autocomplete*="username"]').focus(); true`,
    );
    await client.send('Input.insertText', { text: LOGIN_IDENTIFIER }, sessionId);

    await evaluate(
      client,
      sessionId,
      `document.querySelector('input[autocomplete="current-password"]').focus(); true`,
    );
    await client.send('Input.insertText', { text: LOGIN_PASSWORD }, sessionId);

    await waitForExpression(
      client,
      sessionId,
      `
        document.querySelector('input[autocomplete*="username"]')?.value === ${JSON.stringify(LOGIN_IDENTIFIER)} &&
          document.querySelector('input[autocomplete="current-password"]')?.value === ${JSON.stringify(LOGIN_PASSWORD)}
      `,
      ASSERTION_TIMEOUT_MS,
      'Login form values were not applied before submit.',
    );

    await sleep(100);

    await evaluate(
      client,
      sessionId,
      `document.querySelector('button[type="submit"]').click(); true`,
    );
    if (LIVE_API) {
      loginFulfilledAt = Date.now();
    }

    try {
      await waitForExpression(
        client,
        sessionId,
        `location.pathname === ${JSON.stringify(DASHBOARD_PATH)}`,
        ASSERTION_TIMEOUT_MS,
        `Login form did not navigate to ${DASHBOARD_PATH} after successful login.`,
      );
    } catch (error) {
      const diagnostics = await evaluate(
        client,
        sessionId,
        `
          JSON.stringify({
            location: location.href,
            usernameValue: document.querySelector('input[autocomplete*="username"]')?.value ?? null,
            passwordValueLength: document.querySelector('input[autocomplete="current-password"]')?.value?.length ?? null,
            submitDisabled: document.querySelector('button[type="submit"]')?.disabled ?? null,
            formValid: document.querySelector('form')?.reportValidity() ?? null,
            activeElement: document.activeElement?.outerHTML?.slice(0, 300) ?? null,
            alerts: Array.from(document.querySelectorAll('[role="alert"]')).map((el) => el.textContent?.trim()),
            bodyText: document.body?.innerText?.slice(0, 1000) ?? null,
          }, null, 2)
        `,
      );
      throw new Error(`${error instanceof Error ? error.message : String(error)}\nDiagnostics:\n${diagnostics}\nAPI requests:\n${apiRequests.join('\n')}\nPage errors:\n${pageErrors.join('\n')}\nConsole errors:\n${consoleErrors.join('\n')}`);
    }
    dashboardObservedAt = Date.now();

    const policyRequested = apiRequests.some((request) => request.includes('/api/v1/auth/passkeys/policy'));
    const loginRequested = apiRequests.some((request) => request.includes('/api/v1/auth/login'));
    const conditionalOptionsBody = authenticationOptionsBodies.find((body) => body?.conditional === true);
    const postLoginNavigationLatencyMs = loginFulfilledAt && dashboardObservedAt
      ? dashboardObservedAt - loginFulfilledAt
      : null;

    if (EXPECT_CONDITIONAL_PASSKEY) {
      assert(policyRequested, 'Passkey policy request was not observed.');
      assert(authenticationOptionsBodies.length > 0, 'Passkey authentication options request was not observed.');
      assert(
        conditionalOptionsBody,
        `Conditional UI passkey authentication options request was not observed. Bodies:\n${JSON.stringify(authenticationOptionsBodies, null, 2)}`,
      );
      const conditionalOptionsBodyText = JSON.stringify(conditionalOptionsBody);
      assert(
        !Object.hasOwn(conditionalOptionsBody, 'identifier') || conditionalOptionsBody.identifier === null,
        `Conditional UI passkey authentication options included an identifier: ${conditionalOptionsBodyText}`,
      );
      for (const field of ['email', 'login', 'username']) {
        assert(
          !Object.hasOwn(conditionalOptionsBody, field) || conditionalOptionsBody[field] === null,
          `Conditional UI passkey authentication options included ${field}: ${conditionalOptionsBodyText}`,
        );
      }
      assert(
        !conditionalOptionsBodyText.includes(LOGIN_IDENTIFIER),
        `Conditional UI passkey authentication options leaked the typed identifier: ${conditionalOptionsBodyText}`,
      );
    }

    assert(interceptionErrors.length === 0, `Interception errors observed:\n${interceptionErrors.join('\n')}`);
    assert(loginRequested, 'Normal login submit did not call /api/v1/auth/login.');
    const passwordLoginRequest = loginRequests.find((request) => request.method === 'POST');
    const redactedLoginRequests = loginRequests.map(redactLoginRequest);
    assert(
      passwordLoginRequest,
      `Password login did not submit a POST request. Observed: ${JSON.stringify(redactedLoginRequests, null, 2)}`,
    );
    assert(
      passwordLoginRequest.body?.login_or_email === LOGIN_IDENTIFIER,
      `Password login body did not include the expected login_or_email. Observed: ${JSON.stringify(redactedLoginRequests, null, 2)}`,
    );
    assert(
      passwordLoginRequest.body?.password === LOGIN_PASSWORD,
      `Password login body did not include the expected password field. Observed: ${JSON.stringify(redactedLoginRequests, null, 2)}`,
    );
    assert(
      !Object.hasOwn(passwordLoginRequest.body, 'email'),
      `Password login body should use login_or_email instead of email. Observed: ${JSON.stringify(redactedLoginRequests, null, 2)}`,
    );
	    assert(
	      typeof postLoginNavigationLatencyMs === 'number' &&
	        postLoginNavigationLatencyMs <= POST_LOGIN_NAVIGATION_BUDGET_MS,
	      `Post-login navigation latency exceeded ${POST_LOGIN_NAVIGATION_BUDGET_MS}ms: ${postLoginNavigationLatencyMs}ms`,
	    );
	    assert(pageErrors.length === 0, `Page errors observed:\n${pageErrors.join('\n')}`);
	    assert(consoleErrors.length === 0, `Console errors observed:\n${consoleErrors.join('\n')}`);
	    await waitForExpression(
	      client,
	      sessionId,
	      `Boolean(document.querySelector('button[aria-haspopup="menu"]'))`,
	      ASSERTION_TIMEOUT_MS,
	      'User menu trigger did not render after login.',
	    );
	    await evaluate(
	      client,
	      sessionId,
	      `
	        (() => {
	          const trigger = document.querySelector('button[aria-haspopup="menu"]');
	          trigger?.click();
	          return Boolean(trigger);
	        })()
	      `,
	    );
	    await waitForExpression(
	      client,
	      sessionId,
	      `Boolean(document.querySelector('[role="menu"]'))`,
	      ASSERTION_TIMEOUT_MS,
	      'User menu did not open.',
	    );
	    const userMenuLinks = await evaluate(
	      client,
	      sessionId,
	      `
	        Array.from(document.querySelectorAll('[role="menu"] a[href]')).map((link) => ({
	          href: link.href,
	          pathname: new URL(link.href).pathname,
	          text: link.textContent?.replace(/\\s+/g, ' ').trim() ?? '',
	          role: link.getAttribute('role'),
	        }))
	      `,
	    );
	    assert(
	      userMenuLinks.some((link) => link.pathname === USER_MENU_NAVIGATION_PATH),
	      `User menu did not expose ${USER_MENU_NAVIGATION_PATH}. Observed links: ${JSON.stringify(userMenuLinks, null, 2)}`,
	    );
	    const userMenuNavigationStartedAt = Date.now();
	    const clickedUserMenuLink = await evaluate(
	      client,
	      sessionId,
	      `
	        (() => {
	          const target = Array.from(document.querySelectorAll('[role="menu"] a[href]'))
	            .find((link) => new URL(link.href).pathname === ${JSON.stringify(USER_MENU_NAVIGATION_PATH)});
	          target?.click();
	          return Boolean(target);
	        })()
	      `,
	    );
	    assert(
	      clickedUserMenuLink,
	      `User menu link ${USER_MENU_NAVIGATION_PATH} disappeared before click. Observed links: ${JSON.stringify(userMenuLinks, null, 2)}`,
	    );
	    try {
	      await waitForExpression(
	        client,
	        sessionId,
	        `location.pathname === ${JSON.stringify(USER_MENU_NAVIGATION_PATH)}`,
	        ASSERTION_TIMEOUT_MS,
	        `User menu navigation did not reach ${USER_MENU_NAVIGATION_PATH}.`,
	      );
	    } catch (error) {
	      const diagnostics = await collectUserMenuDiagnostics(client, sessionId);
	      throw new Error(`${error instanceof Error ? error.message : String(error)}\nDiagnostics:\n${diagnostics}\nAPI requests:\n${apiRequests.slice(-60).join('\n')}\nPage errors:\n${pageErrors.join('\n')}\nConsole errors:\n${consoleErrors.join('\n')}`);
	    }
	    const userMenuNavigationLatencyMs = Date.now() - userMenuNavigationStartedAt;
	    await waitForExpression(
	      client,
	      sessionId,
	      `Boolean(document.querySelector('button[aria-haspopup="menu"]'))`,
	      ASSERTION_TIMEOUT_MS,
	      'User menu trigger did not render after menu navigation.',
	    );
	    await evaluate(
	      client,
	      sessionId,
	      `
	        (() => {
	          const trigger = document.querySelector('button[aria-haspopup="menu"]');
	          trigger?.click();
	          return Boolean(trigger);
	        })()
	      `,
	    );
	    await waitForExpression(
	      client,
	      sessionId,
	      `
	        Array.from(document.querySelectorAll('button'))
	          .some((button) => /sign\\s*out/i.test(button.textContent ?? '') && !button.matches('[aria-haspopup="menu"]'))
	      `,
	      ASSERTION_TIMEOUT_MS,
	      'User menu logout button did not render.',
	    );
	    await evaluate(
	      client,
	      sessionId,
	      `
	        (() => {
	          const logoutButton = Array.from(document.querySelectorAll('button'))
	            .find((button) => /sign\\s*out/i.test(button.textContent ?? '') && !button.matches('[aria-haspopup="menu"]'));
	          logoutButton?.click();
	          return Boolean(logoutButton);
	        })()
	      `,
	    );
      logoutClickedAt = Date.now();
	    await waitForExpression(
	      client,
	      sessionId,
	      `location.pathname === ${JSON.stringify(LOGIN_PATH)}`,
	      ASSERTION_TIMEOUT_MS,
	      `User menu logout did not navigate to ${LOGIN_PATH}.`,
	    );
	    const logoutNavigationPath = await evaluate(client, sessionId, 'location.pathname');
      const sessionAfterLogoutStatus = LIVE_API
        ? await evaluate(
          client,
          sessionId,
          `
            fetch('/api/v1/auth/session', { credentials: 'include', cache: 'no-store' })
              .then((response) => response.status)
              .catch((error) => 'network:' + error.message)
          `,
        )
        : null;
      if (LIVE_API) {
        assert(
          sessionAfterLogoutStatus === 401 || sessionAfterLogoutStatus === 403,
          `Expected /api/v1/auth/session after live logout to return 401/403, got ${sessionAfterLogoutStatus}.`,
        );
        assert(
          apiFailures.length === 0,
          `Live API failures observed outside the expected post-logout session rejection:\n${JSON.stringify(apiFailures, null, 2)}`,
        );
      }
	    assert(pageErrors.length === 0, `Page errors observed:\n${pageErrors.join('\n')}`);
	    assert(consoleErrors.length === 0, `Console errors observed:\n${consoleErrors.join('\n')}`);

    process.stdout.write(`${JSON.stringify({
      status: 'passed',
      surface: SURFACE,
      url: SMOKE_URL,
      liveApi: LIVE_API,
      intercepted: !LIVE_API,
      devBypassAuth: false,
      dashboardUrl: DASHBOARD_URL,
      dashboardPath: DASHBOARD_PATH,
      sessionResponseDelayMs: SESSION_RESPONSE_DELAY_MS,
      postLoginNavigationBudgetMs: POST_LOGIN_NAVIGATION_BUDGET_MS,
      postLoginNavigationLatencyMs,
      autocomplete,
      expectConditionalPasskey: EXPECT_CONDITIONAL_PASSKEY,
      expectPasskeyLoginUi: EXPECT_PASSKEY_LOGIN_UI,
      expectedLiveApiRejections,
	      apiRequests,
	      authenticationOptionsBodies,
	      loginRequests: loginRequests.map(redactLoginRequest),
	      userMenu: {
	        navigationPath: USER_MENU_NAVIGATION_PATH,
	        navigationLatencyMs: userMenuNavigationLatencyMs,
	        logoutNavigationPath,
          sessionAfterLogoutStatus,
	        links: userMenuLinks,
	      },
      apiResponses: apiResponses.slice(0, 200),
	    }, null, 2)}\n`);
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

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
