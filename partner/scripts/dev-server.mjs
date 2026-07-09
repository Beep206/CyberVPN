import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(PROJECT_ROOT, '..');
const NEXT_BIN = [
  path.join(PROJECT_ROOT, 'node_modules', 'next', 'dist', 'bin', 'next'),
  path.join(REPO_ROOT, 'node_modules', 'next', 'dist', 'bin', 'next'),
].find((candidate) => existsSync(candidate));
const DEV_HOST = process.env.HOST ?? '0.0.0.0';
const DEV_PORT = process.env.PORT ?? '3002';
const DEV_PORTAL_HOSTS = [
  `localhost:${DEV_PORT}`,
  `127.0.0.1:${DEV_PORT}`,
  `portal.localhost:${DEV_PORT}`,
];

if (!NEXT_BIN) {
  console.error('Unable to find Next.js. Run npm ci from the repository root before starting the partner dev server.');
  process.exit(1);
}

function appendCsvEnv(value, entries) {
  const items = new Set(
    (value ?? '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
  );

  for (const entry of entries) {
    items.add(entry);
  }

  return Array.from(items).join(',');
}

const sharedEnv = {
  ...process.env,
  NEXT_TELEMETRY_DISABLED: process.env.NEXT_TELEMETRY_DISABLED ?? '1',
  NEXT_PUBLIC_PARTNER_PORTAL_HOSTS: appendCsvEnv(
    process.env.NEXT_PUBLIC_PARTNER_PORTAL_HOSTS,
    DEV_PORTAL_HOSTS,
  ),
};

const watcher = spawn(process.execPath, [path.join(__dirname, 'generate-message-bundles.mjs'), '--watch'], {
  cwd: PROJECT_ROOT,
  env: sharedEnv,
  stdio: 'inherit',
});

const nextDev = spawn(process.execPath, [NEXT_BIN, 'dev', '-p', DEV_PORT, '-H', DEV_HOST], {
  cwd: PROJECT_ROOT,
  env: sharedEnv,
  stdio: 'inherit',
});

let isShuttingDown = false;

function shutdown(signal = 'SIGTERM') {
  if (isShuttingDown) {
    return;
  }

  isShuttingDown = true;
  watcher.kill(signal);
  nextDev.kill(signal);
}

watcher.on('exit', (code, signal) => {
  if (isShuttingDown) {
    return;
  }

  shutdown();
  process.exit(code ?? (signal ? 1 : 0));
});

nextDev.on('exit', (code, signal) => {
  shutdown();
  process.exit(code ?? (signal ? 1 : 0));
});

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
