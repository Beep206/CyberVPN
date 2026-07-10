import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const testDir = dirname(fileURLToPath(import.meta.url));
const patchScript = resolve(testDir, '..', 'patch-xray-config-validator.mjs');
const fixture = resolve(testDir, 'fixtures', 'xray-config.validator.upstream.js');

const expectedVlessBlock = `            case 'vless':
                if (!inbound.settings) {
                    inbound.settings = {};
                }
                inbound.settings.clients ??= [];
                for (const user of users) {
                    inbound.settings.clients.push({
                        id: user.vlessUuid,
                        email: user.tId.toString(),
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
  const target = join(dir, 'xray-config.validator.js');
  copyFileSync(fixture, target);
  return { dir, target };
}

test('patch adds Vision flow to RAW VLESS clients and omits empty flow clients', async () => {
  const { dir, target } = makeTempFixture();
  try {
    const result = runPatch(target);
    assert.equal(result.status, 0, result.stderr);

    const patchedSource = readFileSync(target, 'utf8');
    assert.equal(patchedSource.includes(expectedVlessBlock), false);
    assert.equal(
      (patchedSource.match(/const vlessFlow = \(0, get_vless_flow_1\.getVlessFlow\)\(inbound\);/g) ?? [])
        .length,
      1,
    );

    const require = createRequire(import.meta.url);
    const { XRayConfigHarness } = require(target);
    const harness = new XRayConfigHarness();
    const users = [{ vlessUuid: 'raw-user-id', tId: 101 }];

    const rawInbound = {
      protocol: 'vless',
      settings: {},
      __testFlow: 'xtls-rprx-vision',
    };
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
      __testFlow: '',
    };
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

test('patch fails closed when the expected VLESS block is ambiguous', () => {
  const { dir, target } = makeTempFixture();
  try {
    const before = `${readFileSync(target, 'utf8')}\n${expectedVlessBlock}\n`;
    writeFileSync(target, before);

    const result = runPatch(target);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /expected VLESS addUsersToInbound block exactly once/);
    assert.equal(readFileSync(target, 'utf8'), before);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('patch fails closed when the expected VLESS block is missing', () => {
  const { dir, target } = makeTempFixture();
  try {
    const before = readFileSync(target, 'utf8').replace(expectedVlessBlock, '');
    writeFileSync(target, before);

    const result = runPatch(target);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /expected VLESS addUsersToInbound block exactly once/);
    assert.equal(readFileSync(target, 'utf8'), before);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('patch fails closed when rerun against an already patched source', () => {
  const { dir, target } = makeTempFixture();
  try {
    const firstResult = runPatch(target);
    assert.equal(firstResult.status, 0, firstResult.stderr);
    const beforeSecondRun = readFileSync(target, 'utf8');

    const secondResult = runPatch(target);
    assert.notEqual(secondResult.status, 0);
    assert.match(secondResult.stderr, /expected VLESS addUsersToInbound block exactly once/);
    assert.equal(readFileSync(target, 'utf8'), beforeSecondRun);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
