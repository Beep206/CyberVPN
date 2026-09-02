#!/usr/bin/env node
import { readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';

const sourceRoot = resolve(
  process.env.REMNAWAVE_BACKEND_SOURCE_ROOT ?? '/opt/remnawave-backend',
);

const configPath = join(sourceRoot, 'src/common/config/app-config/config.schema.ts');
const modulePath = join(sourceRoot, 'src/modules/node-ssh/node-ssh.module.ts');
const gatewayPath = join(
  sourceRoot,
  'src/modules/node-ssh/ssh/ssh-terminal.gateway.ts',
);

const configAppSecretBlock = `        APP_SECRET: z
            .string()
            .refine((val) => val !== 'change_me', 'APP_SECRET cannot be set to "change_me"'),
        JWT_AUTH_LIFETIME: z`;

const configBrokerBlock = `        APP_SECRET: z
            .string()
            .refine((val) => val !== 'change_me', 'APP_SECRET cannot be set to "change_me"'),
        CYBERVPN_NODE_SSH_BROKER_ENABLED: booleanString('false'),
        CYBERVPN_NODE_SSH_BROKER_SECRET: z.string().optional(),
        CYBERVPN_NODE_SSH_BROKER_TRUSTED_PROXY_RANGES: z.string().optional(),
        JWT_AUTH_LIFETIME: z`;

const configSuperRefineAnchor = `    .superRefine((data, ctx) => {
        if (!data.REDIS_SOCKET && (!data.REDIS_HOST || !data.REDIS_PORT)) {`;

const configSuperRefinePatched = `    .superRefine((data, ctx) => {
        if (data.CYBERVPN_NODE_SSH_BROKER_ENABLED) {
            if (!data.CYBERVPN_NODE_SSH_BROKER_SECRET) {
                ctx.issues.push({
                    input: data,
                    code: 'custom',
                    message:
                        'CYBERVPN_NODE_SSH_BROKER_SECRET is required when the broker is enabled',
                    path: ['CYBERVPN_NODE_SSH_BROKER_SECRET'],
                });
            } else if (!/^[a-f0-9]{128}$/.test(data.CYBERVPN_NODE_SSH_BROKER_SECRET)) {
                ctx.issues.push({
                    input: data,
                    code: 'custom',
                    message:
                        'CYBERVPN_NODE_SSH_BROKER_SECRET must be 64 random bytes encoded as lowercase hex',
                    path: ['CYBERVPN_NODE_SSH_BROKER_SECRET'],
                });
            } else if (data.CYBERVPN_NODE_SSH_BROKER_SECRET === data.APP_SECRET) {
                ctx.issues.push({
                    input: data,
                    code: 'custom',
                    message: 'CYBERVPN_NODE_SSH_BROKER_SECRET must be distinct from APP_SECRET',
                    path: ['CYBERVPN_NODE_SSH_BROKER_SECRET'],
                });
            }

            if (!data.CYBERVPN_NODE_SSH_BROKER_TRUSTED_PROXY_RANGES) {
                ctx.issues.push({
                    input: data,
                    code: 'custom',
                    message:
                        'CYBERVPN_NODE_SSH_BROKER_TRUSTED_PROXY_RANGES is required when the broker is enabled',
                    path: ['CYBERVPN_NODE_SSH_BROKER_TRUSTED_PROXY_RANGES'],
                });
            }
        }

        if (!data.REDIS_SOCKET && (!data.REDIS_HOST || !data.REDIS_PORT)) {`;

const expectedModule = `import { Module } from '@nestjs/common';
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

const patchedModule = `import { Module } from '@nestjs/common';
import { CqrsModule } from '@nestjs/cqrs';

import { CybervpnNodeSshBrokerController } from './cybervpn-node-ssh-broker.controller';
import { CybervpnNodeSshBrokerService } from './cybervpn-node-ssh-broker.service';
import { NodeSshService } from './node-ssh.service';
import { SshTerminalGateway } from './ssh/ssh-terminal.gateway';
import { VaultOprfService } from './vault-oprf.service';

@Module({
    imports: [CqrsModule],
    controllers: [CybervpnNodeSshBrokerController],
    providers: [NodeSshService, SshTerminalGateway, VaultOprfService, CybervpnNodeSshBrokerService],
})
export class NodeSshModule {}
`;

const gatewayServiceImport = `import { IAdminIdentity, ISshCredentials } from '../interfaces';
import { NodeSshService } from '../node-ssh.service';`;

const gatewayBrokerImport = `import {
    CYBERVPN_NODE_SSH_WS_PATH,
    CYBERVPN_NODE_SSH_WS_PROTOCOL,
    parseCybervpnNodeSshWsCredentials,
} from '../cybervpn-node-ssh-broker.credentials';
import { CybervpnNodeSshBrokerService } from '../cybervpn-node-ssh-broker.service';
import { IAdminIdentity, ISshCredentials } from '../interfaces';
import { NodeSshService } from '../node-ssh.service';`;

const gatewayConstructor = `        private readonly nodeSshService: NodeSshService,
        private readonly queryBus: QueryBus,`;

const gatewayBrokerConstructor = `        private readonly nodeSshService: NodeSshService,
        private readonly cybervpnNodeSshBrokerService: CybervpnNodeSshBrokerService,
        private readonly queryBus: QueryBus,`;

const gatewayProtocolHandler = `            handleProtocols: (protocols) =>
                protocols.has(SSH_TERMINAL_WS_PROTOCOL) ? SSH_TERMINAL_WS_PROTOCOL : false,`;

const gatewayBrokerProtocolHandler = `            handleProtocols: (protocols) => {
                return protocols.has(CYBERVPN_NODE_SSH_WS_PROTOCOL)
                    ? CYBERVPN_NODE_SSH_WS_PROTOCOL
                    : false;
            },`;

const gatewayPathAndProxyBlock = `        const url = new URL(request.url ?? '', 'http://localhost');
        if (url.pathname !== SSH_TERMINAL_WS_PATH) {
            return reject(socket, 404, 'Not Found');
        }

        if (!isDevelopment() && !isBehindTrustedProxy(request)) {
            this.logger.error('Reverse proxy and HTTPS are required.');
            return reject(socket, 400, 'Bad Request');
        }

        const credentials = parseCredentials(request.headers['sec-websocket-protocol']);`;

const gatewayBrokerPathAndProxyBlock = `        const url = new URL(request.url ?? '', 'http://localhost');
        if (url.pathname !== SSH_TERMINAL_WS_PATH && url.pathname !== CYBERVPN_NODE_SSH_WS_PATH) {
            return reject(socket, 404, 'Not Found');
        }

        // The custom image deliberately disables upstream browser SSH.  Every
        // usable session must cross CyberVPN's trusted-admin, fresh-MFA,
        // one-time-ticket and audit boundary instead of accepting a broad
        // Remnawave ADMIN JWT.
        if (url.pathname === SSH_TERMINAL_WS_PATH) {
            return reject(socket, 404, 'Not Found');
        }

        if (!isDevelopment() && !isBehindTrustedProxy(request)) {
            this.logger.error('Reverse proxy and HTTPS are required.');
            return reject(socket, 400, 'Bad Request');
        }

        if (url.pathname === CYBERVPN_NODE_SSH_WS_PATH) {
            return this.handleCybervpnUpgrade(request, socket, head, server);
        }

        const credentials = parseCredentials(request.headers['sec-websocket-protocol']);`;

const gatewayVerifyAdminAnchor = `    private async verifyAdminToken(token: string): Promise<IAdminIdentity | null> {`;

const gatewayBrokerHandler = `    private async handleCybervpnUpgrade(
        request: IncomingMessage,
        socket: Duplex,
        head: Buffer,
        server: WebSocketServer,
    ): Promise<void> {
        if (!this.cybervpnNodeSshBrokerService.isEnabled()) {
            return reject(socket, 404, 'Not Found');
        }

        const credentials = parseCybervpnNodeSshWsCredentials(
            request.headers['sec-websocket-protocol'],
        );
        if (!credentials) {
            return reject(socket, 401, 'Unauthorized');
        }

        const clientIp = getClientIp(request, [REMNAWAVE_REAL_IP_HEADER]) ?? '0.0.0.0';
        const payload = await this.cybervpnNodeSshBrokerService.consumeTicket(
            credentials,
            clientIp,
            request.socket.remoteAddress,
        );
        if (!payload) {
            return reject(socket, 401, 'Unauthorized');
        }

        const node = await this.queryBus.execute(new GetNodeByUuidQuery(payload.nodeUuid));
        if (!node.isOk) {
            return reject(socket, 404, 'Not Found');
        }

        if (this.sessions.size >= MAX_CONCURRENT_SESSIONS) {
            this.logger.warn(\`Refusing SSH session: \${MAX_CONCURRENT_SESSIONS} already open.\`);
            return reject(socket, 503, 'Service Unavailable');
        }

        const brokerIdentity: IAdminIdentity = {
            username: \`cybervpn:\${payload.actorReference}\`,
            uuid: payload.actorReference,
        };

        server.handleUpgrade(request, socket, head, (ws: WebSocket) => {
            try {
                this.startSession(ws, node.response, brokerIdentity);
            } catch (error) {
                this.logger.error(error);
                ws.terminate();
            }
        });
    }

${gatewayVerifyAdminAnchor}`;

function countOccurrences(source, needle) {
  return source.split(needle).length - 1;
}

function replaceExactly(source, expected, replacement, label) {
  const occurrences = countOccurrences(source, expected);
  if (occurrences !== 1) {
    fail(`expected ${label} exactly once, found ${occurrences}`);
  }
  return source.replace(expected, replacement);
}

function fail(message) {
  console.error(`CyberVPN scoped Node SSH source patch failed: ${message}`);
  process.exit(1);
}

function load(path) {
  const original = readFileSync(path, 'utf8');
  return {
    original,
    normalized: original.replaceAll('\r\n', '\n'),
    usesCrlf: original.includes('\r\n'),
  };
}

const config = load(configPath);
const moduleSource = load(modulePath);
const gateway = load(gatewayPath);

let patchedConfig = replaceExactly(
  config.normalized,
  configAppSecretBlock,
  configBrokerBlock,
  'Remnawave 3.4.2 APP_SECRET config block',
);
patchedConfig = replaceExactly(
  patchedConfig,
  configSuperRefineAnchor,
  configSuperRefinePatched,
  'Remnawave 3.4.2 config superRefine anchor',
);

if (moduleSource.normalized !== expectedModule) {
  fail('Remnawave 3.4.2 NodeSshModule source drifted');
}

let patchedGateway = replaceExactly(
  gateway.normalized,
  gatewayServiceImport,
  gatewayBrokerImport,
  'Remnawave 3.4.2 Node SSH gateway service import',
);
patchedGateway = replaceExactly(
  patchedGateway,
  gatewayConstructor,
  gatewayBrokerConstructor,
  'Remnawave 3.4.2 Node SSH gateway constructor',
);
patchedGateway = replaceExactly(
  patchedGateway,
  gatewayProtocolHandler,
  gatewayBrokerProtocolHandler,
  'Remnawave 3.4.2 native WebSocket protocol handler',
);
patchedGateway = replaceExactly(
  patchedGateway,
  gatewayPathAndProxyBlock,
  gatewayBrokerPathAndProxyBlock,
  'Remnawave 3.4.2 native WebSocket path and proxy block',
);
patchedGateway = replaceExactly(
  patchedGateway,
  gatewayVerifyAdminAnchor,
  gatewayBrokerHandler,
  'Remnawave 3.4.2 admin JWT verifier anchor',
);

if (countOccurrences(patchedModule, 'NodeSshController') !== 0) {
  fail('native Remnawave Node SSH controller remains registered');
}
if (countOccurrences(patchedGateway, 'return reject(socket, 404, \'Not Found\');') < 2) {
  fail('native Remnawave Node SSH WebSocket denial is missing');
}
if (countOccurrences(patchedGateway, 'verify(token, this.configService.getOrThrow(\'APP_SECRET\'))') !== 1) {
  fail('pinned upstream admin JWT verifier drifted before the native SSH denial boundary');
}
if (countOccurrences(patchedGateway, 'parseCredentials(request.headers[\'sec-websocket-protocol\'])') !== 1) {
  fail('pinned upstream WebSocket parser drifted before the native SSH denial boundary');
}
if (countOccurrences(patchedGateway, 'this.handleCybervpnUpgrade(request, socket, head, server)') !== 1) {
  fail('scoped CyberVPN WebSocket branch is missing or ambiguous');
}

const changes = [
  [configPath, config, patchedConfig],
  [modulePath, moduleSource, patchedModule],
  [gatewayPath, gateway, patchedGateway],
];

const temporaryPaths = [];
try {
  for (const [path, metadata, patched] of changes) {
    const rendered = metadata.usesCrlf ? patched.replaceAll('\n', '\r\n') : patched;
    const temporaryPath = join(dirname(path), `.${process.pid}.${temporaryPaths.length}.tmp`);
    writeFileSync(temporaryPath, rendered);
    temporaryPaths.push([temporaryPath, path]);
  }
  for (const [temporaryPath, path] of temporaryPaths) {
    renameSync(temporaryPath, path);
  }
} catch (error) {
  for (const [temporaryPath] of temporaryPaths) {
    rmSync(temporaryPath, { force: true });
  }
  throw error;
}

console.log(`Patched Remnawave scoped Node SSH broker in ${sourceRoot}`);
