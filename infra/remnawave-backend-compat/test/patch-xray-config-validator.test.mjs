import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import test from 'node:test';

const testDir = dirname(fileURLToPath(import.meta.url));
const patchScript = resolve(testDir, '..', 'patch-xray-config-validator.mjs');
const fixture = resolve(testDir, 'fixtures', 'xray-config.validator.upstream.ts');

const expectedVlessBlock = `            case 'vless':
                if (!inbound.settings) {
                    inbound.settings = {};
                }
                inbound.settings.clients ??= [];

                for (const user of users) {
                    inbound.settings.clients.push({
                        id: user.vlessUuid,
                        email: user.id.toString(),
                    });
                }
                break;`;

function runPatch(targetPath) {
  return spawnSync(process.execPath, [patchScript], {
    env: {
      ...process.env,
      XRAY_CONFIG_VALIDATOR_PATH: targetPath,
    },
    encoding: 'utf8',
  });
}

function makeTempFixture() {
  const dir = mkdtempSync(join(tmpdir(), 'cybervpn-remnawave-compat-'));
  const target = join(dir, 'xray-config.validator.ts');
  copyFileSync(fixture, target);
  return { dir, target };
}

test('source patch adds Vision flow to RAW VLESS clients and omits empty flow', async () => {
  const { dir, target } = makeTempFixture();
  try {
    const result = runPatch(target);
    assert.equal(result.status, 0, result.stderr);

    const patchedSource = readFileSync(target, 'utf8');
    assert.equal(patchedSource.includes(expectedVlessBlock), false);
    assert.equal((patchedSource.match(/const vlessFlow = getVlessFlow\(inbound\);/g) ?? []).length, 1);
    assert.equal((patchedSource.match(/email: user\.id\.toString\(\),/g) ?? []).length, 4);
    assert.equal(patchedSource.includes('user.tId'), false);

    const moduleUrl = `${pathToFileURL(target).href}?test=${Date.now()}`;
    const { XRayConfigHarness } = await import(moduleUrl);
    const harness = new XRayConfigHarness();
    const users = [{ vlessUuid: 'raw-user-id', id: 101n }];

    const rawInbound = {
      protocol: 'vless',
      settings: {},
      testFlow: 'xtls-rprx-vision',
    };
    harness.cleanInboundClients(rawInbound);
    harness.addUsersToInbound(rawInbound, users);
    assert.equal(Object.hasOwn(rawInbound.settings, 'flow'), false);
    assert.deepEqual(rawInbound.settings.clients, [
      {
        id: 'raw-user-id',
        email: '101',
        flow: 'xtls-rprx-vision',
      },
    ]);

    const xhttpInbound = {
      protocol: 'vless',
      settings: {},
      testFlow: '',
    };
    harness.cleanInboundClients(xhttpInbound);
    harness.addUsersToInbound(xhttpInbound, users);
    assert.equal(Object.hasOwn(xhttpInbound.settings, 'flow'), false);
    assert.deepEqual(xhttpInbound.settings.clients, [
      {
        id: 'raw-user-id',
        email: '101',
      },
    ]);
    assert.equal(Object.hasOwn(xhttpInbound.settings.clients[0], 'flow'), false);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('source patch fails closed when the expected VLESS block is ambiguous', () => {
  const { dir, target } = makeTempFixture();
  try {
    const before = `${readFileSync(target, 'utf8')}\n${expectedVlessBlock}\n`;
    writeFileSync(target, before);

    const result = runPatch(target);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /expected 3\.4\.2 TypeScript VLESS addUsersToInbound block exactly once/);
    assert.equal(readFileSync(target, 'utf8'), before);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('source patch fails closed when upstream numeric user id mapping drifts', () => {
  const { dir, target } = makeTempFixture();
  try {
    const before = readFileSync(target, 'utf8').replace(
      'email: user.id.toString(),',
      'email: user.legacyId.toString(),',
    );
    writeFileSync(target, before);

    const result = runPatch(target);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /numeric user id mapping/);
    assert.equal(readFileSync(target, 'utf8'), before);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('source patch fails closed when rerun against already patched source', () => {
  const { dir, target } = makeTempFixture();
  try {
    const firstResult = runPatch(target);
    assert.equal(firstResult.status, 0, firstResult.stderr);
    const beforeSecondRun = readFileSync(target, 'utf8');

    const secondResult = runPatch(target);
    assert.notEqual(secondResult.status, 0);
    assert.match(secondResult.stderr, /expected 3\.4\.2 TypeScript VLESS addUsersToInbound block exactly once/);
    assert.equal(readFileSync(target, 'utf8'), beforeSecondRun);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
