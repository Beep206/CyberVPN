#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const sourceRoot = process.env.REMNAWAVE_NODE_SOURCE_ROOT ?? '/opt/remnawave-node';
const proofPath = process.env.REMNAWAVE_NODE_PROOF_PATH ?? '/tmp/cybervpn-node-3.4.1-verified';

function fail(message) {
  console.error(`Remnawave Node 3.4.1 verification failed: ${message}`);
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

function extractMethod(source, signature) {
  const start = source.indexOf(signature);
  if (start < 0) {
    fail(`required method ${JSON.stringify(signature)} is missing`);
  }

  const nextMethod = source.indexOf('\n    public async ', start + signature.length);
  return source.slice(start, nextMethod < 0 ? source.length : nextMethod);
}

const packageJson = JSON.parse(read('package.json'));
const contractPackage = JSON.parse(read('libs/contract/package.json'));
if (packageJson.version !== '3.4.1') fail('runtime package version is not 3.4.1');
if (packageJson.dependencies?.zod !== '4.5.4') fail('runtime Zod must be 4.5.4');
if (packageJson.dependencies?.['@remnawave/node-plugins'] !== '0.8.2') {
  fail('node-plugins must be 0.8.2');
}
if (contractPackage.version !== '3.4.1' || contractPackage.dependencies?.zod !== '4.5.4') {
  fail('node-contract must be 3.4.1 on Zod 4.5.4');
}

const main = read('src/main.ts');
requireOnce(main, "import 'zod/compile';", 'compiled Zod activation');

const handler = read('src/modules/handler/handler.service.ts');
const addUserMethod = extractMethod(handler, 'public async addUser(');
requireOnce(
  addUserMethod,
  'new DropConnectionsEvent(userIps)',
  'scoped credential-change drop in addUser',
);
requireOrder(
  addUserMethod,
  [
    'const userId = requestData[0].username;',
    'let userIps: string[] | null = null;',
    'if (hashData.prevVlessUuid) {\n                userIps = await this.getUserIps(userId);',
    'await this.xtlsApi.handler.removeUser(tag, userId);',
    'if (userIps && hashData.prevVlessUuid) {',
    'new DropConnectionsEvent(userIps)',
    'for (const item of requestData) {\n                let tempRes = null;',
  ],
  'capture/remove/drop/re-add credential sequence',
);
if (addUserMethod.includes('new DropConnectionsEvent(await this.getUserIps(')) {
  fail('credential rotation must not perform an unscoped late IP lookup');
}

writeFileSync(proofPath, 'node-3.4.1-source-verified\n', { mode: 0o444 });
console.log('Verified Remnawave Node 3.4.1 dependency and scoped credential-drop fixes.');
