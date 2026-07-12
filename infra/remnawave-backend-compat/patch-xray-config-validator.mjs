#!/usr/bin/env node
import { readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

const targetPath =
  process.env.XRAY_CONFIG_VALIDATOR_PATH ??
  '/opt/app/dist/src/common/helpers/xray-config/xray-config.validator.js';

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

const patchedVlessBlock = `            case 'vless': {
                if (!inbound.settings) {
                    inbound.settings = {};
                }
                inbound.settings.clients ??= [];
                const vlessFlow = (0, get_vless_flow_1.getVlessFlow)(inbound);
                delete inbound.settings.flow;
                for (const user of users) {
                    const client = {
                        id: user.vlessUuid,
                        email: user.tId.toString(),
                    };
                    if (vlessFlow) {
                        client.flow = vlessFlow;
                    }
                    inbound.settings.clients.push(client);
                }
                break;
            }`;

const requiredExistingFlowCall = '(0, get_vless_flow_1.getVlessFlow)(inbound)';
const requiredPatchedLine =
  'const vlessFlow = (0, get_vless_flow_1.getVlessFlow)(inbound);';
const requiredFlowCleanupLine = 'delete inbound.settings.flow;';

function countOccurrences(source, needle) {
  return source.split(needle).length - 1;
}

function fail(message) {
  console.error(`CyberVPN Remnawave backend compatibility patch failed: ${message}`);
  process.exit(1);
}

const source = readFileSync(targetPath, 'utf8');
const expectedBlockCount = countOccurrences(source, expectedVlessBlock);

if (expectedBlockCount !== 1) {
  fail(
    `expected VLESS addUsersToInbound block exactly once in ${targetPath}, found ${expectedBlockCount}`,
  );
}

const existingFlowCallCount = countOccurrences(source, requiredExistingFlowCall);
if (existingFlowCallCount !== 1) {
  fail(
    `expected upstream getVlessFlow call exactly once before patch in ${targetPath}, found ${existingFlowCallCount}`,
  );
}

const patched = source.replace(expectedVlessBlock, patchedVlessBlock);

if (countOccurrences(patched, expectedVlessBlock) !== 0) {
  fail('source pattern remains after patch');
}

if (countOccurrences(patched, patchedVlessBlock) !== 1) {
  fail('patched VLESS block was not written exactly once');
}

if (countOccurrences(patched, requiredPatchedLine) !== 1) {
  fail('patched per-client getVlessFlow assignment is missing or ambiguous');
}

if (countOccurrences(patched, requiredFlowCleanupLine) !== 1) {
  fail('patched top-level VLESS flow cleanup is missing or ambiguous');
}

if (countOccurrences(patched, requiredExistingFlowCall) !== 2) {
  fail('compiled file does not contain the expected upstream and per-client getVlessFlow calls');
}

const temporaryPath = join(dirname(targetPath), `.xray-config.validator.js.${process.pid}.tmp`);
try {
  writeFileSync(temporaryPath, patched);
  renameSync(temporaryPath, targetPath);
} catch (error) {
  rmSync(temporaryPath, { force: true });
  throw error;
}
console.log(`Patched Remnawave Xray config validator: ${targetPath}`);
