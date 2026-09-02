import type { Request } from 'express';

import { createZodDto } from 'nestjs-zod';
import { z } from 'zod';

import {
    Body,
    Controller,
    Headers,
    HttpCode,
    HttpStatus,
    Param,
    ParseUUIDPipe,
    Post,
    Req,
} from '@nestjs/common';
import { ApiExcludeController } from '@nestjs/swagger';

import { IpAddress } from '@common/decorators/get-ip';

import {
    CYBERVPN_NODE_SSH_BROKER_HEADER,
    ICybervpnNodeSshTicketMaterial,
    isCybervpnNodeSshUuid,
} from './cybervpn-node-ssh-broker.credentials';
import { CybervpnNodeSshBrokerService } from './cybervpn-node-ssh-broker.service';

const createCybervpnNodeSshTicketBodySchema = z
    .object({
        actorReference: z
            .uuid()
            .refine(isCybervpnNodeSshUuid, 'actorReference must be a versioned UUID'),
    })
    .strict();

class CreateCybervpnNodeSshTicketBodyDto extends createZodDto(
    createCybervpnNodeSshTicketBodySchema,
) {}

interface ICreateCybervpnNodeSshTicketResponse {
    response: ICybervpnNodeSshTicketMaterial;
}

@ApiExcludeController()
@Controller('cybervpn/node-ssh')
export class CybervpnNodeSshBrokerController {
    constructor(private readonly brokerService: CybervpnNodeSshBrokerService) {}

    @Post('tickets/:uuid')
    @HttpCode(HttpStatus.CREATED)
    async createTicket(
        @Param('uuid', new ParseUUIDPipe()) nodeUuid: string,
        @Body() body: CreateCybervpnNodeSshTicketBodyDto,
        @IpAddress() clientIp: string,
        @Req() request: Request,
        @Headers(CYBERVPN_NODE_SSH_BROKER_HEADER) brokerSecret: string | undefined,
    ): Promise<ICreateCybervpnNodeSshTicketResponse> {
        const response = await this.brokerService.createTicket(
            nodeUuid,
            body.actorReference,
            clientIp,
            request.socket.remoteAddress,
            brokerSecret,
        );
        return { response };
    }
}
