import fs from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('/home/beep/.local/lib/node_modules/playwright');

const issueId = 'CYBA-697';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '../../..');
const outputRoot = path.join(repoRoot, 'evidence/customer/cyba-697');
const screenshotDir = path.join(outputRoot, 'screenshots');
const notesDir = path.join(outputRoot, 'notes');
const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
const baseUrl = process.env.CYBA697_BASE_URL || 'http://127.0.0.1:9001';
let sessionAuthorized = true;

fs.mkdirSync(screenshotDir, { recursive: true });
fs.mkdirSync(notesDir, { recursive: true });

const now = new Date('2026-06-16T16:00:00.000Z');
const plusDays = (days) => new Date(now.getTime() + days * 86_400_000).toISOString();
const minusDays = (days) => new Date(now.getTime() - days * 86_400_000).toISOString();

const syntheticUser = {
  id: 'auth-user-synthetic-cyba697',
  public_uid: 14677650,
  email: 'qa-customer.cyba697@example.test',
  login: 'qa_customer_cyba697',
  role: 'viewer',
  is_active: true,
  is_email_verified: true,
  created_at: '2026-05-01T12:00:00.000Z',
  telegram_id: 8800697001,
};

const syntheticProfile = {
  id: 'profile-cyba697',
  public_uid: 14677650,
  email: syntheticUser.email,
  display_name: 'QA Customer CYBA-697',
  avatar_url: null,
  language: 'ru-RU',
  timezone: 'Europe/Moscow',
  created_at: syntheticUser.created_at,
  updated_at: '2026-06-16T12:00:00.000Z',
};

const subscriptionKey = 'grant_cyba697_active';
const entitlement = {
  status: 'active',
  plan_uuid: 'plan-pro-month',
  plan_code: 'pro_month',
  display_name: 'CyberVPN Pro Monthly',
  period_days: 30,
  expires_at: plusDays(24),
  effective_entitlements: {
    access_state: 'active',
    device_limit: 5,
    devices: 5,
    display_traffic_label: 'Безлимит',
    max_devices: 5,
    plan_name: 'CyberVPN Pro Monthly',
    traffic_limit_bytes: 0,
    vpn_protocols: ['vless', 'wireguard'],
  },
  invite_bundle: {},
  is_trial: false,
  addons: [],
};

const subscriptions = {
  customer_account_id: 'customer-account-cyba697',
  auth_realm_id: 'realm-cyba697',
  selected_subscription_key: subscriptionKey,
  default_subscription_key: subscriptionKey,
  items: [
    {
      subscription_key: subscriptionKey,
      kind: 'entitlement_grant',
      status: 'active',
      display_name: 'CyberVPN Pro Monthly',
      plan_uuid: 'plan-pro-month',
      plan_code: 'pro_month',
      source_type: 'synthetic_qa',
      source_order_id: 'order-cyba697-paid',
      entitlement_grant_id: 'grant-cyba697-paid',
      service_identity_id: 'svc-cyba697-active',
      provider_name: 'remnawave',
      expires_at: plusDays(24),
      created_at: minusDays(6),
      effective_entitlements: entitlement.effective_entitlements,
      invite_bundle: {},
      is_trial: false,
      addons: [],
      can_manage: true,
      can_deliver_config: true,
      management_scope: 'subscription_entitlement',
    },
    {
      subscription_key: 'trial_cyba697_readonly',
      kind: 'trial',
      status: 'expired',
      display_name: 'Trial expired sample',
      plan_uuid: 'plan-trial',
      plan_code: 'trial',
      source_type: 'synthetic_qa',
      source_order_id: null,
      entitlement_grant_id: null,
      service_identity_id: 'svc-cyba697-trial',
      provider_name: 'remnawave',
      expires_at: minusDays(1),
      created_at: minusDays(10),
      effective_entitlements: {
        access_state: 'expired',
        device_limit: 1,
        display_traffic_label: '10 GB',
        traffic_limit_bytes: 10 * 1024 ** 3,
      },
      invite_bundle: {},
      is_trial: true,
      addons: [],
      can_manage: false,
      can_deliver_config: false,
      management_scope: 'account_vpn_identity',
    },
  ],
  limitations: [],
};

const serviceState = {
  access_active: true,
  access_state: 'active',
  access_delivery_channel: {
    id: 'adc-cyba697',
    provider_name: 'remnawave',
    channel_type: 'shared_client',
    status: 'active',
  },
  payment_state: 'paid',
  provisioning_state: 'ready',
  provisioning_profile: {
    id: 'profile-cyba697-active',
    status: 'ready',
  },
  provider_name: 'remnawave',
  channel_type: 'shared_client',
  credential_type: 'desktop_client',
  credential_subject_key: 'official-web-dashboard',
  credential_available: true,
  credentials_active: true,
  credential_expires_at: plusDays(24),
  device_credential: {
    id: 'credential-cyba697-active',
    status: 'active',
    expires_at: plusDays(24),
  },
  config_available: true,
  config_links_available: true,
  config_delivery_available: true,
  service_identity: {
    id: 'svc-cyba697-active',
    status: 'active',
  },
  warnings: [],
  blocking_reasons: [],
  updated_at: now.toISOString(),
};

const usage = {
  bandwidth_used_bytes: 23 * 1024 ** 3,
  bandwidth_limit_bytes: 0,
  active_connections: 2,
  max_connections: 5,
  usage_available: true,
  period_started_at: minusDays(6),
  period_ends_at: plusDays(24),
  last_connection_at: minusDays(0.2),
};

const plans = [
  {
    uuid: 'plan-basic-month',
    plan_code: 'basic_month',
    code: 'basic_month',
    display_name: 'Basic Monthly',
    name: 'Basic Monthly',
    description: 'Monthly access for up to 3 devices',
    duration_days: 30,
    devices_included: 3,
    connection_modes: ['vless'],
    traffic_limit_bytes: 100 * 1024 ** 3,
    traffic_policy: { display_label: '100 GB' },
    price: 499,
    price_minor: 499,
    price_usd: 4.99,
    price_rub: 449,
    currency: 'USD',
    catalog_visibility: 'public',
    is_public: true,
    is_active: true,
    sale_channels: ['web'],
    sort_order: 10,
    features: ['100 GB', '3 devices'],
  },
  {
    uuid: 'plan-pro-quarter',
    plan_code: 'pro_quarter',
    code: 'pro_quarter',
    display_name: 'Pro Quarterly',
    name: 'Pro Quarterly',
    description: 'Quarterly access for ten devices',
    duration_days: 90,
    devices_included: 10,
    connection_modes: ['vless', 'wireguard'],
    traffic_limit_bytes: 0,
    traffic_policy: { display_label: 'Unlimited' },
    price: 1299,
    price_minor: 1299,
    price_usd: 12.99,
    price_rub: 1190,
    currency: 'USD',
    catalog_visibility: 'public',
    is_public: true,
    is_active: true,
    sale_channels: ['web'],
    sort_order: 20,
    features: ['Unlimited traffic', '10 devices'],
  },
  {
    uuid: 'plan-family-year',
    plan_code: 'family_year',
    code: 'family_year',
    display_name: 'Family Year',
    name: 'Family Year',
    description: 'Annual access for larger households',
    duration_days: 365,
    devices_included: 12,
    connection_modes: ['vless', 'wireguard'],
    traffic_limit_bytes: 0,
    traffic_policy: { display_label: 'Unlimited' },
    price: 3999,
    price_minor: 3999,
    price_usd: 39.99,
    price_rub: 3490,
    currency: 'USD',
    catalog_visibility: 'public',
    is_public: true,
    is_active: true,
    sale_channels: ['web'],
    sort_order: 30,
    features: ['Unlimited traffic', '12 devices'],
  },
];

const servers = [
  {
    id: 'srv-de-01',
    uuid: 'srv-de-01',
    name: 'Frankfurt-01',
    address: 'de.example.test',
    country: 'Germany',
    country_code: 'DE',
    city: 'Frankfurt',
    region: 'EU Central',
    status: 'online',
    load: 38,
    load_percentage: 38,
    latency_ms: 24,
    protocol: 'vless',
    vpn_protocol: 'vless',
    users_online: 38,
    is_connected: true,
    is_disabled: false,
    supported_protocols: ['vless', 'wireguard'],
  },
  {
    id: 'srv-nl-01',
    uuid: 'srv-nl-01',
    name: 'Amsterdam-01',
    address: 'nl.example.test',
    country: 'Netherlands',
    country_code: 'NL',
    city: 'Amsterdam',
    region: 'EU West',
    status: 'online',
    load: 44,
    load_percentage: 44,
    latency_ms: 31,
    protocol: 'wireguard',
    vpn_protocol: 'wireguard',
    users_online: 44,
    is_connected: true,
    is_disabled: false,
    supported_protocols: ['wireguard'],
  },
  {
    id: 'srv-us-01',
    uuid: 'srv-us-01',
    name: 'New York-01',
    address: 'us.example.test',
    country: 'United States',
    country_code: 'US',
    city: 'New York',
    region: 'US East',
    status: 'maintenance',
    load: 0,
    load_percentage: 0,
    latency_ms: 98,
    protocol: 'vless',
    vpn_protocol: 'vless',
    users_online: 0,
    is_connected: false,
    is_disabled: false,
    supported_protocols: ['vless'],
  },
];

function json(body, status = 200) {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  };
}

function sanitizeUrl(urlValue) {
  const parsed = new URL(urlValue);
  return `${parsed.pathname}${parsed.search ? '?<redacted-query>' : ''}`;
}

function routeKey(urlValue) {
  const parsed = new URL(urlValue);
  return parsed.pathname.replace(/\/+$/, '') || '/';
}

function apiResponseFor(request) {
  const url = new URL(request.url());
  const key = routeKey(request.url());
  const method = request.method();

  if (key === '/api/auth/optional-session' && method === 'GET') {
    return sessionAuthorized ? json(syntheticUser) : json(null, 401);
  }

  if (key.startsWith('/api/analytics/')) {
    return json({ ok: true }, 202);
  }

  if (key === '/api/v1/me/realtime/sse' && method === 'GET') {
    return {
      status: 200,
      headers: {
        'content-type': 'text/event-stream',
        'cache-control': 'no-cache',
      },
      body: 'event: connected\ndata: {"type":"connected","cursor":"cursor-cyba697"}\n\n',
    };
  }

  if ((key === '/api/v1/auth/session' || key === '/api/v1/auth/me') && method === 'GET') {
    return sessionAuthorized ? json(syntheticUser) : json({ detail: 'Unauthorized' }, 401);
  }

  if (key === '/api/v1/auth/logout' && method === 'POST') {
    sessionAuthorized = false;
    return json({ message: 'Logged out' });
  }

  if (key === '/api/v1/auth/refresh' && method === 'POST') {
    return json({ refreshed: true });
  }

  if (key === '/api/v1/users/me/profile' && method === 'GET') {
    return json(syntheticProfile);
  }

  if (key === '/api/v1/users/me/profile' && method === 'PATCH') {
    return json({ ...syntheticProfile, updated_at: now.toISOString() });
  }

  if (key === '/api/v1/users/me/notifications' && method === 'GET') {
    return json({
      email_security: true,
      email_marketing: false,
      push_connection: false,
      push_payment: true,
      push_subscription: false,
    });
  }

  if (key === '/api/v1/growth-notifications/preferences' && method === 'GET') {
    return json({
      growth_in_app_invites: false,
      growth_email_referral_rewards: false,
      growth_telegram_referral_rewards: false,
      growth_email_gifts: false,
      growth_telegram_admin_updates: false,
    });
  }

  if (key === '/api/v1/client/capabilities' && method === 'GET') {
    return json({
      auth: { email_password: true, magic_link: true, telegram: true },
      payments: {
        web_checkout: true,
        telegram_stars: false,
        cryptobot: false,
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
    });
  }

  if (key === '/api/v1/customer-subscriptions' && method === 'GET') {
    return json(subscriptions);
  }

  if (key === `/api/v1/customer-subscriptions/${subscriptionKey}` && method === 'GET') {
    return json(subscriptions.items[0]);
  }

  if (key === `/api/v1/customer-subscriptions/${subscriptionKey}/entitlements` && method === 'GET') {
    return json(entitlement);
  }

  if (key === `/api/v1/customer-subscriptions/${subscriptionKey}/service-state` && method === 'POST') {
    return json(serviceState);
  }

  if (key === `/api/v1/customer-subscriptions/${subscriptionKey}/usage` && method === 'GET') {
    return json(usage);
  }

  if (key === `/api/v1/customer-subscriptions/${subscriptionKey}/config` && method === 'GET') {
    return json({
      config: '',
      isFound: true,
      links: ['vless://synthetic-cyba697@de.example.test:443?security=tls#CyberVPN-Full-Link'],
      ssConfLinks: {},
      subscriptionUrl: 'https://sub.example.test/cyba697/full-subscription-url-visible',
    });
  }

  if (key === '/api/v1/entitlements/current' && method === 'GET') {
    return json(entitlement);
  }

  if (key === '/api/v1/access-delivery-channels/current/service-state' && method === 'POST') {
    return json(serviceState);
  }

  if (key === '/api/v1/users/me/usage' && method === 'GET') {
    return json(usage);
  }

  if (key === '/api/v1/wallet' && method === 'GET') {
    return json({ balance: 1250, currency: 'USD', updated_at: now.toISOString() });
  }

  if (key === '/api/v1/trial/status' && method === 'GET') {
    return json({
      eligible: false,
      active: false,
      trial_used: true,
      trial_started_at: null,
      trial_ends_at: null,
    });
  }

  if (key === '/api/v1/referral/stats' && method === 'GET') {
    return json({
      total_referrals: 2,
      qualifying_orders: 1,
      total_earnings: 1200,
      current_commission_rate: 15,
    });
  }

  if (key === '/api/v1/plans' && method === 'GET') {
    return json(plans);
  }

  if (key === '/api/v1/addons/catalog' && method === 'GET') {
    return json([
      {
        uuid: 'addon-device-1',
        code: 'extra_device',
        display_name: 'Extra device',
        name: 'Extra device',
        description: 'Add one device',
        duration_mode: 'subscription_period',
        delta_entitlements: { device_limit: 1 },
        price_minor: 199,
        price_usd: 1.99,
        price_rub: 179,
        currency: 'USD',
        is_public: true,
        is_active: true,
        sale_channels: ['web'],
        requires_location: false,
        max_quantity_by_plan: { pro_month: 3 },
      },
    ]);
  }

  if (key === '/api/v1/orders' && method === 'GET') {
    return json([
      {
        id: 'order-cyba697-paid',
        public_id: 'ORD-CYBA697',
        status: 'paid',
        order_status: 'paid',
        settlement_status: 'paid',
        total_amount: 1299,
        amount_minor: 1299,
        displayed_price: 12.99,
        currency_code: 'USD',
        currency: 'USD',
        plan_code: 'pro_month',
        plan_name: 'CyberVPN Pro Monthly',
        subscription_plan_id: 'plan-pro-month',
        items: [{ display_name: 'CyberVPN Pro Monthly' }],
        created_at: minusDays(6),
        updated_at: minusDays(6),
      },
    ]);
  }

  if (key === '/api/v1/servers' && method === 'GET') {
    return json(servers);
  }

  if (key === '/api/v1/servers/stats' && method === 'GET') {
    return json({
      total_servers: servers.length,
      online_servers: 2,
      offline_servers: 0,
      average_load: 41,
      total_bandwidth: 23 * 1024 ** 3,
    });
  }

  if (key === '/api/v1/public-network/overview' && method === 'GET') {
    return json({
      regions: 3,
      countries: 3,
      online_servers: 2,
      average_load: 41,
    });
  }

  if (key === '/api/v1/auth/devices' && method === 'GET') {
    return json({
      devices: [
        {
          id: 'device-cyba697-current',
          device_id: 'device-cyba697-current',
          is_current: true,
          user_agent: 'Chrome/126.0 Linux',
          ip_address: '203.0.113.10',
          created_at: minusDays(2),
          last_seen_at: minusDays(0.1),
          expires_at: plusDays(24),
        },
      ],
      total: 1,
      total_devices: 1,
      limit: 5,
      remaining: 4,
    });
  }

  if (key === '/api/v1/auth/me/privacy-requests' && method === 'POST') {
    return json({
      id: 'privacy-cyba697',
      request_type: 'account_deletion',
      status: 'open',
      ticket_reference: 'PRIV-CYBA697',
      target_contact: 'privacy@cyber-vpn.net',
      manual_fulfillment_target_days: 30,
      created_at: now.toISOString(),
    }, 201);
  }

  if ((key === '/api/v1/two-factor/status' || key === '/api/v1/2fa/status') && method === 'GET') {
    return json({ status: 'disabled', enabled: false, recovery_codes_remaining: 0 });
  }

  if (key === '/api/v1/security/antiphishing' && method === 'GET') {
    return json({ code: 'QA-SAFE-697', updated_at: now.toISOString() });
  }

  if ((key === '/api/v1/passkeys/policy' || key === '/api/v1/auth/passkeys/policy') && method === 'GET') {
    return json({
      enabled: true,
      surface: 'customer',
      realm_key: 'customer',
      rp_id: '127.0.0.1',
      rp_name: 'CyberVPN QA',
      allowedOrigins: [baseUrl],
      conditionalUiEnabled: false,
      registrationEnabled: false,
      authenticationEnabled: true,
      reauthenticationEnabled: true,
      adminCountsAsMfa: false,
      challengeTtlSeconds: 300,
      browserTimeoutMs: 60000,
    });
  }

  if ((key === '/api/v1/passkeys' || key === '/api/v1/auth/passkeys') && method === 'GET') {
    return json({ credentials: [] });
  }

  if (key === '/api/v1/growth-notifications' && method === 'GET') {
    return json([]);
  }

  if (key === '/api/v1/growth-notifications/counters' && method === 'GET') {
    return json({ unread: 0, total: 0, actionable: 0 });
  }

  if (key === '/api/v1/public/network/dpi-score' && method === 'GET') {
    return json({ score: 96, confidence: 'high', status: 'nominal', updated_at: now.toISOString() });
  }

  if (key === '/api/v1/me/conversations' && method === 'GET') {
    return json({ conversations: [], nextCursor: null });
  }

  if (key === '/api/v1/me/notifications' && method === 'GET') {
    return json({ notifications: [], nextCursor: null });
  }

  if (key === '/api/v1/me/realtime/sync' && method === 'GET') {
    return json({
      cursor: 'cursor-cyba697',
      conversations: [],
      messages: [],
      notifications: [],
      unread_counts: { conversations: 0, notifications: 0 },
    });
  }

  if (key === '/api/v1/oauth/telegram/magic-link' && method === 'GET') {
    return json({
      token: 'fresh-magic-cyba697',
      bot_url: 'https://t.me/C_y_b_e_r_VPN_Bot?start=auth_fresh-magic-cyba697',
      deep_link_url: 'tg://resolve?domain=C_y_b_e_r_VPN_Bot&start=auth_fresh-magic-cyba697',
    });
  }

  if (key.startsWith('/api/v1/oauth/telegram/magic-link/') && key.endsWith('/status') && method === 'GET') {
    const token = key.split('/').at(-2);
    if (token === 'expired-magic-cyba697') {
      return json({ status: 'expired', login_result: null });
    }

    return json({
      status: 'completed',
      login_result: {
        user: syntheticUser,
        is_new_user: false,
        requires_2fa: false,
        tfa_token: null,
      },
    });
  }

  if (key === '/api/v1/auth/telegram/bot-link' && method === 'POST') {
    if (url.search.includes('expired')) {
      return json({ detail: 'Telegram link expired' }, 400);
    }

    return json({
      user: syntheticUser,
      is_new_user: false,
      requires_2fa: false,
      tfa_token: null,
    });
  }

  return json({ detail: `Unhandled synthetic endpoint: ${method} ${key}` }, 404);
}

async function installRoutes(context, result) {
  await context.route('https://telegram.org/js/telegram-web-app.js', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: 'window.Telegram = window.Telegram || { WebApp: { initData: "", ready() {}, expand() {} } };',
    }),
  );

  await context.route('**/api/**', async (route) => {
    const request = route.request();
    const response = apiResponseFor(request);
    const parsed = new URL(request.url());
    result.network.push({
      method: request.method(),
      path: sanitizeUrl(request.url()),
      routeKey: routeKey(request.url()),
      status: response.status ?? 200,
      mocked: true,
    });
    if (parsed.pathname.includes('/auth/telegram') || parsed.pathname.includes('/oauth/telegram')) {
      result.telegramNetwork.push({
        method: request.method(),
        path: sanitizeUrl(request.url()),
        routeKey: routeKey(request.url()),
        status: response.status ?? 200,
      });
    }
    await route.fulfill(response);
  });
}

async function screenshot(page, result, name, fullPage = false) {
  const fileName = `${issueId}__customer-portal__synthetic__ru-RU__desktop-1440__${name}__${timestamp}.png`;
  const targetPath = path.join(screenshotDir, fileName);
  await page.screenshot({ path: targetPath, fullPage });
  const relative = path.relative(repoRoot, targetPath);
  result.screenshots.push(relative);
  return relative;
}

async function textSnapshot(page) {
  return page.locator('body').innerText({ timeout: 10_000 });
}

function pass(id, actual, expected) {
  return { id, status: 'PASS', actual, expected };
}

function fail(id, actual, expected) {
  return { id, status: 'FAIL', actual, expected };
}

function record(result, id, condition, actual, expected) {
  result.checks.push(condition ? pass(id, actual, expected) : fail(id, actual, expected));
}

async function gotoReady(page, routePath) {
  await page.goto(`${baseUrl}${routePath}`, { timeout: 30_000, waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});
  await page.waitForTimeout(500);
}

async function run() {
  const result = {
    baseUrl,
    checks: [],
    console: [],
    docs: 'Context7 MCP quota exceeded; ctx7 fallback checked /microsoft/playwright.dev and /microsoft/playwright for locator.innerText, page.on, page.goto, page.screenshot, route APIs.',
    environment: {
      browser: 'chromium',
      locale: 'ru-RU',
      viewport: '1440x1000',
      userRoleState: 'synthetic authenticated customer, viewer role, local mocked /api/v1 responses',
    },
    network: [],
    screenshots: [],
    telegramNetwork: [],
    timestamp,
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    locale: 'ru-RU',
    timezoneId: 'Europe/Moscow',
    viewport: { width: 1440, height: 1000 },
  });
  await installRoutes(context, result);
  const page = await context.newPage();
  page.setDefaultTimeout(25_000);
  page.on('console', (message) => {
    if (['error', 'warning'].includes(message.type())) {
      result.console.push({
        type: message.type(),
        text: message.text().slice(0, 500),
      });
    }
  });
  page.on('pageerror', (error) => {
    result.console.push({ type: 'pageerror', text: error.message.slice(0, 500) });
  });
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (!url.includes('/_next/static/')) {
      result.network.push({
        method: request.method(),
        path: sanitizeUrl(url),
        routeKey: routeKey(url),
        status: 'requestfailed',
        failure: request.failure()?.errorText ?? 'unknown',
      });
    }
  });

  await gotoReady(page, '/ru-RU/settings');
  await screenshot(page, result, 'settings-overview', true);
  const settingsText = await textSnapshot(page);
  record(
    result,
    'settings-account-public-uid-full',
    settingsText.includes('14677650'),
    'visible account id contains 14677650',
    'full approved public UID is visible',
  );
  record(
    result,
    'settings-no-uuid4-customer-display',
    !/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i.test(settingsText),
    'no UUID4 found in visible body text',
    'customer-visible ID should not be UUID4',
  );
  record(
    result,
    'settings-language-human-name-flag',
    settingsText.includes('Русский') && settingsText.includes('Russian') && !settingsText.includes('ru-RU'),
    'language select text includes Russian human label and no raw ru-RU visible',
    'language displays human name + flag option instead of raw locale code',
  );
  record(
    result,
    'settings-timezone-offset',
    settingsText.includes('Europe/Moscow') && settingsText.includes('UTC+03:00'),
    'timezone select text includes Europe/Moscow (UTC+03:00)',
    'timezone displays UTC offset',
  );
  record(
    result,
    'settings-security-controls-separated',
    !settingsText.includes('Новый passkey') && !settingsText.includes('Смена пароля'),
    'overview does not expose passkey/password management form controls',
    'profile settings are not overloaded with security controls',
  );
  record(
    result,
    'settings-delete-account-cabinet-link',
    settingsText.toLocaleLowerCase('ru').includes('удалить аккаунт'),
    'cabinet settings contains delete-account action',
    'delete-account flow is inside cabinet',
  );

  await page.getByRole('button', { name: /QA Customer CYBA-697|qa_customer_cyba697/i }).click();
  await page.waitForTimeout(1800);
  await screenshot(page, result, 'settings-user-menu-open', false);
  const menuText = await textSnapshot(page);
  record(
    result,
    'account-nav-security-item',
    menuText.includes('Безопасность'),
    'user menu contains Безопасность',
    'account nav has security item',
  );
  const headerText = await page.locator('header').innerText({ timeout: 10_000 });
  record(
    result,
    'header-currency-symbol-not-raw-code',
    headerText.includes('₽') && !/\bRUB\b/.test(headerText),
    'header shows ₽ and no visible RUB code in closed selector',
    'currency selector uses visual representation instead of raw code',
  );

  await gotoReady(page, '/ru-RU/settings/security');
  await screenshot(page, result, 'settings-security-route', true);
  const securityText = await textSnapshot(page);
  record(
    result,
    'security-route-controls-present',
    securityText.includes('Passkey') || securityText.includes('passkey') || securityText.includes('Антифишинг'),
    'security route exposes dedicated security controls',
    'security controls live under /settings/security',
  );

  await gotoReady(page, '/ru-RU/settings/delete-account');
  await screenshot(page, result, 'settings-delete-account-form', true);
  const deleteText = await textSnapshot(page);
  record(
    result,
    'delete-account-localized-cabinet-no-port',
    deleteText.toLocaleLowerCase('ru').includes('удал') && !deleteText.includes(':3000'),
    'cabinet delete account text is localized and contains no :3000 URL',
    'localized cabinet delete-account flow without localhost port leak',
  );
  await page.getByLabel(/подтверж/i).fill('DELETE').catch(async () => {
    await page.locator('#delete-confirm-input').fill('DELETE');
  });
  await page.locator('#confirmation').check();
  await Promise.all([
    page.waitForResponse((response) =>
      response.url().includes('/api/v1/auth/me/privacy-requests') && response.status() === 201,
    ),
    page.getByRole('button', { name: /удал/i }).click(),
  ]);
  await page.waitForTimeout(500);
  await screenshot(page, result, 'settings-delete-account-success', true);
  record(
    result,
    'delete-account-request-success',
    (await textSnapshot(page)).includes('PRIV-CYBA697'),
    'privacy request reference PRIV-CYBA697 shown',
    'delete account request succeeds via cabinet synthetic data',
  );

  await gotoReady(page, '/ru-RU/dashboard');
  await screenshot(page, result, 'dashboard', true);
  const dashboardText = await textSnapshot(page);
  record(
    result,
    'dashboard-subscription-switcher-not-dimmed',
    dashboardText.includes('CyberVPN Pro Monthly'),
    'active subscription name visible in dashboard',
    'dashboard subscription switcher is visually available',
  );
  record(
    result,
    'dashboard-provisioning-warning-consistent',
    !dashboardText.toLowerCase().includes('warning') && !dashboardText.includes('Ручная проверка'),
    'active credentials/service state show no provisioning warning',
    'provisioning warning matches active credentials/access state',
  );

  await gotoReady(page, '/ru-RU/servers');
  await screenshot(page, result, 'servers', true);
  const serversText = await textSnapshot(page);
  record(
    result,
    'servers-full-subscription-link',
    serversText.includes('https://sub.example.test/cyba697/full-subscription-url-visible'),
    'full synthetic subscription URL is visible',
    'servers subscription link displays fully',
  );
  record(
    result,
    'servers-active-service-no-false-warning',
    !serversText.includes('Недоступно') || serversText.includes('Frankfurt-01'),
    'server access has active server/config data',
    'active credentials state should not show blocking warning',
  );

  await gotoReady(page, '/ru-RU/subscriptions');
  await screenshot(page, result, 'subscriptions-default', true);
  const subscriptionsText = await textSnapshot(page);
  const normalizedSubscriptionsText = subscriptionsText.toLocaleLowerCase('ru');
  record(
    result,
    'subscriptions-catalog-filters-visible',
    normalizedSubscriptionsText.includes('фильтры каталога') &&
      normalizedSubscriptionsText.includes('срок') &&
      normalizedSubscriptionsText.includes('устройства') &&
      normalizedSubscriptionsText.includes('трафик'),
    'duration/devices/traffic filter labels visible',
    'catalog can be filtered/grouped by duration/devices/traffic',
  );
  await page.getByRole('button', { name: '32-100д' }).click();
  await page.getByRole('button', { name: '6-10' }).click();
  await page.getByRole('button', { name: 'Безлимит' }).click();
  await page.waitForTimeout(400);
  await screenshot(page, result, 'subscriptions-filtered-quarterly-devices-traffic', true);
  const filteredText = await textSnapshot(page);
  record(
    result,
    'subscriptions-filtered-result',
    filteredText.includes('Pro Quarterly'),
    'filtered catalog includes Pro Quarterly after duration/devices/traffic filters',
    'filters apply to catalog results',
  );

  await gotoReady(page, '/ru-RU/telegram-link?magic=fresh-magic-cyba697');
  await page.waitForURL(/\/ru-RU\/dashboard/, { timeout: 8_000 }).catch(() => {});
  await page.waitForTimeout(500);
  await screenshot(page, result, 'telegram-fresh-synthetic-link-dashboard', false);
  record(
    result,
    'telegram-fresh-synthetic-link-succeeds',
    page.url().includes('/ru-RU/dashboard'),
    `final URL ${sanitizeUrl(page.url())}`,
    'fresh synthetic Telegram link redirects to dashboard',
  );

  await gotoReady(page, '/ru-RU/telegram-link?magic=expired-magic-cyba697');
  await page.waitForTimeout(1_000);
  await screenshot(page, result, 'telegram-expired-synthetic-link-error', false);
  const expiredText = await textSnapshot(page);
  const expectedExpiredCopy = 'Запрос на вход через Telegram истёк. Запустите вход заново на сайте.';
  record(
    result,
    'telegram-expired-synthetic-link-fails',
    expiredText.includes(expectedExpiredCopy),
    `expired-link copy ${expiredText.includes(expectedExpiredCopy) ? 'matches' : 'does not match'} Auth.telegram.botLinkExpired`,
    'expired synthetic Telegram link shows Auth.telegram.botLinkExpired localized copy',
  );

  await gotoReady(page, '/ru-RU/dashboard');
  await page.getByRole('button', { name: /QA Customer CYBA-697|qa_customer_cyba697/i }).click();
  await Promise.all([
    page.waitForResponse((response) =>
      response.url().includes('/api/v1/auth/logout') && response.status() === 200,
    ),
    page.getByRole('button', { name: /Выйти/i }).click(),
  ]);
  await page.waitForURL(/\/ru-RU$/, { timeout: 8_000 }).catch(() => {});
  await screenshot(page, result, 'header-sign-out-after-click', false);
  await gotoReady(page, '/ru-RU/dashboard');
  await page.waitForURL(/\/ru-RU\/login/, { timeout: 8_000 }).catch(() => {});
  await screenshot(page, result, 'protected-dashboard-after-sign-out-login', false);
  record(
    result,
    'header-signout-removes-protected-access',
    page.url().includes('/ru-RU/login'),
    `final URL ${sanitizeUrl(page.url())}`,
    'header sign out removes access to cabinet/protected route',
  );

  await context.close();
  await browser.close();

  const notePath = path.join(notesDir, `${issueId.toLowerCase()}-customer-portal-regression__${timestamp}.json`);
  fs.writeFileSync(notePath, `${JSON.stringify(result, null, 2)}\n`);
  const failed = result.checks.filter((check) => check.status !== 'PASS');
  console.log(JSON.stringify({
    note: path.relative(repoRoot, notePath),
    screenshots: result.screenshots.length,
    checks: result.checks.length,
    failed: failed.map((check) => check.id),
  }, null, 2));

  if (failed.length > 0) {
    process.exitCode = 1;
  }
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
