import { createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto';
import { BlockList, isIP } from 'node:net';

export const CYBERVPN_NODE_SSH_BROKER_HEADER = 'x-cybervpn-node-ssh-broker-secret' as const;
export const CYBERVPN_NODE_SSH_WS_PATH = '/api/cybervpn/node-ssh/ws' as const;
export const CYBERVPN_NODE_SSH_WS_PROTOCOL = 'rw-cybervpn' as const;
export const CYBERVPN_NODE_SSH_TICKET_TTL_SECONDS = 10;
export const CYBERVPN_NODE_SSH_ISSUE_RATE_LIMIT = 60;
export const CYBERVPN_NODE_SSH_ISSUE_RATE_WINDOW_SECONDS = 60;

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{43}$/;
const BROKER_SECRET_PATTERN = /^[a-f0-9]{128}$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SHA256_PATTERN = /^[a-f0-9]{64}$/;

const TICKET_CACHE_DOMAIN = 'cybervpn/remnawave-node-ssh/cache-key/v1';
const TICKET_DIGEST_DOMAIN = 'cybervpn/remnawave-node-ssh/ticket-digest/v1';
const RATE_LIMIT_DOMAIN = 'cybervpn/remnawave-node-ssh/rate-limit/v1';
const MAX_TRUSTED_PROXY_RANGES = 32;

export interface ICybervpnNodeSshTrustedProxyPolicy {
    allows(socketPeerIp: string): boolean;
}

export interface ICybervpnNodeSshTicketStore {
    getDelString(key: string): Promise<null | string>;
    set(key: string, value: unknown, ttlSeconds?: number): Promise<void>;
}

export interface ICybervpnNodeSshTicketPayload {
    actorReference: string;
    clientIp: string;
    nodeUuid: string;
    ticketDigest: string;
}

export interface ICybervpnNodeSshTicketMaterial {
    credential: string;
    expiresInSeconds: number;
    path: typeof CYBERVPN_NODE_SSH_WS_PATH;
    protocol: typeof CYBERVPN_NODE_SSH_WS_PROTOCOL;
    ticket: string;
}

export interface ICybervpnNodeSshWsCredentials {
    credential: string;
    ticket: string;
}

export function isCybervpnNodeSshBrokerSecret(value: string): boolean {
    return BROKER_SECRET_PATTERN.test(value);
}

export function isCybervpnNodeSshUuid(value: string): boolean {
    return UUID_PATTERN.test(value);
}

export function cybervpnNodeSshBrokerSecretMatches(
    configuredSecret: string,
    presentedSecret: string | undefined,
): boolean {
    if (
        !isCybervpnNodeSshBrokerSecret(configuredSecret) ||
        presentedSecret === undefined ||
        !isCybervpnNodeSshBrokerSecret(presentedSecret)
    ) {
        return false;
    }

    const configuredDigest = createHash('sha256').update(configuredSecret, 'utf8').digest();
    const presentedDigest = createHash('sha256').update(presentedSecret, 'utf8').digest();
    return timingSafeEqual(configuredDigest, presentedDigest);
}

export function normalizeCybervpnNodeSshSourceIp(value: string): null | string {
    const normalized = value.trim();
    if (normalized.toLowerCase().startsWith('::ffff:')) {
        const mappedIpv4 = normalized.slice('::ffff:'.length);
        if (isIP(mappedIpv4) === 4) {
            return mappedIpv4;
        }
    }
    return isIP(normalized) === 0 ? null : normalized;
}

export function compileCybervpnNodeSshTrustedProxyPolicy(
    configuredRanges: string,
): ICybervpnNodeSshTrustedProxyPolicy {
    const ranges = configuredRanges.split(',').map((value) => value.trim());
    if (
        ranges.length === 0 ||
        ranges.length > MAX_TRUSTED_PROXY_RANGES ||
        ranges.some((value) => value.length === 0)
    ) {
        throw new Error('CyberVPN Node SSH trusted proxy ranges are invalid.');
    }

    const blockList = new BlockList();
    for (const range of ranges) {
        const separator = range.indexOf('/');
        if (separator === -1) {
            const address = normalizeCybervpnNodeSshSourceIp(range);
            const version = address === null ? 0 : isIP(address);
            if (
                address === null ||
                version === 0 ||
                !isPermittedTrustedProxyAddress(address, version)
            ) {
                throw new Error('CyberVPN Node SSH trusted proxy range is invalid.');
            }
            try {
                blockList.addAddress(address, version === 4 ? 'ipv4' : 'ipv6');
            } catch {
                throw new Error('CyberVPN Node SSH trusted proxy range is invalid.');
            }
            continue;
        }

        if (separator !== range.lastIndexOf('/')) {
            throw new Error('CyberVPN Node SSH trusted proxy range is invalid.');
        }
        const address = normalizeCybervpnNodeSshSourceIp(range.slice(0, separator));
        const prefixText = range.slice(separator + 1);
        const version = address === null ? 0 : isIP(address);
        const prefix = Number(prefixText);
        const maxPrefix = version === 4 ? 32 : 128;
        const minPrefix = version === 4 ? 24 : 64;
        if (
            address === null ||
            version === 0 ||
            !isPermittedTrustedProxyAddress(address, version) ||
            !/^\d{1,3}$/.test(prefixText) ||
            !Number.isInteger(prefix) ||
            prefix < minPrefix ||
            prefix > maxPrefix
        ) {
            throw new Error('CyberVPN Node SSH trusted proxy range is invalid.');
        }
        try {
            blockList.addSubnet(address, prefix, version === 4 ? 'ipv4' : 'ipv6');
        } catch {
            throw new Error('CyberVPN Node SSH trusted proxy range is invalid.');
        }
    }

    return {
        allows(socketPeerIp: string): boolean {
            const address = normalizeCybervpnNodeSshSourceIp(socketPeerIp);
            const version = address === null ? 0 : isIP(address);
            return (
                address !== null &&
                version !== 0 &&
                blockList.check(address, version === 4 ? 'ipv4' : 'ipv6')
            );
        },
    };
}

function isPermittedTrustedProxyAddress(address: string, version: number): boolean {
    if (version === 4) {
        const octets = address.split('.').map(Number);
        return (
            octets.length === 4 &&
            octets[0] > 0 &&
            octets[0] < 224 &&
            !(octets[0] === 169 && octets[1] === 254)
        );
    }

    const lowercase = address.toLowerCase();
    const isUnspecified = lowercase.replaceAll(':', '').replaceAll('0', '') === '';
    return !isUnspecified && !lowercase.startsWith('ff');
}

export function resolveCybervpnNodeSshTrustedSourceIp(
    trustedProxyPolicy: ICybervpnNodeSshTrustedProxyPolicy,
    forwardedClientIp: string,
    socketPeerIp: string | undefined,
): string | null {
    if (socketPeerIp === undefined || !trustedProxyPolicy.allows(socketPeerIp)) {
        return null;
    }
    return normalizeCybervpnNodeSshSourceIp(forwardedClientIp);
}

export function parseCybervpnNodeSshWsCredentials(
    header: string | string[] | undefined,
): ICybervpnNodeSshWsCredentials | null {
    const parts = (Array.isArray(header) ? header.join(',') : (header ?? ''))
        .split(',')
        .map((part) => part.trim())
        .filter(Boolean);

    if (
        parts.length !== 3 ||
        parts[0] !== CYBERVPN_NODE_SSH_WS_PROTOCOL ||
        !TOKEN_PATTERN.test(parts[1]) ||
        !TOKEN_PATTERN.test(parts[2])
    ) {
        return null;
    }

    return { ticket: parts[1], credential: parts[2] };
}

export async function issueCybervpnNodeSshTicket(
    store: ICybervpnNodeSshTicketStore,
    brokerSecret: string,
    scope: { actorReference: string; clientIp: string; nodeUuid: string },
): Promise<ICybervpnNodeSshTicketMaterial> {
    const normalizedClientIp = normalizeCybervpnNodeSshSourceIp(scope.clientIp);
    if (
        !isCybervpnNodeSshBrokerSecret(brokerSecret) ||
        !isCybervpnNodeSshUuid(scope.actorReference) ||
        !isCybervpnNodeSshUuid(scope.nodeUuid) ||
        normalizedClientIp === null
    ) {
        throw new Error('Invalid CyberVPN Node SSH ticket scope.');
    }

    const ticket = randomBytes(32).toString('base64url');
    const credential = randomBytes(32).toString('base64url');
    const payload: ICybervpnNodeSshTicketPayload = {
        actorReference: scope.actorReference,
        clientIp: normalizedClientIp,
        nodeUuid: scope.nodeUuid,
        ticketDigest: ticketDigest(brokerSecret, ticket),
    };

    await store.set(
        ticketCacheKey(brokerSecret, ticket, credential),
        payload,
        CYBERVPN_NODE_SSH_TICKET_TTL_SECONDS,
    );

    return {
        ticket,
        credential,
        path: CYBERVPN_NODE_SSH_WS_PATH,
        protocol: CYBERVPN_NODE_SSH_WS_PROTOCOL,
        expiresInSeconds: CYBERVPN_NODE_SSH_TICKET_TTL_SECONDS,
    };
}

export async function consumeCybervpnNodeSshTicket(
    store: ICybervpnNodeSshTicketStore,
    brokerSecret: string,
    credentials: ICybervpnNodeSshWsCredentials,
    clientIp: string,
): Promise<ICybervpnNodeSshTicketPayload | null> {
    if (
        !isCybervpnNodeSshBrokerSecret(brokerSecret) ||
        !TOKEN_PATTERN.test(credentials.ticket) ||
        !TOKEN_PATTERN.test(credentials.credential) ||
        normalizeCybervpnNodeSshSourceIp(clientIp) === null
    ) {
        return null;
    }

    const raw = await store.getDelString(
        ticketCacheKey(brokerSecret, credentials.ticket, credentials.credential),
    );
    if (raw === null) {
        return null;
    }

    const payload = parseTicketPayload(raw);
    if (
        payload === null ||
        payload.clientIp !== clientIp ||
        !safeEqualHex(payload.ticketDigest, ticketDigest(brokerSecret, credentials.ticket))
    ) {
        return null;
    }

    return payload;
}

export function cybervpnNodeSshRateLimitKey(brokerSecret: string, clientIp: string): string {
    return `cybervpn_ssh_broker_rate:${domainHmac(brokerSecret, RATE_LIMIT_DOMAIN, clientIp)}`;
}

function ticketCacheKey(brokerSecret: string, ticket: string, credential: string): string {
    return `cybervpn_ssh_broker_ticket:${domainHmac(
        brokerSecret,
        TICKET_CACHE_DOMAIN,
        ticket,
        credential,
    )}`;
}

function ticketDigest(brokerSecret: string, ticket: string): string {
    return domainHmac(brokerSecret, TICKET_DIGEST_DOMAIN, ticket);
}

function domainHmac(brokerSecret: string, domain: string, ...parts: string[]): string {
    const digest = createHmac('sha256', Buffer.from(brokerSecret, 'utf8'));
    digest.update(domain, 'utf8');
    for (const part of parts) {
        digest.update('\0', 'utf8');
        digest.update(part, 'utf8');
    }
    return digest.digest('hex');
}

function parseTicketPayload(raw: string): ICybervpnNodeSshTicketPayload | null {
    try {
        const value = JSON.parse(raw) as unknown;
        if (
            typeof value !== 'object' ||
            value === null ||
            Array.isArray(value) ||
            Object.keys(value).length !== 4
        ) {
            return null;
        }

        const record = value as Record<string, unknown>;
        if (
            typeof record.actorReference !== 'string' ||
            !isCybervpnNodeSshUuid(record.actorReference) ||
            typeof record.nodeUuid !== 'string' ||
            !isCybervpnNodeSshUuid(record.nodeUuid) ||
            typeof record.clientIp !== 'string' ||
            normalizeCybervpnNodeSshSourceIp(record.clientIp) === null ||
            typeof record.ticketDigest !== 'string' ||
            !SHA256_PATTERN.test(record.ticketDigest)
        ) {
            return null;
        }

        return {
            actorReference: record.actorReference,
            clientIp: record.clientIp,
            nodeUuid: record.nodeUuid,
            ticketDigest: record.ticketDigest,
        };
    } catch {
        return null;
    }
}

function safeEqualHex(left: string, right: string): boolean {
    if (!SHA256_PATTERN.test(left) || !SHA256_PATTERN.test(right)) {
        return false;
    }
    return timingSafeEqual(Buffer.from(left, 'hex'), Buffer.from(right, 'hex'));
}
