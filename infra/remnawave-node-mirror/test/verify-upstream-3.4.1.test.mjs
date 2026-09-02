import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const testDir = dirname(fileURLToPath(import.meta.url));
const verifier = resolve(testDir, '..', 'verify-upstream-3.4.1.mjs');
const dockerfile = resolve(testDir, '..', 'Dockerfile');

function write(root, relativePath, content) {
  const target = join(root, relativePath);
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, content);
}

function makeFixture() {
  const root = mkdtempSync(join(tmpdir(), 'cybervpn-node-341-'));
  write(
    root,
    'package.json',
    JSON.stringify({
      version: '3.4.1',
      dependencies: { zod: '4.5.4', '@remnawave/node-plugins': '0.8.2' },
    }),
  );
  write(
    root,
    'libs/contract/package.json',
    JSON.stringify({ version: '3.4.1', dependencies: { zod: '4.5.4' } }),
  );
  write(root, 'src/main.ts', "import 'zod/compile';\n");
  write(
    root,
    'src/modules/handler/handler.service.ts',
    `public async addUser(data: AddUserRequestDto) {
const userId = requestData[0].username;
let userIps: string[] | null = null;
if (hashData.prevVlessUuid) {
                userIps = await this.getUserIps(userId);
}
await this.xtlsApi.handler.removeUser(tag, userId);
if (userIps && hashData.prevVlessUuid) {
  this.eventBus.publish(new DropConnectionsEvent(userIps));
}
for (const item of requestData) {
                let tempRes = null;
}
}

    public async removeUser() {
      this.eventBus.publish(new DropConnectionsEvent(userIps));
      this.eventBus.publish(new DropConnectionsEvent(userIps));
      this.eventBus.publish(new DropConnectionsEvent(userIps));
    }`,
  );
  return root;
}

function run(root) {
  return spawnSync(process.execPath, [verifier], {
    env: {
      ...process.env,
      REMNAWAVE_NODE_SOURCE_ROOT: root,
      REMNAWAVE_NODE_PROOF_PATH: join(root, 'proof'),
    },
    encoding: 'utf8',
  });
}

test('node 3.4.1 verifier accepts compiled validation and scoped credential drop', () => {
  const root = makeFixture();
  try {
    const result = run(root);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Verified Remnawave Node 3\.4\.1/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('node 3.4.1 verifier fails closed when drop occurs before old credential removal', () => {
  const root = makeFixture();
  try {
    const handlerPath = join(root, 'src/modules/handler/handler.service.ts');
    const source = readFileSync(handlerPath, 'utf8');
    writeFileSync(
      handlerPath,
      source.replace(
        'await this.xtlsApi.handler.removeUser(tag, userId);',
        'this.eventBus.publish(new DropConnectionsEvent(userIps));\nawait this.xtlsApi.handler.removeUser(tag, userId);',
      ),
    );
    const result = run(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /scoped credential-change drop|capture\/remove\/drop\/re-add/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('node mirror pins exact 3.4.1 source commit, image digest and runtime dependencies', () => {
  const source = readFileSync(dockerfile, 'utf8');
  assert.match(source, /REMNAWAVE_NODE_VERSION=3\.4\.1/);
  assert.match(source, /REMNAWAVE_NODE_COMMIT=44912631321664dbd5822e9bf8d96766ccff7c93/);
  assert.match(source, /sha256:0cdf386dd49f360fc885bb34bde21132e478e40f0deac62d616086ec0fa9257e/);
  assert.match(source, /verify-upstream-3\.4\.1\.mjs/);
  assert.match(source, /dist\/node_modules\/zod\/package\.json/);
  assert.match(source, /this\.nodeVersion=\\"3\.4\.1\\"/);
});
