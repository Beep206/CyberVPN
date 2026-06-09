import playwright from '/home/beep/.local/lib/node_modules/playwright/index.js';
import fs from 'node:fs';
import path from 'node:path';

const { chromium } = playwright;
const issue = 'CYBA-610';
const baseUrl = process.env.CYBA_610_PARTNER_URL ?? 'http://127.0.0.1:3002';
const evidenceDir = 'evidence/partner/CYBA-610';
const screenshotDir = path.join(evidenceDir, 'screenshots');
const summaryPath = path.join(evidenceDir, 'playwright-security-sessions-summary.json');

fs.mkdirSync(screenshotDir, { recursive: true });

const now = '2026-06-09T19:00:00Z';
const workspaceId = '10000000-0000-4000-8000-000000000001';
const permissionKeys = [
  'workspace_read',
  'membership_read',
];
const principal = {
  audience: 'cybervpn:partner',
  auth_realm_id: '10000000-0000-4000-8000-000000000901',
  auth_realm_key: 'partner',
  email: 'partner.security.fixture@example.invalid',
  id: '10000000-0000-4000-8000-000000000202',
  is_active: true,
  is_email_verified: true,
  login: 'partner.security.fixture',
  principal_type: 'partner_operator',
  role: 'admin',
  scope_family: 'partner',
};

const workspace = {
  account_key: 'safe-security-lab',
  active_code_count: 0,
  code_count: 0,
  created_by_admin_user_id: principal.id,
  current_permission_keys: permissionKeys,
  current_role_key: 'owner',
  display_name: 'Safe Security Sessions Lab',
  id: workspaceId,
  last_activity_at: now,
  legacy_owner_user_id: null,
  members: [],
  status: 'active',
  total_clients: 0,
  total_earned: 0,
};

const bootstrap = {
  active_workspace: workspace,
  active_workspace_id: workspaceId,
  blocked_reasons: [],
  compliance_readiness: 'clear',
  counters: { open_cases: 0, pending_tasks: 0, unread_notifications: 0 },
  current_permission_keys: permissionKeys,
  finance_readiness: 'ready',
  governance_state: 'clear',
  pending_tasks: [],
  principal,
  programs: {
    canonical_source: 'safe_fixture_partner_security_sessions',
    lane_memberships: [],
    primary_lane_key: 'creator_affiliate',
    readiness_items: [],
    updated_at: now,
  },
  release_ring: 'R4',
  technical_readiness: 'ready',
  updated_at: now,
  workspace_resolution: 'selected',
  workspaces: [workspace],
};

const initialDevices = [
  {
    created_at: '2026-06-09T17:30:00Z',
    device_id: 'dev_current_desktop',
    ip_address: '203.0.113.10',
    is_current: true,
    last_used_at: now,
    user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit Safari',
  },
  {
    created_at: '2026-06-08T12:00:00Z',
    device_id: 'dev_remote_android',
    ip_address: '198.51.100.77',
    is_current: false,
    last_used_at: '2026-06-09T18:50:00Z',
    user_agent: 'Mozilla/5.0 (Linux; Android 14) AppleWebKit Chrome Mobile',
  },
  {
    created_at: '2026-06-07T09:15:00Z',
    device_id: 'dev_remote_windows',
    ip_address: '192.0.2.44',
    is_current: false,
    last_used_at: '2026-06-09T16:25:00Z',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit Chrome',
  },
];

let devices = initialDevices.map((device) => ({ ...device }));
const apiHits = [];
const mutations = [];
const consoleMessages = [];
const pageErrors = [];
const failedResponses = [];

function deviceListPayload() {
  return {
    device_limit: 5,
    devices,
    remaining_devices: Math.max(5 - devices.length, 0),
    total: devices.length,
    total_devices: devices.length,
  };
}

function sanitizeUrl(url) {
  const parsed = new URL(url);
  return `${parsed.pathname}${parsed.search}`;
}

async function fulfillJson(route, status, json) {
  await route.fulfill({
    body: JSON.stringify(json),
    contentType: 'application/json',
    status,
  });
}

async function waitForText(page, text, timeout = 10000) {
  await page.getByText(text, { exact: false }).first().waitFor({ timeout });
}

function normalizeText(value) {
  return value.replace(/\s+/g, ' ').trim().toLocaleUpperCase('en-US');
}

function containsText(bodyText, expected) {
  return normalizeText(bodyText).includes(normalizeText(expected));
}

async function screenshot(page, name, status, options = {}) {
  const filePath = path.join(
    screenshotDir,
    `${issue}__partner-security-sessions__safe-fixture__en-EN__desktop-1440__${name}__${status}__20260609.png`,
  );
  await page.screenshot({ fullPage: options.fullPage ?? true, path: filePath, timeout: 15000 });
  return filePath;
}

async function clickDialogConfirm(page, dialogTitle, confirmLabel) {
  const dialog = page.getByRole('dialog', { name: dialogTitle });
  await dialog.waitFor({ timeout: 10000 });
  const confirmButton = dialog.getByRole('button', { name: confirmLabel });
  await confirmButton.click();
  await page.waitForTimeout(40);
  await confirmButton.click().catch(() => {});
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { height: 1000, width: 1440 } });

await context.addInitScript(() => {
  document.cookie = 'DEV_BYPASS_AUTH=true; path=/';
  window.localStorage.setItem('USER_ROLE', 'partner_operator');
});

await context.route('**/api/analytics/**', async (route) => {
  const request = route.request();
  apiHits.push({ method: request.method(), path: sanitizeUrl(request.url()), status: 202 });
  await fulfillJson(route, 202, { accepted: true, fixture: 'CYBA-610 telemetry sink' });
});

await context.route('**/api/v1/**', async (route) => {
  const request = route.request();
  const parsed = new URL(request.url());
  const method = request.method();
  const pathWithSearch = `${parsed.pathname}${parsed.search}`;

  async function record(status, json) {
    apiHits.push({ method, path: pathWithSearch, status });
    await fulfillJson(route, status, json);
  }

  if (method === 'GET' && parsed.pathname === '/api/v1/auth/session') {
    await record(200, principal);
    return;
  }

  if (method === 'GET' && parsed.pathname === '/api/v1/partner-workspaces/me') {
    await record(200, [workspace]);
    return;
  }

  if (method === 'GET' && parsed.pathname === '/api/v1/partner-session/bootstrap') {
    await record(200, bootstrap);
    return;
  }

  if (method === 'GET' && parsed.pathname === '/api/v1/auth/devices') {
    await record(200, deviceListPayload());
    return;
  }

  if (method === 'DELETE' && parsed.pathname.startsWith('/api/v1/auth/devices/')) {
    const deviceId = decodeURIComponent(parsed.pathname.split('/').at(-1));
    mutations.push({ deviceId, method, operation: 'revoke-device' });
    await new Promise((resolve) => setTimeout(resolve, 220));

    const before = devices.length;
    devices = devices.filter((device) => device.device_id !== deviceId);
    if (devices.length === before) {
      await record(404, { detail: 'Device not found in CYBA-610 fixture' });
      return;
    }

    await record(200, {
      device_id: deviceId,
      message: 'Device session revoked successfully',
    });
    return;
  }

  if (method === 'POST' && parsed.pathname === '/api/v1/auth/devices/logout-others') {
    const remoteCount = devices.filter((device) => !device.is_current).length;
    mutations.push({ method, operation: 'logout-others', sessions_revoked: remoteCount });
    await new Promise((resolve) => setTimeout(resolve, 220));
    devices = devices.filter((device) => device.is_current);
    await record(200, { sessions_revoked: remoteCount });
    return;
  }

  if (method === 'POST' && parsed.pathname === '/api/v1/auth/logout-all') {
    const sessionCount = devices.length;
    mutations.push({ method, operation: 'logout-all', sessions_revoked: sessionCount });
    await new Promise((resolve) => setTimeout(resolve, 220));
    devices = [];
    await record(200, {
      message: 'All sessions terminated',
      sessions_revoked: sessionCount,
    });
    return;
  }

  await record(404, { detail: `No CYBA-610 mock for ${method} ${parsed.pathname}` });
});

const page = await context.newPage();
page.on('console', (message) => {
  if (message.type() === 'error') {
    consoleMessages.push({ text: message.text().slice(0, 1000), type: message.type() });
  }
});
page.on('pageerror', (error) => {
  pageErrors.push({ message: error.message, stack: String(error.stack ?? '').slice(0, 1500) });
});
page.on('response', (response) => {
  if (response.status() >= 400) {
    const request = response.request();
    failedResponses.push({
      method: request.method(),
      resourceType: request.resourceType(),
      status: response.status(),
      url: sanitizeUrl(response.url()),
    });
  }
});

const results = [];
const routePath = '/en-EN/security/sessions';
let routeReachable = false;

await page.goto(`${baseUrl}${routePath}`, {
  timeout: 30000,
  waitUntil: 'domcontentloaded',
});
await waitForText(page, 'Sessions Console', 20000).catch(() => {});
await waitForText(page, '198.51.100.77', 20000).catch(() => {});

const initialBodyText = (await page.textContent('body')) ?? '';
routeReachable =
  containsText(initialBodyText, 'Sessions Console')
  && containsText(initialBodyText, '203.0.113.10')
  && containsText(initialBodyText, '198.51.100.77')
  && containsText(initialBodyText, '192.0.2.44');

const initialScreenshot = await screenshot(page, 'initial', routeReachable ? 'pass' : 'fail');
const currentDeviceBadgeCount = await page.getByText('Current device', { exact: true }).count().catch(() => 0);
const remoteLogoutButtonCount = await page.getByRole('button', { name: 'Logout device' }).count().catch(() => 0);

results.push({
  bodyTextSample: initialBodyText.replace(/\s+/g, ' ').trim().slice(0, 2400),
  currentDeviceBadgeCount,
  expectedText: [
    'Sessions Console',
    'Safari on macOS',
    'Chrome on Android',
    'Chrome on Windows',
    '203.0.113.10',
    '198.51.100.77',
    '192.0.2.44',
    '3/5',
  ],
  missingExpectedText: [
    'Sessions Console',
    'Safari on macOS',
    'Chrome on Android',
    'Chrome on Windows',
    '203.0.113.10',
    '198.51.100.77',
    '192.0.2.44',
    '3/5',
  ]
    .filter((expected) => !containsText(initialBodyText, expected)),
  name: 'initial-render',
  path: routePath,
  remoteLogoutButtonCount,
  routeReachable,
  screenshot: initialScreenshot,
});

if (routeReachable) {
  await page.getByRole('button', { name: 'Logout device' }).first().click();
  await clickDialogConfirm(page, 'Revoke device sessions', 'Logout device');
  await waitForText(page, 'Device session revoked successfully');
  await waitForText(page, '192.0.2.44');
  const afterRevokeBodyText = (await page.textContent('body')) ?? '';
  const revokeScreenshot = await screenshot(page, 'after-revoke-device', 'pass');
  results.push({
    name: 'revoke-selected-device',
    path: routePath,
    selectedDeviceAbsent: !containsText(afterRevokeBodyText, '198.51.100.77'),
    untouchedRemotePresent: containsText(afterRevokeBodyText, '192.0.2.44'),
    mutationCount: mutations.filter((item) => item.operation === 'revoke-device').length,
    mutationDeviceIds: mutations
      .filter((item) => item.operation === 'revoke-device')
      .map((item) => item.deviceId),
    screenshot: revokeScreenshot,
  });

  await page.getByRole('button', { name: 'Logout others' }).first().click();
  await clickDialogConfirm(page, 'Logout other devices', 'Logout others');
  await waitForText(page, 'Revoked 1 remote sessions.');
  const afterLogoutOthersBodyText = (await page.textContent('body')) ?? '';
  const logoutOthersScreenshot = await screenshot(page, 'after-logout-others', 'pass');
  results.push({
    currentDevicePresent: containsText(afterLogoutOthersBodyText, '203.0.113.10'),
    mutationCount: mutations.filter((item) => item.operation === 'logout-others').length,
    name: 'logout-others',
    path: routePath,
    remoteWindowsAbsent: !containsText(afterLogoutOthersBodyText, '192.0.2.44'),
    screenshot: logoutOthersScreenshot,
  });

  await page.getByRole('button', { name: 'Logout all' }).first().click();
  await clickDialogConfirm(page, 'Revoke all device sessions', 'Logout all');
  await page.waitForURL('**/en-EN/login', { timeout: 10000 }).catch(() => {});
  const logoutAllScreenshot = await screenshot(
    page,
    'after-logout-all',
    page.url().endsWith('/en-EN/login') ? 'pass' : 'fail',
    { fullPage: false },
  );
  results.push({
    loginRedirected: page.url().endsWith('/en-EN/login'),
    mutationCount: mutations.filter((item) => item.operation === 'logout-all').length,
    name: 'logout-all',
    path: routePath,
    screenshot: logoutAllScreenshot,
  });
}

await browser.close();

const pass =
  routeReachable
  && currentDeviceBadgeCount === 1
  && remoteLogoutButtonCount === 2
  && mutations.filter((item) => item.operation === 'revoke-device').length === 1
  && mutations.some((item) => item.operation === 'revoke-device' && item.deviceId === 'dev_remote_android')
  && mutations.filter((item) => item.operation === 'logout-others').length === 1
  && mutations.filter((item) => item.operation === 'logout-all').length === 1
  && results.every((item) => item.missingExpectedText === undefined || item.missingExpectedText.length === 0)
  && results.every((item) => item.selectedDeviceAbsent !== false)
  && results.every((item) => item.untouchedRemotePresent !== false)
  && results.every((item) => item.remoteWindowsAbsent !== false)
  && results.every((item) => item.currentDevicePresent !== false)
  && results.every((item) => item.loginRedirected !== false)
  && pageErrors.length === 0
  && failedResponses.length === 0
  && consoleMessages.length === 0;

const summary = {
  apiHits,
  assertionPolicy: 'Expected text matched against full normalized body text; bodyTextSample is truncated evidence only.',
  consoleMessages,
  environment: {
    app: 'partner',
    browser: 'Chromium via Playwright',
    locale: 'en-EN',
    mode: 'local Next dev + Playwright route mocks',
    url: baseUrl,
    viewport: '1440x1000',
  },
  failedResponses,
  fixture: {
    dataSafety: 'synthetic masked device fixture; no credentials, cookies, JWTs, refresh tokens, storageState, HAR, payment data, production PII, or Telegram initData stored',
    role: 'partner_operator',
  },
  issue,
  mutations,
  pageErrors,
  pass,
  results,
  timestamp: new Date().toISOString(),
};

fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`);
console.log(JSON.stringify({
  failedResponses,
  mutations,
  pageErrors,
  pass,
  results: results.map((item) => ({
    currentDeviceBadgeCount: item.currentDeviceBadgeCount,
    loginRedirected: item.loginRedirected,
    missingExpectedText: item.missingExpectedText,
    mutationCount: item.mutationCount,
    name: item.name,
    remoteLogoutButtonCount: item.remoteLogoutButtonCount,
    routeReachable: item.routeReachable,
    selectedDeviceAbsent: item.selectedDeviceAbsent,
  })),
}, null, 2));
