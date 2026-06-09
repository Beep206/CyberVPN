import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import playwright from '/home/beep/.local/lib/node_modules/playwright/index.js';

const { chromium } = playwright;

const baseUrl = process.env.CYBA608_BASE_URL ?? 'http://127.0.0.1:9001';
const outDir = 'evidence/client/cyba-608';
const screenshotDir = path.join(outDir, 'screenshots');
const networkDir = path.join(outDir, 'network');
const nowIso = new Date().toISOString();

await mkdir(screenshotDir, { recursive: true });
await mkdir(networkDir, { recursive: true });

const qaUser = {
  id: 'qa-user-cyba-608',
  email: 'qa-device-user@example.test',
  login: 'qa_device_user',
  role: 'user',
  is_active: true,
  is_email_verified: true,
  created_at: '2026-06-09T00:00:00.000Z',
};

const uaChromeLinux =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36';
const uaFirefoxLinux =
  'Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0';
const uaSafariMobile =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.0 Mobile/15E148 Safari/604.1';

const deviceFixtures = {
  repeatedSameBrowserDeduped: {
    devices: [
      {
        device_id: 'stable-browser-device-1',
        ip_address: '203.0.113.10',
        user_agent: uaChromeLinux,
        last_used_at: '2026-06-09T18:10:00.000Z',
        created_at: '2026-06-09T17:00:00.000Z',
        is_current: true,
      },
    ],
    total: 1,
    total_devices: 1,
    device_limit: 3,
    remaining_devices: 2,
  },
  withOtherDevices: {
    devices: [
      {
        device_id: 'stable-browser-device-1',
        ip_address: '203.0.113.10',
        user_agent: uaChromeLinux,
        last_used_at: '2026-06-09T18:20:00.000Z',
        created_at: '2026-06-09T17:00:00.000Z',
        is_current: true,
      },
      {
        device_id: 'stable-browser-device-2',
        ip_address: '198.51.100.22',
        user_agent: uaFirefoxLinux,
        last_used_at: '2026-06-09T17:55:00.000Z',
        created_at: '2026-06-08T11:00:00.000Z',
        is_current: false,
      },
      {
        device_id: 'stable-browser-device-3',
        ip_address: '192.0.2.44',
        user_agent: uaSafariMobile,
        last_used_at: '2026-06-09T17:40:00.000Z',
        created_at: '2026-06-07T09:30:00.000Z',
        is_current: false,
      },
    ],
    total: 3,
    total_devices: 3,
    device_limit: 3,
    remaining_devices: 0,
  },
};

let activeDevices = deviceFixtures.repeatedSameBrowserDeduped;
let logoutOthersCalls = 0;
let singleDeviceDeleteCalls = 0;
const network = [];
const consoleMessages = [];
const pageErrors = [];

function allNotificationPreferences(value = false) {
  return {
    account_email: value,
    account_telegram: value,
    payment_email: value,
    payment_telegram: value,
    subscription_email: value,
    subscription_telegram: value,
    vpn_email: value,
    vpn_telegram: value,
    growth_in_app_invites: value,
    growth_email_invites: value,
    growth_telegram_invites: value,
    growth_in_app_referral_rewards: value,
    growth_email_referral_rewards: value,
    growth_telegram_referral_rewards: value,
    growth_in_app_gifts: value,
    growth_email_gifts: value,
    growth_telegram_gifts: value,
    growth_in_app_admin_updates: value,
    growth_email_admin_updates: value,
    growth_telegram_admin_updates: value,
  };
}

function customerSubscriptionsResponse() {
  return {
    customer_account_id: 'qa-account-cyba-608',
    auth_realm_id: 'qa-realm-cyba-608',
    selected_subscription_key: 'qa-subscription-1',
    default_subscription_key: 'qa-subscription-1',
    items: [
      {
        subscription_key: 'qa-subscription-1',
        kind: 'entitlement_grant',
        status: 'active',
        display_name: 'QA Device Plan',
        plan_uuid: 'qa-plan-device',
        plan_code: 'qa-device',
        source_type: 'qa_fixture',
        source_order_id: null,
        entitlement_grant_id: 'qa-grant-device',
        service_identity_id: null,
        provider_name: 'remnawave',
        expires_at: '2026-07-09T00:00:00.000Z',
        created_at: '2026-06-09T00:00:00.000Z',
        effective_entitlements: {
          max_devices_per_user: 99,
          devices_included: 99,
          display_traffic_label: 'QA traffic',
        },
        invite_bundle: {},
        is_trial: false,
        addons: [],
        can_manage: true,
        can_deliver_config: false,
        management_scope: 'subscription_entitlement',
      },
    ],
    limitations: [],
  };
}

function entitlementResponse() {
  return {
    status: 'active',
    plan_uuid: 'qa-plan-device',
    plan_code: 'qa-device',
    display_name: 'QA Device Plan',
    period_days: 30,
    expires_at: '2026-07-09T00:00:00.000Z',
    effective_entitlements: {
      max_devices_per_user: 99,
      devices_included: 99,
      display_traffic_label: 'QA traffic',
    },
    invite_bundle: {},
    is_trial: false,
    addons: [],
  };
}

function clientCapabilitiesResponse() {
  return {
    auth: {
      email_password: true,
      magic_link: true,
      telegram: true,
    },
    payments: {
      web_checkout: false,
      telegram_stars: false,
      cryptobot: false,
      manual_invoice: false,
      autorenewal: false,
    },
    growth: {
      invites: false,
      referral: false,
      promo_codes: false,
      gift_codes: false,
      checkout_code_discounts: false,
      growth_hub: false,
    },
    subscriptions: {
      multi_subscription: true,
      selected_subscription_required: false,
      addons: false,
      upgrade: false,
      trial: false,
      paid_provisioning: false,
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
  };
}

async function fulfill(route, status, json, label) {
  const request = route.request();
  const url = new URL(request.url());
  network.push({
    method: request.method(),
    path: url.pathname,
    status,
    label,
  });
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(json),
  });
}

async function fulfillText(route, status, body, contentType, label) {
  const request = route.request();
  const url = new URL(request.url());
  network.push({
    method: request.method(),
    path: url.pathname,
    status,
    label,
  });
  await route.fulfill({
    status,
    contentType,
    body,
  });
}

function apiLabel(method, pathname) {
  return `${method} ${pathname.replace('/api/v1', '')}`;
}

async function handleApi(route) {
  const request = route.request();
  const url = new URL(request.url());
  const method = request.method();
  const pathname = url.pathname;
  const label = apiLabel(method, pathname);

  if (method === 'GET' && (pathname === '/api/v1/auth/session' || pathname === '/api/v1/auth/me')) {
    return fulfill(route, 200, qaUser, label);
  }
  if (method === 'GET' && pathname === '/api/v1/users/me/profile') {
    return fulfill(route, 200, {
      id: qaUser.id,
      email: qaUser.email,
      display_name: 'QA Device User',
      language: 'en-EN',
      timezone: 'UTC',
      updated_at: '2026-06-09T18:00:00.000Z',
    }, label);
  }
  if (method === 'GET' && pathname === '/api/v1/users/me/notifications') {
    return fulfill(route, 200, allNotificationPreferences(true), label);
  }
  if (method === 'GET' && pathname === '/api/v1/growth-notifications/preferences') {
    return fulfill(route, 200, allNotificationPreferences(false), label);
  }
  if (method === 'GET' && pathname === '/api/v1/2fa/status') {
    return fulfill(route, 200, { status: 'disabled' }, label);
  }
  if (method === 'GET' && pathname === '/api/v1/security/antiphishing') {
    return fulfill(route, 200, { code: null }, label);
  }
  if (method === 'GET' && pathname === '/api/v1/auth/passkeys/policy') {
    return fulfill(route, 200, {
      enabled: false,
      surface: 'customer',
      realm_key: 'customer',
      rp_id: '127.0.0.1',
      rp_name: 'CyberVPN QA',
      allowedOrigins: [baseUrl],
      conditionalUiEnabled: false,
      registrationEnabled: false,
      authenticationEnabled: false,
      reauthenticationEnabled: false,
      adminCountsAsMfa: false,
      challengeTtlSeconds: 60,
      browserTimeoutMs: 60000,
    }, label);
  }
  if (method === 'GET' && pathname === '/api/v1/auth/passkeys') {
    return fulfill(route, 200, { credentials: [] }, label);
  }
  if (method === 'GET' && pathname === '/api/v1/client/capabilities') {
    return fulfill(route, 200, clientCapabilitiesResponse(), label);
  }
  if (method === 'GET' && pathname === '/api/v1/me/realtime/sse') {
    return fulfillText(route, 200, ': cyba-608 synthetic stream\n\n', 'text/event-stream', label);
  }
  if (method === 'GET' && pathname === '/api/v1/me/realtime/sync') {
    return fulfill(route, 200, { events: [], cursor: null }, label);
  }
  if (method === 'GET' && pathname === '/api/v1/me/conversations') {
    return fulfill(route, 200, { items: [] }, label);
  }
  if (method === 'GET' && pathname === '/api/v1/me/notifications') {
    return fulfill(route, 200, { items: [], unread_count: 0 }, label);
  }
  if (method === 'GET' && pathname === '/api/v1/auth/devices') {
    return fulfill(route, 200, activeDevices, label);
  }
  if (method === 'POST' && pathname === '/api/v1/auth/devices/logout-others') {
    logoutOthersCalls += 1;
    activeDevices = deviceFixtures.repeatedSameBrowserDeduped;
    return fulfill(route, 200, {
      message: 'Other device sessions terminated',
      sessions_revoked: 2,
    }, label);
  }
  if (method === 'DELETE' && pathname.startsWith('/api/v1/auth/devices/')) {
    singleDeviceDeleteCalls += 1;
    return fulfill(route, 200, {
      message: 'Device revoked',
      device_id: pathname.split('/').at(-1),
    }, label);
  }
  if (method === 'GET' && pathname.startsWith('/api/v1/customer-subscriptions')) {
    if (pathname.endsWith('/entitlements')) {
      return fulfill(route, 200, entitlementResponse(), label);
    }
    return fulfill(route, 200, customerSubscriptionsResponse(), label);
  }
  if (method === 'GET' && pathname === '/api/v1/entitlements/current') {
    return fulfill(route, 200, entitlementResponse(), label);
  }

  return fulfill(route, 200, {}, `${label} fallback-empty`);
}

async function textCount(locator, text) {
  return locator.getByText(text, { exact: true }).count();
}

async function waitForText(locator, text) {
  await locator.getByText(text, { exact: true }).first().waitFor({ timeout: 20000 });
}

async function getDevicePanelSnapshot(page, currentLabel) {
  const devicesPanel = page.locator('article#devices');
  await devicesPanel.scrollIntoViewIfNeeded();
  const text = await devicesPanel.innerText();
  return {
    currentBadgeCount: await textCount(devicesPanel, currentLabel),
    revokeButtonCount: await devicesPanel.getByRole('button', { name: /revoke|отозвать/i }).count(),
    text,
  };
}

const browser = await chromium.launch({
  headless: true,
  executablePath: '/home/beep/.local/bin/chromium',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});

const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  deviceScaleFactor: 1,
});
await context.addCookies([{ name: 'DEV_BYPASS_AUTH', value: 'true', url: baseUrl }]);
await context.addInitScript(() => {
  window.localStorage.setItem('USER_ROLE', 'user');
});

const page = await context.newPage();
page.on('console', (message) => {
  const type = message.type();
  if (type === 'error' || type === 'warning') {
    consoleMessages.push({ type, text: message.text().slice(0, 500) });
  }
});
page.on('pageerror', (error) => {
  pageErrors.push(error.message.slice(0, 500));
});
await page.route('**/api/v1/**', handleApi);

await page.goto(`${baseUrl}/en-EN/settings`, { waitUntil: 'domcontentloaded' });
await waitForText(page.locator('article#devices'), 'Active devices');
await waitForText(page.locator('article#devices'), '1 of 3');
const initialPanel = await getDevicePanelSnapshot(page, 'Current');
await page.locator('article#devices').screenshot({
  path: path.join(screenshotDir, 'settings-devices-deduped-en-desktop.png'),
});

activeDevices = deviceFixtures.withOtherDevices;
await page.reload({ waitUntil: 'domcontentloaded' });
await waitForText(page.locator('article#devices'), '3 of 3');
const beforeLogoutPanel = await getDevicePanelSnapshot(page, 'Current');
await page.locator('article#devices').screenshot({
  path: path.join(screenshotDir, 'settings-devices-before-logout-others-en-desktop.png'),
});

await page.locator('article#devices').getByRole('button', { name: /Revoke others/i }).click();
await waitForText(page.locator('body'), '2 devices revoked.');
await waitForText(page.locator('article#devices'), '1 of 3');
const afterLogoutPanel = await getDevicePanelSnapshot(page, 'Current');
await page.locator('article#devices').screenshot({
  path: path.join(screenshotDir, 'settings-devices-after-logout-others-en-desktop.png'),
});

const mobilePage = await context.newPage();
await mobilePage.setViewportSize({ width: 390, height: 844 });
await mobilePage.route('**/api/v1/**', handleApi);
activeDevices = deviceFixtures.withOtherDevices;
await mobilePage.goto(`${baseUrl}/ru-RU/settings`, { waitUntil: 'domcontentloaded' });
await mobilePage.addStyleTag({
  content: `
    nextjs-portal,
    [data-nextjs-toast],
    [data-nextjs-dev-tools-button],
    [data-nextjs-dev-tools-panel] {
      display: none !important;
    }
  `,
});
await waitForText(mobilePage.locator('article#devices'), 'Активные устройства');
await waitForText(mobilePage.locator('article#devices'), '3 из 3');
const ruMobilePanel = await getDevicePanelSnapshot(mobilePage, 'Текущая');
await mobilePage.evaluate(() => {
  const panel = document.querySelector('article#devices');
  if (!panel) return;
  const absoluteTop = panel.getBoundingClientRect().top + window.scrollY;
  window.scrollTo(0, Math.max(0, absoluteTop - 78));
});
await mobilePage.screenshot({
  path: path.join(screenshotDir, 'settings-devices-ru-mobile.png'),
  fullPage: false,
});

const failures = [];
if (initialPanel.currentBadgeCount !== 1) {
  failures.push(`Expected one Current badge in deduped scenario, got ${initialPanel.currentBadgeCount}`);
}
if (!initialPanel.text.includes('1 of 3') || !initialPanel.text.includes('2')) {
  failures.push('Deduped scenario did not show backend total/remaining counters 1 of 3 / 2.');
}
if (beforeLogoutPanel.currentBadgeCount !== 1) {
  failures.push(`Expected one Current badge before logout-others, got ${beforeLogoutPanel.currentBadgeCount}`);
}
if (!beforeLogoutPanel.text.includes('3 of 3') || !beforeLogoutPanel.text.includes('0')) {
  failures.push('Before logout-others scenario did not show backend counters 3 of 3 / 0.');
}
if (logoutOthersCalls !== 1) {
  failures.push(`Expected one POST /auth/devices/logout-others call, got ${logoutOthersCalls}`);
}
if (singleDeviceDeleteCalls !== 0) {
  failures.push(`Expected no duplicate DELETE /auth/devices/{id} calls during logout-others, got ${singleDeviceDeleteCalls}`);
}
if (afterLogoutPanel.currentBadgeCount !== 1 || !afterLogoutPanel.text.includes('1 of 3')) {
  failures.push('After logout-others did not settle back to one current device with 1 of 3 counter.');
}
if (ruMobilePanel.currentBadgeCount !== 1 || !ruMobilePanel.text.includes('3 из 3')) {
  failures.push('Russian mobile smoke did not preserve one current badge and 3 из 3 counter.');
}

const summary = {
  issue: 'CYBA-608',
  timestamp: nowIso,
  baseUrl,
  environment: {
    browser: 'Chrome for Testing via global Playwright',
    desktopViewport: '1440x1000',
    mobileViewport: '390x844',
    locales: ['en-EN', 'ru-RU'],
    auth: 'DEV_BYPASS_AUTH=true synthetic user; no real cookies/JWT/passwords stored',
  },
  scenarios: {
    repeatedSameBrowserDeduped: {
      fixtureMeaning: 'Synthetic backend response representing 10 same-browser logins collapsed to one stable device.',
      expected: 'one row/current badge, active count 1, plan limit 3, remaining slots 2',
      currentBadgeCount: initialPanel.currentBadgeCount,
      visibleHasExpectedCounter: initialPanel.text.includes('1 of 3'),
      visibleHasRemainingSlots: initialPanel.text.includes('2'),
    },
    logoutOthers: {
      expected: 'one POST /auth/devices/logout-others, no per-device DELETE loop, current badge once',
      beforeCurrentBadgeCount: beforeLogoutPanel.currentBadgeCount,
      afterCurrentBadgeCount: afterLogoutPanel.currentBadgeCount,
      logoutOthersCalls,
      singleDeviceDeleteCalls,
      visiblePostLogoutBanner: afterLogoutPanel.text.includes('1 of 3'),
    },
    ruMobile: {
      expected: 'mobile ru-RU device panel renders without overlap-critical failure and current badge once',
      currentBadgeCount: ruMobilePanel.currentBadgeCount,
      visibleHasExpectedCounter: ruMobilePanel.text.includes('3 из 3'),
    },
  },
  screenshots: [
    'evidence/client/cyba-608/screenshots/settings-devices-deduped-en-desktop.png',
    'evidence/client/cyba-608/screenshots/settings-devices-before-logout-others-en-desktop.png',
    'evidence/client/cyba-608/screenshots/settings-devices-after-logout-others-en-desktop.png',
    'evidence/client/cyba-608/screenshots/settings-devices-ru-mobile.png',
  ],
  network,
  consoleMessages,
  pageErrors,
  failures,
};

await writeFile(
  path.join(networkDir, 'settings-device-browser-qa-summary.json'),
  `${JSON.stringify(summary, null, 2)}\n`,
);

await browser.close();

if (failures.length > 0) {
  console.error(failures.join('\n'));
  process.exit(1);
}

console.log(JSON.stringify({
  issue: summary.issue,
  result: 'PASS',
  logoutOthersCalls,
  singleDeviceDeleteCalls,
  evidence: summary.screenshots.length + 1,
}, null, 2));
