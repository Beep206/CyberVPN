import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const DEFAULT_OUTPUT = '.codex/local-runtime/ac18-critical-state-assertions-20260708.json';
const OUTPUT_PATH = readCliOption('output') || process.env.AC18_CRITICAL_STATE_OUTPUT || DEFAULT_OUTPUT;

const evidence = {
  frontendRoutes: readJson('.codex/local-runtime/ac18-frontend-live-api-critical-routes-followup2.json'),
  adminRoutes: readJson('.codex/local-runtime/ac18-admin-live-api-critical-routes.json'),
  partnerRoutes: readJson('.codex/local-runtime/ac18-partner-live-api-critical-routes.json'),
  frontendUserMenu: readJson('.codex/local-runtime/ac18-frontend-live-user-menu-logout-20260708.json'),
  adminUserMenu: readJson('.codex/local-runtime/ac18-admin-live-user-menu-logout-admin-localhost-20260708.json'),
  partnerUserMenu: readJson('.codex/local-runtime/ac18-partner-live-user-menu-logout-portal-20260708.json'),
  passkeyVirtualAuthenticator: readJson('.codex/local-runtime/ac18-frontend-passkey-virtual-authenticator-20260708.json'),
};

const checks = [];

routeCheck('frontend:customer dashboard session state', evidence.frontendRoutes, '/ru-RU/dashboard', {
  minBodyTextLength: 1000,
  minMenuTriggerCount: 1,
  h1Includes: ['Личный кабинет'],
  apiIncludes: [
    '/api/v1/auth/session',
    '/api/auth/optional-session',
    '/api/v1/client/capabilities',
    '/api/v1/wallet',
    '/api/v1/customer-subscriptions/',
    '/api/v1/trial/status',
    '/api/v1/access-delivery-channels/current/service-state',
  ],
});

routeCheck('frontend:customer subscription money state', evidence.frontendRoutes, '/ru-RU/subscriptions', {
  minBodyTextLength: 1000,
  minMenuTriggerCount: 1,
  h1Includes: ['УПРАВЛЕНИЕ ПОДПИСКОЙ'],
  apiIncludes: [
    '/api/v1/entitlements/current',
    '/api/v1/customer-subscriptions/',
    '/api/v1/plans/',
    '/api/v1/orders/',
    '/api/v1/trial/status',
  ],
});

routeCheck('frontend:customer wallet money state', evidence.frontendRoutes, '/ru-RU/wallet', {
  minBodyTextLength: 600,
  minMenuTriggerCount: 1,
  h1Includes: ['КОШЕЛЕК'],
  apiIncludes: [
    '/api/v1/wallet',
    '/api/v1/wallet/transactions',
    '/api/v1/payments/history',
    '/api/v1/customer-subscriptions/',
  ],
});

routeCheck('admin:security passkey policy/compliance state', evidence.adminRoutes, '/ru-RU/security/passkeys', {
  minBodyTextLength: 900,
  minMenuTriggerCount: 1,
  h1Includes: ['ключи доступа'],
  apiIncludes: [
    '/api/v1/auth/session',
    '/api/v1/security/passkeys/policy',
    '/api/v1/auth/passkeys',
    '/api/v1/security/passkeys/compliance',
  ],
});

routeCheck('admin:security session-device state', evidence.adminRoutes, '/ru-RU/security/sessions', {
  minBodyTextLength: 1000,
  minMenuTriggerCount: 1,
  h1Includes: ['Консоль сессий'],
  apiIncludes: [
    '/api/v1/auth/session',
    '/api/v1/auth/devices',
    '/api/v1/security/risk-reviews/queue',
  ],
});

routeCheck('admin:dashboard admin-state queues', evidence.adminRoutes, '/ru-RU/dashboard', {
  minBodyTextLength: 2000,
  minMenuTriggerCount: 1,
  h1Includes: ['КОМАНДНЫЙ ЦЕНТР'],
  apiIncludes: [
    '/api/v1/admin/withdrawals',
    '/api/v1/admin/privacy-requests/queue-count',
    '/api/v1/admin/support/tickets',
    '/api/v1/security/risk-reviews/queue',
    '/api/v1/admin/growth-signals/abuse-queue',
    '/api/v1/admin/webhook-log',
    '/api/v1/admin/audit-log',
    '/api/v1/admin/payment-attempts',
    '/api/v1/monitoring/stats',
    '/api/v1/servers/stats',
  ],
});

routeCheck('admin:pricebook money state', evidence.adminRoutes, '/ru-RU/commerce/pricebooks', {
  minBodyTextLength: 600,
  minMenuTriggerCount: 1,
  h1Includes: ['прайсбуками'],
  apiIncludes: [
    '/api/v1/auth/session',
    '/api/v1/offers/admin',
    '/api/v1/admin/withdrawals',
    '/api/v1/admin/support/tickets',
  ],
});

routeCheck('partner:finance money state', evidence.partnerRoutes, '/ru-RU/finance', {
  minBodyTextLength: 2000,
  minMenuTriggerCount: 1,
  h1Includes: ['Finance'],
  apiIncludes: [
    '/api/v1/auth/session',
    '/api/v1/partner-workspaces/me',
    '/finance-summary',
    '/payout-history',
    '/payout-accounts',
    '/statements',
    '/commercial-capabilities',
    '/eligibility',
  ],
});

routeCheck('partner:codes tracking state', evidence.partnerRoutes, '/ru-RU/codes', {
  minBodyTextLength: 800,
  minMenuTriggerCount: 1,
  h1Includes: ['Codes & Tracking'],
  apiIncludes: [
    '/api/v1/auth/session',
    '/api/v1/partner-session/bootstrap',
    '/finance-summary',
    '/campaign-assets',
    '/statements',
    '/payout-accounts',
    '/reseller-voucher-batches',
    '/analytics-metrics',
  ],
});

routeCheck('partner:conversions money state', evidence.partnerRoutes, '/ru-RU/conversions', {
  minBodyTextLength: 1000,
  minMenuTriggerCount: 1,
  h1Includes: ['Conversions'],
  apiIncludes: [
    '/commercial-capabilities',
    '/campaign-assets',
    '/codes',
    '/finance-summary',
    '/statements',
    '/payout-accounts',
    '/conversion-records',
    '/analytics-metrics',
  ],
});

routeCheck('partner:workspace security settings state', evidence.partnerRoutes, '/ru-RU/settings', {
  minBodyTextLength: 2000,
  minMenuTriggerCount: 1,
  h1Includes: ['Settings'],
  apiIncludes: [
    '/api/v1/auth/passkeys/policy',
    '/api/v1/auth/passkeys',
    '/settings',
    '/security/passkeys/compliance',
    '/security/passkeys/policy',
    '/partner-session/bootstrap',
  ],
});

routeCheck('partner:session-device state', evidence.partnerRoutes, '/ru-RU/security/sessions', {
  minBodyTextLength: 1000,
  minMenuTriggerCount: 1,
  h1Includes: ['Консоль сессий'],
  apiIncludes: [
    '/api/v1/auth/session',
    '/api/v1/auth/devices',
    '/api/v1/partner-workspaces/me',
    '/api/v1/partner-session/bootstrap',
  ],
});

userMenuCheck('frontend live user-menu/logout', evidence.frontendUserMenu, {
  navigationPath: '/en-EN/settings/security',
});
userMenuCheck('admin live user-menu/logout', evidence.adminUserMenu, {
  navigationPath: '/en-EN/security/sessions',
});
userMenuCheck('partner live user-menu/logout', evidence.partnerUserMenu, {
  navigationPath: '/en-EN/settings',
});

passkeyVirtualAuthenticatorCheck(evidence.passkeyVirtualAuthenticator);

const failed = checks.filter((check) => check.status !== 'passed');
const output = {
  status: failed.length === 0 ? 'passed' : 'failed',
  checkCount: checks.length,
  passedCount: checks.length - failed.length,
  failedCount: failed.length,
  checks,
};

const outputPath = resolve(REPO_ROOT, OUTPUT_PATH);
mkdirSync(dirname(outputPath), { recursive: true });
writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`, 'utf8');
process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);

if (failed.length > 0) {
  process.exitCode = 1;
}

function routeCheck(name, routeEvidence, routePath, expectations) {
  const route = routeEvidence.routes.find((candidate) => candidate.path === routePath);
  const details = {
    routePath,
    h1: route?.h1 ?? [],
    bodyTextLength: route?.bodyTextLength ?? null,
    menuTriggerCount: route?.menuTriggerCount ?? null,
    apiMatches: [],
  };

  const failures = [];
  if (!route) {
    failures.push(`Missing route ${routePath}.`);
  } else {
    if (route.status !== 'passed') {
      failures.push(`Route status is ${route.status}.`);
    }
    if (route.finalPathname !== routePath) {
      failures.push(`Route finalPathname is ${route.finalPathname}.`);
    }
    if ((route.bodyTextLength ?? 0) < expectations.minBodyTextLength) {
      failures.push(`Route bodyTextLength ${route.bodyTextLength} < ${expectations.minBodyTextLength}.`);
    }
    if ((route.menuTriggerCount ?? 0) < expectations.minMenuTriggerCount) {
      failures.push(`Route menuTriggerCount ${route.menuTriggerCount} < ${expectations.minMenuTriggerCount}.`);
    }
    for (const text of expectations.h1Includes) {
      if (!route.h1.some((h1) => h1.toLowerCase().includes(text.toLowerCase()))) {
        failures.push(`Route h1 did not include ${text}.`);
      }
    }
    const badApiResponses = route.apiResponses.filter((response) => response.status >= 400);
    if (badApiResponses.length > 0) {
      failures.push(`Route had API responses >=400: ${JSON.stringify(badApiResponses)}.`);
    }
    for (const expectedApi of expectations.apiIncludes) {
      const matches = route.apiResponses.filter((response) => response.path.includes(expectedApi));
      details.apiMatches.push({ expectedApi, count: matches.length, statuses: [...new Set(matches.map((item) => item.status))] });
      if (matches.length === 0) {
        failures.push(`Route did not call ${expectedApi}.`);
      }
      const nonSuccess = matches.filter((response) => response.status < 200 || response.status >= 300);
      if (nonSuccess.length > 0) {
        failures.push(`Route ${expectedApi} had non-2xx statuses: ${JSON.stringify(nonSuccess)}.`);
      }
    }
  }

  recordCheck(name, failures, details);
}

function userMenuCheck(name, payload, expectations) {
  const failures = [];
  if (payload.status !== 'passed') {
    failures.push(`Smoke status is ${payload.status}.`);
  }
  if (payload.liveApi !== true || payload.intercepted !== false || payload.devBypassAuth !== false) {
    failures.push('Smoke did not run as strict live API with no interception/dev bypass.');
  }
  if (payload.userMenu?.navigationPath !== expectations.navigationPath) {
    failures.push(`navigationPath is ${payload.userMenu?.navigationPath}.`);
  }
  if (payload.userMenu?.logoutNavigationPath !== '/en-EN/login') {
    failures.push(`logoutNavigationPath is ${payload.userMenu?.logoutNavigationPath}.`);
  }
  if (payload.userMenu?.sessionAfterLogoutStatus !== 401 && payload.userMenu?.sessionAfterLogoutStatus !== 403) {
    failures.push(`sessionAfterLogoutStatus is ${payload.userMenu?.sessionAfterLogoutStatus}.`);
  }
  if (!payload.apiResponses?.some((response) => response.path?.includes('/api/v1/auth/logout') || response.url?.includes('/api/v1/auth/logout'))) {
    failures.push('Logout API response was not recorded.');
  }

  recordCheck(name, failures, {
    navigationPath: payload.userMenu?.navigationPath,
    navigationLatencyMs: payload.userMenu?.navigationLatencyMs,
    logoutNavigationPath: payload.userMenu?.logoutNavigationPath,
    sessionAfterLogoutStatus: payload.userMenu?.sessionAfterLogoutStatus,
  });
}

function passkeyVirtualAuthenticatorCheck(payload) {
  const statuses = new Map(payload.statuses.map((entry) => [`${entry.method} ${entry.path} ${entry.status}`, entry]));
  const failures = [];
  if (payload.status !== 'passed') failures.push(`Smoke status is ${payload.status}.`);
  if (payload.liveApi !== true || payload.intercepted !== false || payload.devBypassAuth !== false) {
    failures.push('Passkey smoke did not run live without interception/dev bypass.');
  }
  if (!payload.virtualAuthenticator?.authenticatorIdPresent) failures.push('Virtual authenticator id was missing.');
  if (payload.policy?.enabled !== true || payload.policy?.rpId !== 'localhost' || payload.policy?.originAllowed !== true) {
    failures.push('Passkey policy did not prove enabled localhost RP and allowed origin.');
  }
  for (const expected of [
    'GET /api/v1/auth/passkeys/policy 200',
    'POST /api/v1/auth/login 200',
    'GET /api/v1/auth/session 200',
    'POST /api/v1/auth/passkeys/registration/options 200',
    'POST /api/v1/auth/passkeys/registration/verify 201',
    'POST /api/v1/auth/logout 204',
    'GET /api/v1/auth/session 401',
    'POST /api/v1/auth/passkeys/authentication/options 200',
    'POST /api/v1/auth/passkeys/authentication/verify 200',
    'POST /api/v1/auth/passkeys/authentication/verify 401',
  ]) {
    if (!statuses.has(expected)) {
      failures.push(`Missing passkey status ${expected}.`);
    }
  }
  if (payload.registration?.userVerified !== true || payload.registration?.credentialType !== 'public-key') {
    failures.push('Registration did not prove public-key user-verified credential.');
  }
  if (payload.authentication?.authRealmKey !== 'customer' || payload.authentication?.tokenFieldsPresent !== false) {
    failures.push('Authentication did not prove customer tokenless passkey session.');
  }
  if (payload.session?.afterPasskeyLogin !== 200 || payload.session?.authRealmKey !== 'customer') {
    failures.push('Post-passkey session did not prove customer session.');
  }
  if (payload.replay?.status !== 401 && payload.replay?.status !== 403) {
    failures.push(`Replay status was ${payload.replay?.status}.`);
  }

  recordCheck('frontend browser-level WebAuthn virtual authenticator', failures, {
    origin: payload.origin,
    apiBaseUrl: payload.apiBaseUrl,
    virtualAuthenticator: payload.virtualAuthenticator,
    registration: payload.registration,
    authentication: payload.authentication,
    replay: payload.replay,
    session: payload.session,
  });
}

function recordCheck(name, failures, details) {
  checks.push({
    name,
    status: failures.length === 0 ? 'passed' : 'failed',
    failures,
    details,
  });
}

function readJson(relativePath) {
  return JSON.parse(readFileSync(resolve(REPO_ROOT, relativePath), 'utf8'));
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
