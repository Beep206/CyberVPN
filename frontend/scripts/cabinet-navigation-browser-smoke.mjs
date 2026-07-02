import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';

const DEFAULT_URL = 'http://127.0.0.1:9003/ru-RU/dashboard';
const SMOKE_URL = process.env.FRONTEND_CABINET_NAV_SMOKE_URL || DEFAULT_URL;
const CHROMIUM_BIN = process.env.CHROMIUM_BIN || findChromium();
const NAVIGATION_TIMEOUT_MS = 60_000;
const ASSERTION_TIMEOUT_MS = 15_000;
const ROUTES = [
  '/servers',
  '/subscriptions',
  '/wallet',
  '/payment-history',
  '/support',
  '/messages',
  '/settings',
  '/settings/security',
];

const baseUrl = new URL(SMOKE_URL);
const locale = baseUrl.pathname.split('/').filter(Boolean)[0] || 'ru-RU';

const SESSION_RESPONSE = {
  id: 'synthetic-customer',
  email: 'nav-smoke@example.com',
  login: 'nav_smoke',
  is_active: true,
  is_email_verified: true,
  role: 'viewer',
  created_at: '2026-07-02T00:00:00.000Z',
};

const CLIENT_CAPABILITIES_RESPONSE = {
  auth: {
    email_password: true,
    magic_link: true,
    telegram: true,
  },
  payments: {
    web_checkout: true,
    telegram_stars: false,
    cryptobot: true,
    manual_invoice: false,
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
    portal: false,
    applications: false,
    codes: false,
    attribution: false,
    storefronts: false,
    reporting: false,
    settlement_sandbox: false,
    webhooks: false,
    payouts: false,
    event_backbone: false,
  },
  site: {
    customer_site_mode: 'cabinet_only',
    cabinet_only: true,
    version: 1,
    public_hosts: [],
    cabinet_hosts: ['127.0.0.1', 'localhost'],
    cabinet_destination_path: '/dashboard',
    cabinet_marketing_route_action: 'redirect_public',
    public_marketing_destination_path: '/',
    allowed_path_prefixes: [],
    preserve_query_keys: [],
    registration_policy_independent: true,
  },
  onboarding: {
    post_registration_code_prompt: false,
    web_otp: false,
    telegram_miniapp: false,
    state_store: false,
    telegram_bot_code_apply: false,
    connection_bootstrap: true,
    flow_key: 'post_registration_growth_code_v1',
    version: 1,
    allowed_code_types: ['invite', 'gift', 'promo'],
    allow_referral_input: true,
    allow_partner_input: false,
    available: true,
  },
};

const SUBSCRIPTION = {
  subscription_key: 'grant:nav-smoke',
  kind: 'entitlement_grant',
  status: 'active',
  display_name: 'Navigation smoke',
  plan_uuid: 'plan-nav-smoke',
  plan_code: 'nav-smoke',
  source_type: 'manual',
  source_order_id: null,
  entitlement_grant_id: 'grant-nav-smoke',
  service_identity_id: 'svc-nav-smoke',
  provider_name: 'smoke',
  expires_at: '2026-12-31T00:00:00.000Z',
  created_at: '2026-07-02T00:00:00.000Z',
  effective_entitlements: {
    display_traffic_label: 'Unlimited',
    device_limit: 5,
    connection_modes: ['vless'],
    support_level: 'standard',
  },
  invite_bundle: {},
  is_trial: false,
  addons: [],
  can_manage: true,
  can_deliver_config: true,
  management_scope: 'subscription_vpn_identity',
};

const CUSTOMER_SUBSCRIPTIONS_RESPONSE = {
  customer_account_id: 'customer-nav-smoke',
  auth_realm_id: 'realm-nav-smoke',
  selected_subscription_key: SUBSCRIPTION.subscription_key,
  default_subscription_key: SUBSCRIPTION.subscription_key,
  items: [SUBSCRIPTION],
  limitations: [],
};

const ENTITLEMENTS_RESPONSE = {
  status: SUBSCRIPTION.status,
  plan_uuid: SUBSCRIPTION.plan_uuid,
  plan_code: SUBSCRIPTION.plan_code,
  display_name: SUBSCRIPTION.display_name,
  period_days: 365,
  expires_at: SUBSCRIPTION.expires_at,
  effective_entitlements: SUBSCRIPTION.effective_entitlements,
  invite_bundle: {},
  is_trial: false,
  addons: [],
};

function findChromium() {
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

function encodeJsonBody(data) {
  return Buffer.from(JSON.stringify(data)).toString('base64');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
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
  let lastError = null;

  while (Date.now() < deadline) {
    try {
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

      if (result.exceptionDetails) {
        lastError = result.exceptionDetails.text || 'Runtime evaluation failed';
      }
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }

    await sleep(100);
  }

  throw new Error(lastError ? `${message} Last error: ${lastError}` : message);
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

function apiResponseFor(url) {
  const { pathname } = new URL(url);

  if (pathname.endsWith('/api/v1/auth/session')) {
    return SESSION_RESPONSE;
  }

  if (pathname.endsWith('/api/v1/client/capabilities')) {
    return CLIENT_CAPABILITIES_RESPONSE;
  }

  if (pathname.endsWith('/api/v1/customer-subscriptions')) {
    return CUSTOMER_SUBSCRIPTIONS_RESPONSE;
  }

  if (pathname.includes('/api/v1/customer-subscriptions/') && pathname.endsWith('/entitlements')) {
    return ENTITLEMENTS_RESPONSE;
  }

  if (pathname.includes('/api/v1/customer-subscriptions/') && pathname.endsWith('/service-state')) {
    return {
      status: 'ready',
      profile_status: 'ready',
      credential_status: 'ready',
      channel_status: 'ready',
      provider: 'smoke',
      last_connection_at: null,
    };
  }

  if (pathname.includes('/api/v1/customer-subscriptions/') && pathname.endsWith('/usage')) {
    return {
      used_bytes: 0,
      total_bytes: null,
      reset_at: null,
    };
  }

  if (pathname.endsWith('/api/v1/profile')) {
    return SESSION_RESPONSE;
  }

  return {};
}

function localizedPath(route) {
  return `/${locale}${route}`;
}

async function waitForCabinetShell(client, sessionId) {
  await waitForExpression(
    client,
    sessionId,
    `Boolean(document.querySelector('aside a[href="${localizedPath('/servers')}"]'))`,
    ASSERTION_TIMEOUT_MS,
    'Desktop cabinet sidebar did not render the servers link.',
  );
}

async function clickCabinetRoute(client, sessionId, route) {
  const expectedPath = localizedPath(route);
  const clickResult = await evaluate(
    client,
    sessionId,
    `
      (() => {
        const link = document.querySelector('aside a[href="${expectedPath}"]');
        if (!link) {
          return { ok: false, reason: 'missing-link', expectedPath: ${JSON.stringify(expectedPath)} };
        }
        const before = location.pathname;
        link.click();
        return { ok: true, before, href: link.href };
      })()
    `,
  );

  assert(clickResult?.ok, `Could not click cabinet route ${route}: ${JSON.stringify(clickResult)}`);

  await waitForExpression(
    client,
    sessionId,
    `location.pathname === ${JSON.stringify(expectedPath)}`,
    ASSERTION_TIMEOUT_MS,
    `Cabinet route ${route} did not update location.pathname to ${expectedPath}.`,
  );

  await waitForCabinetShell(client, sessionId);

  return {
    route,
    expectedPath,
    before: clickResult.before,
    href: clickResult.href,
    actualPath: await evaluate(client, sessionId, 'location.pathname'),
  };
}

async function main() {
  assert(CHROMIUM_BIN, 'Chromium executable was not found. Set CHROMIUM_BIN to run this smoke.');

  const response = await fetch(SMOKE_URL, { method: 'GET' }).catch(() => null);
  assert(response?.ok, `Frontend production-like server is not reachable at ${SMOKE_URL}. Start it before running this smoke.`);

  const userDataDir = await mkdtemp(join(tmpdir(), 'cybervpn-cabinet-nav-smoke-'));
  const browserProcess = spawn(CHROMIUM_BIN, [
    '--headless=new',
    '--use-gl=swiftshader',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--remote-debugging-port=0',
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
    const consoleErrors = [];
    const pageErrors = [];
    const fallbackLogs = [];

    client.on('Network.requestWillBeSent', (message) => {
      if (message.sessionId !== sessionId) return;
      const { request } = message.params;
      if (request.url.includes('/api/')) {
        apiRequests.push(`${request.method} ${request.url}`);
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
      if (message.sessionId !== sessionId) return;
      const text = message.params.args.map((arg) => arg.value || arg.description || '').join(' ');
      if (text.includes('[safe-cabinet-link] document navigation fallback')) {
        fallbackLogs.push(text);
      }
      if (message.params.type === 'error') {
        consoleErrors.push(text);
      }
    });

    client.on('Fetch.requestPaused', async (message) => {
      if (message.sessionId !== sessionId) return;

      const { requestId, request } = message.params;
      const body = encodeJsonBody(apiResponseFor(request.url));

      await client.send('Fetch.fulfillRequest', {
        requestId,
        responseCode: 200,
        responseHeaders: [{ name: 'content-type', value: 'application/json' }],
        body,
      }, sessionId);
    });

    await client.send('Page.enable', {}, sessionId);
    await client.send('Runtime.enable', {}, sessionId);
    await client.send('Network.enable', {}, sessionId);
    await client.send('Fetch.enable', {
      patterns: [{ urlPattern: '*://*/api/v1/*', requestStage: 'Request' }],
    }, sessionId);
    await client.send('Emulation.setDeviceMetricsOverride', {
      width: 1366,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    }, sessionId);

    const loadEvent = waitForEvent(
      client,
      'Page.loadEventFired',
      (message) => message.sessionId === sessionId,
      NAVIGATION_TIMEOUT_MS,
    );
    await client.send('Page.navigate', { url: SMOKE_URL }, sessionId);
    await loadEvent;

    await waitForCabinetShell(client, sessionId);

    const navigations = [];
    for (const route of ROUTES) {
      navigations.push(await clickCabinetRoute(client, sessionId, route));
    }

    const fatalHydrationErrors = [...pageErrors, ...consoleErrors].filter((error) =>
      /Minified React error #418|React error #418|Hydration failed/i.test(error)
    );
    assert(fatalHydrationErrors.length === 0, `Fatal hydration errors observed:\n${fatalHydrationErrors.join('\n')}`);

    process.stdout.write(`${JSON.stringify({
      status: 'passed',
      url: SMOKE_URL,
      locale,
      routes: ROUTES,
      navigations,
      fallbackLogs,
      pageErrorCount: pageErrors.length,
      consoleErrorCount: consoleErrors.length,
      apiRequests,
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
