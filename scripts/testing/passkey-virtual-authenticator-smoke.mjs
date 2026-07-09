import { existsSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import http from 'node:http';

const SURFACE = readCliOption('surface') || process.env.PASSKEY_VIRTUAL_AUTH_SURFACE || 'frontend';
const ORIGIN = trimTrailingSlash(
  readCliOption('origin') || process.env.PASSKEY_VIRTUAL_AUTH_ORIGIN || 'http://localhost:3004',
);
const API_BASE_URL = trimTrailingSlash(
  readCliOption('api-base-url') || process.env.PASSKEY_VIRTUAL_AUTH_API_BASE_URL || 'http://localhost:8002',
);
const LOGIN_IDENTIFIER = process.env.PASSKEY_VIRTUAL_AUTH_IDENTIFIER || process.env.AUTH_LOGIN_SMOKE_IDENTIFIER;
const LOGIN_PASSWORD = process.env.PASSKEY_VIRTUAL_AUTH_PASSWORD || process.env.AUTH_LOGIN_SMOKE_PASSWORD;
const LABEL = process.env.PASSKEY_VIRTUAL_AUTH_LABEL || `Virtual authenticator ${new Date().toISOString()}`;
const NAVIGATION_TIMEOUT_MS = numberFromEnv('PASSKEY_VIRTUAL_AUTH_NAVIGATION_TIMEOUT_MS', 30_000);
const ASSERTION_TIMEOUT_MS = numberFromEnv('PASSKEY_VIRTUAL_AUTH_ASSERTION_TIMEOUT_MS', 90_000);
const CHROMIUM_BIN = process.env.CHROMIUM_BIN || findChromium();

assert(LOGIN_IDENTIFIER, 'PASSKEY_VIRTUAL_AUTH_IDENTIFIER or AUTH_LOGIN_SMOKE_IDENTIFIER is required.');
assert(LOGIN_PASSWORD, 'PASSKEY_VIRTUAL_AUTH_PASSWORD or AUTH_LOGIN_SMOKE_PASSWORD is required.');
assert(CHROMIUM_BIN, 'Chromium/Chrome executable was not found. Set CHROMIUM_BIN.');
assertLocalHttpUrl(ORIGIN, 'origin');
assertLocalHttpUrl(API_BASE_URL, 'api-base-url');

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

function trimTrailingSlash(value) {
  return value.replace(/\/$/, '');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function assertLocalHttpUrl(value, label) {
  const parsed = new URL(value);
  const allowedHosts = new Set(['localhost', '127.0.0.1', '::1']);
  const allowNonLocal = process.env.PASSKEY_VIRTUAL_AUTH_ALLOW_NONLOCAL === 'true';
  assert(parsed.protocol === 'http:' || allowNonLocal, `${label} must use local http unless explicitly overridden.`);
  assert(
    allowedHosts.has(parsed.hostname) || allowNonLocal,
    `${label} must target localhost/127.0.0.1 unless explicitly overridden.`,
  );
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

function startOriginServer(origin) {
  const target = new URL(origin);
  const server = http.createServer((request, response) => {
    response.writeHead(200, {
      'cache-control': 'no-store',
      'content-type': 'text/html; charset=utf-8',
    });
    response.end(`<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Passkey virtual authenticator smoke</title></head>
<body><main id="root">Passkey virtual authenticator smoke</main></body>
</html>`);
  });

  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(Number(target.port || 80), target.hostname, () => {
      server.off('error', reject);
      resolve(server);
    });
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

async function evaluate(client, sessionId, expression) {
  const result = await client.send(
    'Runtime.evaluate',
    {
      expression,
      awaitPromise: true,
      returnByValue: true,
      timeout: ASSERTION_TIMEOUT_MS,
    },
    sessionId,
  );

  if (result.exceptionDetails) {
    const details = result.exceptionDetails;
    const description = details.exception?.description || details.text || 'Runtime evaluation failed';
    throw new Error(description);
  }

  return result.result?.value;
}

async function main() {
  const originServer = await startOriginServer(ORIGIN);
  const userDataDir = await mkdtemp(join(tmpdir(), 'cybervpn-passkey-virtual-auth-'));
  const browserProcess = spawn(CHROMIUM_BIN, [
    '--headless=new',
    '--remote-debugging-port=0',
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-networking',
    '--disable-extensions',
    `--unsafely-treat-insecure-origin-as-secure=${ORIGIN}`,
    'about:blank',
  ], {
    stdio: ['ignore', 'ignore', 'pipe'],
  });

  let socket;
  try {
    const webSocketUrl = await waitForWebSocketUrl(browserProcess);
    socket = new WebSocket(webSocketUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', reject, { once: true });
    });

    const client = new CdpClient(socket);
    const apiResponses = [];
    const pageErrors = [];
    const { targetId } = await client.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await client.send('Target.attachToTarget', {
      targetId,
      flatten: true,
    });

    client.on('Network.responseReceived', (message) => {
      if (message.sessionId !== sessionId) return;
      const { response } = message.params;
      if (response.url.includes('/api/')) {
        apiResponses.push({ status: response.status, url: response.url });
      }
    });
    client.on('Runtime.exceptionThrown', (message) => {
      if (message.sessionId !== sessionId) return;
      const details = message.params.exceptionDetails;
      pageErrors.push(details.exception?.description || details.exception?.value || details.text || JSON.stringify(details));
    });

    await client.send('Page.enable', {}, sessionId);
    await client.send('Runtime.enable', {}, sessionId);
    await client.send('Network.enable', {}, sessionId);
    await client.send('WebAuthn.enable', {}, sessionId);
    const { authenticatorId } = await client.send('WebAuthn.addVirtualAuthenticator', {
      options: {
        protocol: 'ctap2',
        transport: 'usb',
        hasResidentKey: true,
        hasUserVerification: true,
        isUserVerified: true,
        automaticPresenceSimulation: true,
      },
    }, sessionId);

    const loadEvent = waitForEvent(
      client,
      'Page.loadEventFired',
      (message) => message.sessionId === sessionId,
      NAVIGATION_TIMEOUT_MS,
    );
    await client.send('Page.navigate', { url: `${ORIGIN}/passkey-virtual-authenticator-smoke` }, sessionId);
    await loadEvent;

    const resultJson = await evaluate(
      client,
      sessionId,
      `
        (async () => {
          const apiBaseUrl = ${JSON.stringify(API_BASE_URL)};
          const loginIdentifier = ${JSON.stringify(LOGIN_IDENTIFIER)};
          const loginPassword = ${JSON.stringify(LOGIN_PASSWORD)};
          const label = ${JSON.stringify(LABEL)};
          const statuses = [];

          function assertBrowser(condition, message) {
            if (!condition) {
              throw new Error(message);
            }
          }

          function base64UrlToArrayBuffer(value) {
            const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
            const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
            const binary = atob(padded);
            const bytes = new Uint8Array(binary.length);
            for (let index = 0; index < binary.length; index += 1) {
              bytes[index] = binary.charCodeAt(index);
            }
            return bytes.buffer;
          }

          function arrayBufferToBase64Url(value) {
            if (value === null || value === undefined) {
              return null;
            }
            const bytes = new Uint8Array(value);
            let binary = '';
            for (const byte of bytes) {
              binary += String.fromCharCode(byte);
            }
            return btoa(binary).replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/g, '');
          }

          function publicKeyCredentialToJSON(credential) {
            const response = credential.response;
            const output = {
              id: credential.id,
              rawId: arrayBufferToBase64Url(credential.rawId),
              type: credential.type,
              response: {
                clientDataJSON: arrayBufferToBase64Url(response.clientDataJSON),
              },
              clientExtensionResults: credential.getClientExtensionResults?.() ?? {},
              authenticatorAttachment: credential.authenticatorAttachment ?? null,
            };

            if ('attestationObject' in response) {
              output.response.attestationObject = arrayBufferToBase64Url(response.attestationObject);
              output.response.transports = response.getTransports?.() ?? [];
            }
            if ('authenticatorData' in response) {
              output.response.authenticatorData = arrayBufferToBase64Url(response.authenticatorData);
              output.response.signature = arrayBufferToBase64Url(response.signature);
              output.response.userHandle = arrayBufferToBase64Url(response.userHandle);
            }

            return output;
          }

          function toCreationOptions(publicKey) {
            return {
              ...publicKey,
              challenge: base64UrlToArrayBuffer(publicKey.challenge),
              user: {
                ...publicKey.user,
                id: base64UrlToArrayBuffer(publicKey.user.id),
              },
              excludeCredentials: (publicKey.excludeCredentials ?? []).map((credential) => ({
                ...credential,
                id: base64UrlToArrayBuffer(credential.id),
              })),
            };
          }

          function toRequestOptions(publicKey) {
            return {
              ...publicKey,
              challenge: base64UrlToArrayBuffer(publicKey.challenge),
              allowCredentials: (publicKey.allowCredentials ?? []).map((credential) => ({
                ...credential,
                id: base64UrlToArrayBuffer(credential.id),
              })),
            };
          }

          async function requestJson(path, init = {}) {
            const method = init.method ?? 'GET';
            const hasBody = init.body !== undefined;
            const response = await fetch(apiBaseUrl + path, {
              ...init,
              method,
              credentials: 'include',
              headers: {
                ...(hasBody ? { 'content-type': 'application/json' } : {}),
                ...(init.headers ?? {}),
              },
            });
            const text = await response.text();
            const body = text ? JSON.parse(text) : null;
            statuses.push({ method, path, status: response.status });
            return { body, ok: response.ok, status: response.status };
          }

          const policy = await requestJson('/api/v1/auth/passkeys/policy');
          const policyAllowedOrigins = policy.body.allowedOrigins ?? policy.body.allowed_origins ?? [];
          const policyRpId = policy.body.rpId ?? policy.body.rp_id;
          const policyRealmKey = policy.body.realmKey ?? policy.body.realm_key;
          const policyConditionalUiEnabled =
            policy.body.conditionalUiEnabled ?? policy.body.conditional_ui_enabled;
          assertBrowser(policy.status === 200, 'Passkey policy did not return 200.');
          assertBrowser(policy.body.enabled === true, 'Passkey policy was not enabled.');
          assertBrowser(policyRpId === 'localhost', 'Passkey policy rpId was not localhost.');
          assertBrowser(policyAllowedOrigins.includes(location.origin), 'Passkey policy did not allow the browser origin.');

          const login = await requestJson('/api/v1/auth/login', {
            method: 'POST',
            body: JSON.stringify({
              login_or_email: loginIdentifier,
              password: loginPassword,
              remember_me: false,
            }),
          });
          assertBrowser(login.status === 200, 'Password login did not return 200.');

          const sessionAfterPasswordLogin = await requestJson('/api/v1/auth/session');
          assertBrowser(sessionAfterPasswordLogin.status === 200, 'Session after password login did not return 200.');

          const registrationOptions = await requestJson('/api/v1/auth/passkeys/registration/options', {
            method: 'POST',
            body: JSON.stringify({ label }),
          });
          assertBrowser(registrationOptions.status === 200, 'Registration options did not return 200.');
          assertBrowser(
            registrationOptions.body.publicKey.authenticatorSelection.userVerification === 'required',
            'Registration options did not require user verification.',
          );

          const registrationCredential = await navigator.credentials.create({
            publicKey: toCreationOptions(registrationOptions.body.publicKey),
          });
          assertBrowser(registrationCredential?.type === 'public-key', 'Browser did not create a public-key credential.');

          const registrationVerify = await requestJson('/api/v1/auth/passkeys/registration/verify', {
            method: 'POST',
            body: JSON.stringify({
              challengeId: registrationOptions.body.challengeId,
              credential: publicKeyCredentialToJSON(registrationCredential),
              label,
            }),
          });
          assertBrowser(registrationVerify.status === 201, 'Registration verify did not return 201.');
          assertBrowser(registrationVerify.body.status === 'active', 'Registered credential was not active.');

          const logout = await requestJson('/api/v1/auth/logout', { method: 'POST' });
          assertBrowser(logout.status === 204, 'Logout after registration did not return 204.');

          const sessionAfterLogout = await requestJson('/api/v1/auth/session');
          assertBrowser(
            sessionAfterLogout.status === 401 || sessionAfterLogout.status === 403,
            'Session after logout did not return 401/403.',
          );

          const authenticationOptions = await requestJson('/api/v1/auth/passkeys/authentication/options', {
            method: 'POST',
            body: JSON.stringify({ identifier: loginIdentifier, conditional: false }),
          });
          assertBrowser(authenticationOptions.status === 200, 'Authentication options did not return 200.');
          assertBrowser(
            authenticationOptions.body.publicKey.allowCredentials.length >= 1,
            'Authentication options did not include an allowCredentials entry.',
          );

          const authenticationCredential = await navigator.credentials.get({
            publicKey: toRequestOptions(authenticationOptions.body.publicKey),
          });
          assertBrowser(authenticationCredential?.type === 'public-key', 'Browser did not return a public-key assertion.');

          const authenticationVerifyPayload = {
            challengeId: authenticationOptions.body.challengeId,
            credential: publicKeyCredentialToJSON(authenticationCredential),
          };
          const authenticationVerify = await requestJson('/api/v1/auth/passkeys/authentication/verify', {
            method: 'POST',
            body: JSON.stringify(authenticationVerifyPayload),
          });
          assertBrowser(authenticationVerify.status === 200, 'Authentication verify did not return 200.');
          assertBrowser(authenticationVerify.body.auth_realm_key === 'customer', 'Passkey auth did not issue customer realm.');
          assertBrowser(authenticationVerify.body.requires_2fa === false, 'Passkey auth unexpectedly required 2FA.');
          assertBrowser(
            !('access_token' in authenticationVerify.body) && !('refresh_token' in authenticationVerify.body),
            'Passkey auth verify body leaked token fields.',
          );

          const replay = await requestJson('/api/v1/auth/passkeys/authentication/verify', {
            method: 'POST',
            body: JSON.stringify(authenticationVerifyPayload),
          });
          assertBrowser(
            replay.status === 401 || replay.status === 403,
            'Replayed passkey authentication challenge was not rejected.',
          );

          const sessionAfterPasskeyLogin = await requestJson('/api/v1/auth/session');
          assertBrowser(sessionAfterPasskeyLogin.status === 200, 'Session after passkey login did not return 200.');
          const sessionEmail = sessionAfterPasskeyLogin.body.user?.email ?? sessionAfterPasskeyLogin.body.email;
          const sessionRealmKey = sessionAfterPasskeyLogin.body.auth_realm_key;
          const sessionPrincipalType = sessionAfterPasskeyLogin.body.principal_type;
          assertBrowser(sessionEmail === loginIdentifier, 'Passkey session user mismatch.');
          assertBrowser(sessionRealmKey === 'customer', 'Passkey session realm mismatch.');
          assertBrowser(sessionPrincipalType === 'customer', 'Passkey session principal mismatch.');

          return JSON.stringify({
            statuses,
            policy: {
              enabled: policy.body.enabled,
              surface: policy.body.surface,
              realmKey: policyRealmKey,
              rpId: policyRpId,
              originAllowed: policyAllowedOrigins.includes(location.origin),
              conditionalUiEnabled: policyConditionalUiEnabled,
            },
            registration: {
              status: registrationVerify.status,
              credentialRecordId: registrationVerify.body.id,
              label: registrationVerify.body.label,
              credentialType: registrationVerify.body.credentialType ?? registrationVerify.body.credential_type,
              deviceType: registrationVerify.body.deviceType ?? registrationVerify.body.device_type,
              userVerified: registrationVerify.body.userVerified ?? registrationVerify.body.user_verified,
            },
            authentication: {
              status: authenticationVerify.status,
              authRealmKey: authenticationVerify.body.auth_realm_key,
              audience: authenticationVerify.body.audience,
              principalType: authenticationVerify.body.principal_type,
              scopeFamily: authenticationVerify.body.scope_family,
              requires2fa: authenticationVerify.body.requires_2fa,
              tokenFieldsPresent:
                'access_token' in authenticationVerify.body || 'refresh_token' in authenticationVerify.body,
            },
            replay: {
              status: replay.status,
            },
            session: {
              afterPasswordLogin: sessionAfterPasswordLogin.status,
              afterLogout: sessionAfterLogout.status,
              afterPasskeyLogin: sessionAfterPasskeyLogin.status,
              authRealmKey: sessionRealmKey,
              principalType: sessionPrincipalType,
              userEmailMatched: sessionEmail === loginIdentifier,
            },
          });
        })()
      `,
    );
    assert(pageErrors.length === 0, `Page errors observed:\n${pageErrors.join('\n')}`);

    const browserResult = JSON.parse(resultJson);
    process.stdout.write(`${JSON.stringify({
      status: 'passed',
      surface: SURFACE,
      origin: ORIGIN,
      apiBaseUrl: API_BASE_URL,
      liveApi: true,
      intercepted: false,
      devBypassAuth: false,
      virtualAuthenticator: {
        authenticatorIdPresent: Boolean(authenticatorId),
        protocol: 'ctap2',
        transport: 'usb',
        hasResidentKey: true,
        hasUserVerification: true,
        isUserVerified: true,
        automaticPresenceSimulation: true,
      },
      ...browserResult,
      apiResponses,
    }, null, 2)}\n`);
  } finally {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
    if (!browserProcess.killed) {
      browserProcess.kill('SIGTERM');
    }
    await new Promise((resolve) => {
      if (browserProcess.exitCode !== null) {
        resolve();
        return;
      }
      const timer = setTimeout(resolve, 2_000);
      browserProcess.once('exit', () => {
        clearTimeout(timer);
        resolve();
      });
    });
    await new Promise((resolve) => {
      originServer.close(resolve);
    });
    try {
      await rm(userDataDir, { force: true, maxRetries: 5, recursive: true, retryDelay: 200 });
    } catch (error) {
      if (error?.code !== 'EBUSY' && error?.code !== 'EPERM') {
        throw error;
      }
      process.stderr.write(`Warning: deferred Chromium profile cleanup for ${userDataDir}: ${error.code}\n`);
    }
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
