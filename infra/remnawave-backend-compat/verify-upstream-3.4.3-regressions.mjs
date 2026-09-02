#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const sourceRoot =
  process.env.REMNAWAVE_BACKEND_SOURCE_ROOT ?? '/opt/remnawave-backend';

function fail(message) {
  console.error(`Remnawave 3.4.3 upstream regression verification failed: ${message}`);
  process.exit(1);
}

function read(relativePath) {
  return readFileSync(join(sourceRoot, relativePath), 'utf8').replaceAll('\r\n', '\n');
}

function requireOnce(source, needle, label) {
  const count = source.split(needle).length - 1;
  if (count !== 1) {
    fail(`${label} must occur exactly once, found ${count}`);
  }
}

function requireOrder(source, needles, label) {
  let cursor = -1;
  for (const needle of needles) {
    const next = source.indexOf(needle, cursor + 1);
    if (next < 0 || next <= cursor) {
      fail(`${label} is missing or out of order at ${JSON.stringify(needle)}`);
    }
    cursor = next;
  }
}

const packageJson = JSON.parse(read('package.json'));
if (packageJson.version !== '3.4.3') {
  fail(`package version must be 3.4.3, got ${JSON.stringify(packageJson.version)}`);
}
if (packageJson.scripts?.postinstall !== 'patch-package') {
  fail('package postinstall must apply the tagged patch-package fixes');
}
if (packageJson.devDependencies?.['patch-package'] !== '^8.0.1') {
  fail('patch-package ^8.0.1 must remain pinned in the tagged source');
}

const repository = read(
  'src/modules/hwid-user-devices/repositories/hwid-user-devices.repository.ts',
);
requireOnce(repository, '@Transactional()\n    public async createWithAdvisoryLock(', 'HWID transaction');
requireOnce(
  repository,
  '$executeRaw`SELECT pg_advisory_xact_lock(${HWID_LOCK_PREFIX + entity.userId})`',
  'per-user PostgreSQL advisory lock',
);
for (const status of ['CREATED', 'EXISTS', 'LIMIT_REACHED']) {
  if (!repository.includes(`status: '${status}'`)) {
    fail(`HWID repository does not expose ${status}`);
  }
}
requireOrder(
  repository,
  [
    'pg_advisory_xact_lock',
    'hwidUserDevices.findUnique',
    "status: 'EXISTS'",
    'hwidUserDevices.count',
    "status: 'LIMIT_REACHED'",
    'hwidUserDevices.create',
    "status: 'CREATED'",
  ],
  'HWID lock/existing/limit/create sequence',
);

const subscriptionService = read('src/modules/subscription/subscription.service.ts');
requireOnce(subscriptionService, "case 'CREATED':", 'CREATED subscription branch');
requireOnce(subscriptionService, "case 'EXISTS':", 'EXISTS subscription branch');
requireOnce(subscriptionService, "case 'LIMIT_REACHED':", 'LIMIT_REACHED subscription branch');
const createdStart = subscriptionService.indexOf("case 'CREATED':");
const existsStart = subscriptionService.indexOf("case 'EXISTS':", createdStart);
const limitStart = subscriptionService.indexOf("case 'LIMIT_REACHED':", existsStart);
const createdBranch = subscriptionService.slice(createdStart, existsStart);
const existsBranch = subscriptionService.slice(existsStart, limitStart);
if (!createdBranch.includes('EVENTS.USER_HWID_DEVICES.ADDED')) {
  fail('CREATED branch must emit the HWID added event');
}
if (existsBranch.includes('EVENTS.USER_HWID_DEVICES.ADDED')) {
  fail('EXISTS branch must not emit a duplicate HWID added event');
}
if (!existsBranch.includes('checkAndUpsertHwidDevice')) {
  fail('EXISTS branch must reconcile mutable device metadata');
}

const main = read('src/main.ts');
requireOnce(
  main,
  'const backendToolsPath = `${ROOT}${BACKEND_TOOLS_ROOT}`;',
  'backend-tools canonical mount path',
);
requireOnce(
  main,
  'req.path.toLowerCase().startsWith(backendToolsPath);',
  'case-insensitive backend-tools path guard',
);
requireOnce(
  main,
  "app.use(backendToolsPath, toolsAuthMiddleware(config.getOrThrow('APP_SECRET')));",
  'backend-tools auth middleware mount',
);
requireOrder(
  main,
  [
    'const backendToolsPath = `${ROOT}${BACKEND_TOOLS_ROOT}`;',
    'req.path.toLowerCase().startsWith(backendToolsPath);',
    "app.use(backendToolsPath, toolsAuthMiddleware(config.getOrThrow('APP_SECRET')));",
  ],
  'backend-tools mixed-case auth boundary',
);

const nullablePatch = read('patches/nestjs-zod+5.5.0.patch');
for (const compiledModule of [
  'node_modules/nestjs-zod/dist/dto-CHeB-l1i.mjs',
  'node_modules/nestjs-zod/dist/dto-sWxCeI9D.cjs',
]) {
  const compiled = read(compiledModule);
  if (!compiled.includes('function normalizeTypeUnions(rootSchema)')) {
    fail(`${compiledModule} is missing the applied nullable-type normalizer`);
  }
  if (!compiled.includes('anyOf: type.map((singleType) => ({ type: singleType }))')) {
    fail(`${compiledModule} does not render union types with anyOf`);
  }
}
if (!nullablePatch.includes('normalizeTypeUnions')) {
  fail('tagged nestjs-zod patch is missing the nullable-type normalizer');
}

console.log(
  'Verified Remnawave 3.4.3 backend-tools auth, HWID concurrency, and nullable OpenAPI source fixes.',
);
