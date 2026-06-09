import playwright from '/home/beep/.local/lib/node_modules/playwright/index.js';
import fs from 'node:fs';

const { chromium } = playwright;
const baseUrl = process.env.CYBA_610_PARTNER_URL ?? 'http://127.0.0.1:3002';
const outputPath = 'evidence/partner/CYBA-610/runtime-error-probe-after-CYBA-619.json';

const events = {
  console: [],
  cdpExceptions: [],
  failedResponses: [],
  pageErrors: [],
  requests: [],
  status: null,
  url: `${baseUrl}/en-EN/security/sessions`,
};

function sanitizeUrl(rawUrl) {
  const parsed = new URL(rawUrl);
  return `${parsed.pathname}${parsed.search}`;
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { height: 900, width: 1440 } });
await context.addInitScript(() => {
  document.cookie = 'DEV_BYPASS_AUTH=true; path=/';
  window.localStorage.setItem('USER_ROLE', 'partner_operator');
});

await context.route('**/api/v1/**', async (route) => {
  const request = route.request();
  const parsed = new URL(request.url());
  events.requests.push({ method: request.method(), path: sanitizeUrl(request.url()) });

  if (parsed.pathname === '/api/v1/auth/session') {
    await route.fulfill({
      contentType: 'application/json',
      json: {
        audience: 'cybervpn:partner',
        auth_realm_key: 'partner',
        email: 'partner.security.fixture@example.invalid',
        id: '10000000-0000-4000-8000-000000000202',
        is_active: true,
        is_email_verified: true,
        login: 'partner.security.fixture',
        principal_type: 'partner_operator',
        role: 'admin',
      },
      status: 200,
    });
    return;
  }

  if (parsed.pathname === '/api/v1/auth/devices') {
    await route.fulfill({
      contentType: 'application/json',
      json: {
        device_limit: 5,
        devices: [],
        remaining_devices: 5,
        total: 0,
        total_devices: 0,
      },
      status: 200,
    });
    return;
  }

  await route.fulfill({
    contentType: 'application/json',
    json: { detail: `No CYBA-610 probe mock for ${parsed.pathname}` },
    status: 404,
  });
});

const page = await context.newPage();
const cdp = await context.newCDPSession(page);
await cdp.send('Runtime.enable');
cdp.on('Runtime.exceptionThrown', (event) => {
  const details = event.exceptionDetails;
  events.cdpExceptions.push({
    columnNumber: details.columnNumber,
    exception: details.exception?.description ?? details.exception?.value ?? null,
    lineNumber: details.lineNumber,
    scriptId: details.scriptId,
    text: details.text,
    url: details.url ? sanitizeUrl(details.url) : null,
  });
});

page.on('console', (message) => {
  events.console.push({
    location: message.location(),
    text: message.text().slice(0, 1000),
    type: message.type(),
  });
});
page.on('pageerror', (error) => {
  events.pageErrors.push({ message: error.message, stack: String(error.stack ?? '').slice(0, 1500) });
});
page.on('response', (response) => {
  if (response.status() >= 400) {
    events.failedResponses.push({
      method: response.request().method(),
      resourceType: response.request().resourceType(),
      status: response.status(),
      url: sanitizeUrl(response.url()),
    });
  }
});

const response = await page.goto(events.url, {
  timeout: 30000,
  waitUntil: 'domcontentloaded',
});
events.status = response?.status() ?? null;
await page.waitForTimeout(5000);
events.finalUrl = page.url();
events.bodyTextSample = ((await page.textContent('body')) ?? '').replace(/\s+/g, ' ').trim().slice(0, 1800);

await browser.close();

fs.writeFileSync(outputPath, `${JSON.stringify(events, null, 2)}\n`);
console.log(JSON.stringify({
  cdpExceptions: events.cdpExceptions,
  pageErrors: events.pageErrors,
  requests: events.requests,
  status: events.status,
}, null, 2));
