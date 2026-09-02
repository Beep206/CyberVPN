#!/usr/bin/env node
import { readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

const targetPath =
  process.env.XRAY_CONFIG_VALIDATOR_PATH ??
  '/opt/remnawave-backend/src/common/helpers/xray-config/xray-config.validator.ts';

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

const patchedVlessBlock = `            case 'vless': {
                if (!inbound.settings) {
                    inbound.settings = {};
                }
                inbound.settings.clients ??= [];

                const vlessFlow = getVlessFlow(inbound);
                delete inbound.settings.flow;

                for (const user of users) {
                    inbound.settings.clients.push({
                        id: user.vlessUuid,
                        email: user.id.toString(),
                        ...(vlessFlow ? { flow: vlessFlow } : {}),
                    });
                }
                break;
            }`;

const requiredUpstreamFlowLine = 'inbound.settings!.flow = getVlessFlow(inbound);';
const requiredPatchedLine = 'const vlessFlow = getVlessFlow(inbound);';
const requiredFlowCleanupLine = 'delete inbound.settings.flow;';

function countOccurrences(source, needle) {
  return source.split(needle).length - 1;
}

function fail(message) {
  console.error(`CyberVPN Remnawave backend compatibility patch failed: ${message}`);
  process.exit(1);
}

const originalSource = readFileSync(targetPath, 'utf8');
const sourceUsesCrlf = originalSource.includes('\r\n');
const source = originalSource.replaceAll('\r\n', '\n');
const expectedBlockCount = countOccurrences(source, expectedVlessBlock);

if (expectedBlockCount !== 1) {
  fail(
    `expected 3.4.2 TypeScript VLESS addUsersToInbound block exactly once in ${targetPath}, found ${expectedBlockCount}`,
  );
}

if (countOccurrences(source, requiredUpstreamFlowLine) !== 1) {
  fail(`expected the 3.4.2 cleanInboundClients flow assignment exactly once in ${targetPath}`);
}

if (countOccurrences(source, 'email: user.id.toString(),') !== 4) {
  fail(`expected the 3.4.2 numeric user id mapping for all four managed protocols in ${targetPath}`);
}

const patched = source.replace(expectedVlessBlock, patchedVlessBlock);

if (countOccurrences(patched, expectedVlessBlock) !== 0) {
  fail('upstream source pattern remains after patch');
}

if (countOccurrences(patched, patchedVlessBlock) !== 1) {
  fail('patched TypeScript VLESS block was not written exactly once');
}

if (countOccurrences(patched, requiredPatchedLine) !== 1) {
  fail('patched per-client getVlessFlow assignment is missing or ambiguous');
}

if (countOccurrences(patched, requiredFlowCleanupLine) !== 1) {
  fail('patched top-level VLESS flow cleanup is missing or ambiguous');
}

if (countOccurrences(patched, 'getVlessFlow(inbound)') !== 2) {
  fail('patched source does not contain the expected upstream and per-client flow calls');
}

const rendered = sourceUsesCrlf ? patched.replaceAll('\n', '\r\n') : patched;
const temporaryPath = join(dirname(targetPath), `.xray-config.validator.ts.${process.pid}.tmp`);
try {
  writeFileSync(temporaryPath, rendered);
  renameSync(temporaryPath, targetPath);
} catch (error) {
  rmSync(temporaryPath, { force: true });
  throw error;
}
console.log(`Patched Remnawave TypeScript Xray config validator: ${targetPath}`);
