import {
    HttpException,
    HttpStatus,
    Injectable,
    NotFoundException,
    ServiceUnavailableException,
    UnauthorizedException,
} from '@nestjs/common';
import { QueryBus } from '@nestjs/cqrs';

import { TypedConfigService } from '@common/config/app-config';
import { RawCacheService } from '@common/raw-cache';

import { GetNodeByUuidQuery } from '@modules/nodes/queries/get-node-by-uuid';

import {
    consumeCybervpnNodeSshTicket,
    compileCybervpnNodeSshTrustedProxyPolicy,
    cybervpnNodeSshBrokerSecretMatches,
    cybervpnNodeSshRateLimitKey,
    CYBERVPN_NODE_SSH_ISSUE_RATE_LIMIT,
    CYBERVPN_NODE_SSH_ISSUE_RATE_WINDOW_SECONDS,
    ICybervpnNodeSshTicketMaterial,
    ICybervpnNodeSshTicketPayload,
    ICybervpnNodeSshTrustedProxyPolicy,
    ICybervpnNodeSshWsCredentials,
    issueCybervpnNodeSshTicket,
    resolveCybervpnNodeSshTrustedSourceIp,
} from './cybervpn-node-ssh-broker.credentials';

@Injectable()
export class CybervpnNodeSshBrokerService {
    private readonly trustedProxyPolicy: ICybervpnNodeSshTrustedProxyPolicy | null;

    constructor(
        private readonly configService: TypedConfigService,
        private readonly rawCacheService: RawCacheService,
        private readonly queryBus: QueryBus,
    ) {
        this.trustedProxyPolicy = this.isEnabled()
            ? compileCybervpnNodeSshTrustedProxyPolicy(
                  this.configService.get('CYBERVPN_NODE_SSH_BROKER_TRUSTED_PROXY_RANGES') ?? '',
              )
            : null;
    }

    public isEnabled(): boolean {
        return this.configService.get('CYBERVPN_NODE_SSH_BROKER_ENABLED');
    }

    public async createTicket(
        nodeUuid: string,
        actorReference: string,
        forwardedClientIp: string,
        socketPeerIp: string | undefined,
        presentedSecret: string | undefined,
    ): Promise<ICybervpnNodeSshTicketMaterial> {
        if (!this.isEnabled()) {
            throw new NotFoundException();
        }
        const normalizedClientIp = this.requireTrustedSourceIp(forwardedClientIp, socketPeerIp);
        const brokerSecret = this.requireAuthorizedSecret(presentedSecret);

        const attempts = await this.rawCacheService.incrementWithTtl(
            cybervpnNodeSshRateLimitKey(brokerSecret, normalizedClientIp),
            CYBERVPN_NODE_SSH_ISSUE_RATE_WINDOW_SECONDS,
        );
        if (attempts > CYBERVPN_NODE_SSH_ISSUE_RATE_LIMIT) {
            throw new HttpException(
                'Node SSH broker ticket rate limit reached.',
                HttpStatus.TOO_MANY_REQUESTS,
            );
        }

        const node = await this.queryBus.execute(new GetNodeByUuidQuery(nodeUuid));
        if (!node.isOk) {
            throw new NotFoundException('Node not found.');
        }

        return issueCybervpnNodeSshTicket(this.rawCacheService, brokerSecret, {
            actorReference,
            clientIp: normalizedClientIp,
            nodeUuid: node.response.uuid,
        });
    }

    public async consumeTicket(
        credentials: ICybervpnNodeSshWsCredentials,
        forwardedClientIp: string,
        socketPeerIp: string | undefined,
    ): Promise<ICybervpnNodeSshTicketPayload | null> {
        const brokerSecret = this.configuredSecret();
        if (brokerSecret === null) {
            return null;
        }

        const normalizedClientIp = this.resolveTrustedSourceIp(forwardedClientIp, socketPeerIp);
        if (normalizedClientIp === null) {
            return null;
        }

        return consumeCybervpnNodeSshTicket(
            this.rawCacheService,
            brokerSecret,
            credentials,
            normalizedClientIp,
        );
    }

    private requireAuthorizedSecret(presentedSecret: string | undefined): string {
        const brokerSecret = this.configuredSecret();
        if (brokerSecret === null) {
            throw new NotFoundException();
        }
        if (!cybervpnNodeSshBrokerSecretMatches(brokerSecret, presentedSecret)) {
            throw new UnauthorizedException();
        }
        return brokerSecret;
    }

    private configuredSecret(): string | null {
        if (!this.isEnabled()) {
            return null;
        }
        return this.configService.get('CYBERVPN_NODE_SSH_BROKER_SECRET') ?? null;
    }

    private requireTrustedSourceIp(
        forwardedClientIp: string,
        socketPeerIp: string | undefined,
    ): string {
        const clientIp = this.resolveTrustedSourceIp(forwardedClientIp, socketPeerIp);
        if (clientIp === null) {
            throw new ServiceUnavailableException('Node SSH broker source is not trusted.');
        }
        return clientIp;
    }

    private resolveTrustedSourceIp(
        forwardedClientIp: string,
        socketPeerIp: string | undefined,
    ): string | null {
        return this.trustedProxyPolicy === null
            ? null
            : resolveCybervpnNodeSshTrustedSourceIp(
                  this.trustedProxyPolicy,
                  forwardedClientIp,
                  socketPeerIp,
              );
    }
}
