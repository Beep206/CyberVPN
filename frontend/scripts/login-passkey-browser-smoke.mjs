import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';

const DEFAULT_URL = 'http://127.0.0.1:9001/en-EN/login';
const SMOKE_URL = process.env.FRONTEND_LOGIN_SMOKE_URL || DEFAULT_URL;
const CHROMIUM_BIN = process.env.CHROMIUM_BIN || findChromium();
const NAVIGATION_TIMEOUT_MS = 60_000;
const ASSERTION_TIMEOUT_MS = 10_000;

const PASSKEY_POLICY = {
  enabled: true,
  surface: 'frontend',
  realm_key: 'customer',
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

const SESSION_RESPONSE = {
  id: 'synthetic-customer',
  email: 'neo@example.com',
  login: 'neo',
  is_active: true,
  is_email_verified: true,
  role: 'viewer',
  created_at: '2026-06-03T00:00:00.000Z',
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

async function main() {
  assert(CHROMIUM_BIN, 'Chromium executable was not found. Set CHROMIUM_BIN to run this smoke.');

  const response = await fetch(SMOKE_URL, { method: 'GET' }).catch(() => null);
  assert(response?.ok, `Frontend dev server is not reachable at ${SMOKE_URL}. Start it before running this smoke.`);

  const userDataDir = await mkdtemp(join(tmpdir(), 'cybervpn-login-smoke-'));
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
      if (message.sessionId !== sessionId || message.params.type !== 'error') return;
      consoleErrors.push(message.params.args.map((arg) => arg.value || arg.description || '').join(' '));
    });

    client.on('Fetch.requestPaused', async (message) => {
      if (message.sessionId !== sessionId) return;

      const { requestId, request } = message.params;
      const url = request.url;

      if (url.includes('/api/v1/auth/passkeys/policy')) {
        await client.send('Fetch.fulfillRequest', {
          requestId,
          responseCode: 200,
          responseHeaders: [{ name: 'content-type', value: 'application/json' }],
          body: encodeJsonBody(PASSKEY_POLICY),
        }, sessionId);
        return;
      }

      if (url.includes('/api/v1/auth/passkeys/authentication/options')) {
        await client.send('Fetch.fulfillRequest', {
          requestId,
          responseCode: 200,
          responseHeaders: [{ name: 'content-type', value: 'application/json' }],
          body: encodeJsonBody(PASSKEY_AUTHENTICATION_OPTIONS),
        }, sessionId);
        return;
      }

      if (url.includes('/api/v1/auth/login')) {
        await client.send('Fetch.fulfillRequest', {
          requestId,
          responseCode: 200,
          responseHeaders: [{ name: 'content-type', value: 'application/json' }],
          body: encodeJsonBody(LOGIN_RESPONSE),
        }, sessionId);
        return;
      }

      if (url.includes('/api/v1/auth/session')) {
        await client.send('Fetch.fulfillRequest', {
          requestId,
          responseCode: 200,
          responseHeaders: [{ name: 'content-type', value: 'application/json' }],
          body: encodeJsonBody(SESSION_RESPONSE),
        }, sessionId);
        return;
      }

      await client.send('Fetch.continueRequest', { requestId }, sessionId);
    });

    await client.send('Page.enable', {}, sessionId);
    await client.send('Runtime.enable', {}, sessionId);
    await client.send('Network.enable', {}, sessionId);
    await client.send('Fetch.enable', {
      patterns: [
        { urlPattern: '*://*/api/v1/auth/passkeys/policy*', requestStage: 'Request' },
        { urlPattern: '*://*/api/v1/auth/passkeys/authentication/options*', requestStage: 'Request' },
        { urlPattern: '*://*/api/v1/auth/login*', requestStage: 'Request' },
        { urlPattern: '*://*/api/v1/auth/session*', requestStage: 'Request' },
      ],
    }, sessionId);

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

    await waitForExpression(
      client,
      sessionId,
      `Boolean(document.querySelector('button[aria-label="Sign in with passkey"]'))`,
      ASSERTION_TIMEOUT_MS,
      'Passkey CTA did not render.',
    );

    const autocomplete = await evaluate(
      client,
      sessionId,
      `document.querySelector('input[autocomplete*="username"]')?.getAttribute('autocomplete')`,
    );
    assert(autocomplete === 'username webauthn', `Expected username webauthn autocomplete, got ${autocomplete}.`);

    await evaluate(
      client,
      sessionId,
      `
        (() => {
          const setValue = (input, value) => {
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(input, value);
            input.dispatchEvent(new Event('input', { bubbles: true }));
          };
          setValue(document.querySelector('input[autocomplete*="username"]'), 'neo@example.com');
          setValue(document.querySelector('input[autocomplete="current-password"]'), 'Password123!');
          document.querySelector('button[type="submit"]').click();
          return true;
        })()
      `,
    );

    await waitForExpression(
      client,
      sessionId,
      `location.href === ${JSON.stringify(SMOKE_URL)}`,
      ASSERTION_TIMEOUT_MS,
      'Login form performed native navigation instead of staying under React control.',
    );

    const policyRequested = apiRequests.some((request) => request.includes('/api/v1/auth/passkeys/policy'));
    const loginRequested = apiRequests.some((request) => request.includes('/api/v1/auth/login'));

    assert(policyRequested, 'Passkey policy request was not observed.');
    assert(loginRequested, 'Normal login submit did not call /api/v1/auth/login.');
    assert(pageErrors.length === 0, `Page errors observed:\n${pageErrors.join('\n')}`);
    assert(consoleErrors.length === 0, `Console errors observed:\n${consoleErrors.join('\n')}`);

    process.stdout.write(`${JSON.stringify({
      status: 'passed',
      url: SMOKE_URL,
      autocomplete,
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
