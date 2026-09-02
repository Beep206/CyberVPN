import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const testDir = dirname(fileURLToPath(import.meta.url));
const compatDir = resolve(testDir, '..');
const patchScript = resolve(testDir, '..', 'patch-node-ssh-scoped-broker.mjs');

const upstreamModule = `import { Module } from '@nestjs/common';
import { CqrsModule } from '@nestjs/cqrs';

import { NodeSshController } from './node-ssh.controller';
import { NodeSshService } from './node-ssh.service';
import { SshTerminalGateway } from './ssh/ssh-terminal.gateway';
import { VaultOprfService } from './vault-oprf.service';

@Module({
    imports: [CqrsModule],
    controllers: [NodeSshController],
    providers: [NodeSshService, SshTerminalGateway, VaultOprfService],
})
export class NodeSshModule {}
`;

const upstreamConfig = `const booleanString = () => true;
export const configSchema = z
    .object({
        APP_SECRET: z
            .string()
            .refine((val) => val !== 'change_me', 'APP_SECRET cannot be set to "change_me"'),
        JWT_AUTH_LIFETIME: z.string(),
    })
    .superRefine((data, ctx) => {
        if (!data.REDIS_SOCKET && (!data.REDIS_HOST || !data.REDIS_PORT)) {
            ctx.issues.push({ code: 'custom' });
        }
    });
`;

const upstreamGateway = `import { IAdminIdentity, ISshCredentials } from '../interfaces';
import { NodeSshService } from '../node-ssh.service';

class SshTerminalGateway {
    constructor(
        private readonly nodeSshService: NodeSshService,
        private readonly queryBus: QueryBus,
    ) {}

    configure() {
        return {
            handleProtocols: (protocols) =>
                protocols.has(SSH_TERMINAL_WS_PROTOCOL) ? SSH_TERMINAL_WS_PROTOCOL : false,
        };
    }

    private async handleUpgrade(request, socket, head) {
        const server = this.server;
        const url = new URL(request.url ?? '', 'http://localhost');
        if (url.pathname !== SSH_TERMINAL_WS_PATH) {
            return reject(socket, 404, 'Not Found');
        }

        if (!isDevelopment() && !isBehindTrustedProxy(request)) {
            this.logger.error('Reverse proxy and HTTPS are required.');
            return reject(socket, 400, 'Bad Request');
        }

        const credentials = parseCredentials(request.headers['sec-websocket-protocol']);
        return credentials;
    }

    private async verifyAdminToken(token: string): Promise<IAdminIdentity | null> {
        const payload = verify(token, this.configService.getOrThrow('APP_SECRET'));
        return payload;
    }
}
`;

function makeFixture() {
  const root = mkdtempSync(join(tmpdir(), 'cybervpn-remnawave-ssh-patch-'));
  const configPath = join(root, 'src', 'common', 'config', 'app-config', 'config.schema.ts');
  const modulePath = join(root, 'src', 'modules', 'node-ssh', 'node-ssh.module.ts');
  const gatewayPath = join(
    root,
    'src',
    'modules',
    'node-ssh',
    'ssh',
    'ssh-terminal.gateway.ts',
  );
  for (const path of [configPath, modulePath, gatewayPath]) {
    mkdirSync(dirname(path), { recursive: true });
  }
  writeFileSync(configPath, upstreamConfig);
  writeFileSync(modulePath, upstreamModule);
  writeFileSync(gatewayPath, upstreamGateway);
  return { root, configPath, modulePath, gatewayPath };
}

function runPatch(root) {
  return spawnSync(process.execPath, [patchScript], {
    env: { ...process.env, REMNAWAVE_BACKEND_SOURCE_ROOT: root },
    encoding: 'utf8',
  });
}

test('patch leaves only the scoped broker controller and disables native browser SSH', () => {
  const fixture = makeFixture();
  try {
    const result = runPatch(fixture.root);
    assert.equal(result.status, 0, result.stderr);

    const config = readFileSync(fixture.configPath, 'utf8');
    const moduleSource = readFileSync(fixture.modulePath, 'utf8');
    const gateway = readFileSync(fixture.gatewayPath, 'utf8');

    assert.match(config, /CYBERVPN_NODE_SSH_BROKER_ENABLED/);
    assert.match(config, /CYBERVPN_NODE_SSH_BROKER_TRUSTED_PROXY_RANGES/);
    assert.match(config, /\^\[a-f0-9\]\{128\}\$/);
    assert.match(config, /must be distinct from APP_SECRET/);
    assert.match(moduleSource, /CybervpnNodeSshBrokerController/);
    assert.match(moduleSource, /CybervpnNodeSshBrokerService/);
    assert.doesNotMatch(moduleSource, /NodeSshController/);
    assert.match(gateway, /CYBERVPN_NODE_SSH_WS_PATH/);
    assert.match(gateway, /handleCybervpnUpgrade/);
    assert.match(gateway, /parseCybervpnNodeSshWsCredentials/);
    assert.match(gateway, /request\.socket\.remoteAddress/);
    assert.doesNotMatch(
      gateway,
      /protocols\.has\(SSH_TERMINAL_WS_PROTOCOL\)\s*\?\s*SSH_TERMINAL_WS_PROTOCOL/,
    );

    const nativeDenial = gateway.indexOf('if (url.pathname === SSH_TERMINAL_WS_PATH)');
    const nativeCredentials = gateway.indexOf(
      "parseCredentials(request.headers['sec-websocket-protocol'])",
    );
    assert.notEqual(nativeDenial, -1);
    assert.notEqual(nativeCredentials, -1);
    assert.ok(nativeDenial < nativeCredentials);

    assert.equal(
      (gateway.match(/verify\(token, this\.configService\.getOrThrow\('APP_SECRET'\)\)/g) ?? [])
        .length,
      1,
    );
    assert.equal(
      (gateway.match(/parseCredentials\(request\.headers\['sec-websocket-protocol'\]\)/g) ?? [])
        .length,
      1,
    );
  } finally {
    rmSync(fixture.root, { recursive: true, force: true });
  }
});

test('patch is not silently repeatable against an already patched tree', () => {
  const fixture = makeFixture();
  try {
    assert.equal(runPatch(fixture.root).status, 0);
    const before = readFileSync(fixture.gatewayPath, 'utf8');
    const result = runPatch(fixture.root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /APP_SECRET config block exactly once, found 0/);
    assert.equal(readFileSync(fixture.gatewayPath, 'utf8'), before);
  } finally {
    rmSync(fixture.root, { recursive: true, force: true });
  }
});

test('patch fails closed and writes nothing when native admin JWT source drifts', () => {
  const fixture = makeFixture();
  try {
    const drifted = upstreamGateway.replace(
      "verify(token, this.configService.getOrThrow('APP_SECRET'))",
      "verify(token, this.configService.getOrThrow('SOME_OTHER_SECRET'))",
    );
    writeFileSync(fixture.gatewayPath, drifted);
    const beforeConfig = readFileSync(fixture.configPath, 'utf8');
    const beforeModule = readFileSync(fixture.modulePath, 'utf8');

    const result = runPatch(fixture.root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /upstream admin JWT verifier drifted/);
    assert.equal(readFileSync(fixture.configPath, 'utf8'), beforeConfig);
    assert.equal(readFileSync(fixture.modulePath, 'utf8'), beforeModule);
    assert.equal(readFileSync(fixture.gatewayPath, 'utf8'), drifted);
  } finally {
    rmSync(fixture.root, { recursive: true, force: true });
  }
});

test('patch fails closed when NodeSshModule registration drifts', () => {
  const fixture = makeFixture();
  try {
    const drifted = upstreamModule.replace(
      'controllers: [NodeSshController]',
      'controllers: [NodeSshController, UnexpectedController]',
    );
    writeFileSync(fixture.modulePath, drifted);

    const result = runPatch(fixture.root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /NodeSshModule source drifted/);
    assert.equal(readFileSync(fixture.modulePath, 'utf8'), drifted);
  } finally {
    rmSync(fixture.root, { recursive: true, force: true });
  }
});

test('patch fails closed when the config validation anchor drifts', () => {
  const fixture = makeFixture();
  try {
    const drifted = upstreamConfig.replace('.superRefine((data, ctx) => {', '.refine((data) => {');
    writeFileSync(fixture.configPath, drifted);

    const result = runPatch(fixture.root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /config superRefine anchor exactly once, found 0/);
    assert.equal(readFileSync(fixture.configPath, 'utf8'), drifted);
  } finally {
    rmSync(fixture.root, { recursive: true, force: true });
  }
});

test('pinned image build applies source overlays and never reuses broad auth credentials', () => {
  const dockerfile = readFileSync(resolve(compatDir, 'Dockerfile'), 'utf8');
  const overlayFiles = [
    'cybervpn-node-ssh-broker.controller.ts',
    'cybervpn-node-ssh-broker.credentials.ts',
    'cybervpn-node-ssh-broker.service.ts',
  ].map((name) =>
    readFileSync(resolve(compatDir, 'overlay', 'src', 'modules', 'node-ssh', name), 'utf8'),
  );
  const productionOverlay = overlayFiles.join('\n');

  assert.match(
    dockerfile,
    /REMNAWAVE_BACKEND_COMMIT=f8ad8ad3410252215ca7b2e429d157bd275ec564/,
  );
  assert.match(dockerfile, /COPY overlay\/ \/opt\/remnawave-backend\//);
  assert.match(dockerfile, /patch-node-ssh-scoped-broker\.mjs/);
  assert.match(dockerfile, /npm ci --prefer-offline --no-audit --no-fund/);
  assert.match(dockerfile, /npm run lint/);
  assert.match(dockerfile, /npm run build/);
  assert.match(
    dockerfile,
    /net\.cybervpn\.remnawave\.node-ssh-broker="scoped-one-time-native-disabled-v2"/,
  );

  for (const forbiddenCredentialClass of [
    'APP_SECRET',
    'REMNAWAVE_TOKEN',
    'Authorization',
    'JwtDefaultGuard',
    'verify(',
  ]) {
    assert.equal(productionOverlay.includes(forbiddenCredentialClass), false);
  }
  assert.match(productionOverlay, /CYBERVPN_NODE_SSH_BROKER_SECRET/);
  assert.match(productionOverlay, /getDelString/);
});
