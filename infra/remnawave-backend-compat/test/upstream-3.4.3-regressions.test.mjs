import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const testDir = dirname(fileURLToPath(import.meta.url));
const sourceVerifier = resolve(testDir, '..', 'verify-upstream-3.4.3-regressions.mjs');
const openApiVerifier = resolve(testDir, '..', 'verify-openapi-nullability.mjs');

function write(root, relativePath, content) {
  const target = join(root, relativePath);
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, content);
}

function makeSourceFixture() {
  const root = mkdtempSync(join(tmpdir(), 'cybervpn-remnawave-343-source-'));
  write(
    root,
    'package.json',
    JSON.stringify({
      version: '3.4.3',
      scripts: { postinstall: 'patch-package' },
      devDependencies: { 'patch-package': '^8.0.1' },
    }),
  );
  write(
    root,
    'src/modules/hwid-user-devices/repositories/hwid-user-devices.repository.ts',
    `@Transactional()
    public async createWithAdvisoryLock() {
      await tx.$executeRaw\`SELECT pg_advisory_xact_lock(\${HWID_LOCK_PREFIX + entity.userId})\`;
      await tx.hwidUserDevices.findUnique({});
      return { status: 'EXISTS' };
      await tx.hwidUserDevices.count({});
      return { status: 'LIMIT_REACHED' };
      await tx.hwidUserDevices.create({});
      return { status: 'CREATED' };
    }`,
  );
  write(
    root,
    'src/modules/subscription/subscription.service.ts',
    `switch (result.status) {
      case 'CREATED':
        emit(EVENTS.USER_HWID_DEVICES.ADDED);
        break;
      case 'EXISTS':
        checkAndUpsertHwidDevice();
        break;
      case 'LIMIT_REACHED':
        break;
    }`,
  );
  write(
    root,
    'src/main.ts',
    `const backendToolsPath = \`\${ROOT}\${BACKEND_TOOLS_ROOT}\`;
const isBackendToolsRequest = (req: Request): boolean =>
  req.path.toLowerCase().startsWith(backendToolsPath);
app.use(backendToolsPath, toolsAuthMiddleware(config.getOrThrow('APP_SECRET')));`,
  );
  write(root, 'patches/nestjs-zod+5.5.0.patch', 'normalizeTypeUnions');
  const compiled = `function normalizeTypeUnions(rootSchema) {
    return { anyOf: type.map((singleType) => ({ type: singleType })) };
  }`;
  write(root, 'node_modules/nestjs-zod/dist/dto-CHeB-l1i.mjs', compiled);
  write(root, 'node_modules/nestjs-zod/dist/dto-sWxCeI9D.cjs', compiled);
  return root;
}

function runSourceVerifier(root) {
  return spawnSync(process.execPath, [sourceVerifier], {
    env: { ...process.env, REMNAWAVE_BACKEND_SOURCE_ROOT: root },
    encoding: 'utf8',
  });
}

test('3.4.3 source verifier accepts the backend-tools, HWID, and OpenAPI fixes', () => {
  const root = makeSourceFixture();
  try {
    const result = runSourceVerifier(root);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Verified Remnawave 3\.4\.3/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('3.4.3 source verifier fails closed when the per-user advisory lock drifts', () => {
  const root = makeSourceFixture();
  try {
    const repositoryPath = join(
      root,
      'src/modules/hwid-user-devices/repositories/hwid-user-devices.repository.ts',
    );
    const source = String.raw`@Transactional()
    public async createWithAdvisoryLock() {
      await tx.$executeRaw\`SELECT 1\`;
      await tx.hwidUserDevices.findUnique({});
      return { status: 'EXISTS' };
      await tx.hwidUserDevices.count({});
      return { status: 'LIMIT_REACHED' };
      await tx.hwidUserDevices.create({});
      return { status: 'CREATED' };
    }`;
    writeFileSync(repositoryPath, source);
    const result = runSourceVerifier(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /per-user PostgreSQL advisory lock/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('3.4.3 source verifier fails closed when mixed-case backend-tools auth regresses', () => {
  const root = makeSourceFixture();
  try {
    writeFileSync(
      join(root, 'src/main.ts'),
      `app.use((req: Request, res: Response, next: NextFunction) => {
        if (req.path.startsWith(\`\${ROOT}\${BACKEND_TOOLS_ROOT}\`)) {
          return toolsAuthMiddleware(config.getOrThrow('APP_SECRET'))(req, res, next);
        }
        return next();
      });`,
    );
    const result = runSourceVerifier(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /backend-tools canonical mount path/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('OpenAPI verifier accepts anyOf schemas and rejects array-valued type fields', () => {
  const root = mkdtempSync(join(tmpdir(), 'cybervpn-remnawave-343-openapi-'));
  try {
    const target = join(root, 'openapi.json');
    writeFileSync(
      target,
      JSON.stringify({ openapi: '3.1.0', components: { schemas: { Value: { anyOf: [{ type: 'string' }] } } } }),
    );
    const passing = spawnSync(process.execPath, [openApiVerifier, target], { encoding: 'utf8' });
    assert.equal(passing.status, 0, passing.stderr);

    writeFileSync(
      target,
      JSON.stringify({ openapi: '3.1.0', components: { schemas: { Value: { type: ['string', 'null'] } } } }),
    );
    const failing = spawnSync(process.execPath, [openApiVerifier, target], { encoding: 'utf8' });
    assert.notEqual(failing.status, 0);
    assert.match(failing.stderr, /array-valued type fields/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
