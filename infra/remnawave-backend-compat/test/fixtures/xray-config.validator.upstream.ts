function getVlessFlow(inbound: { settings?: { flow?: string }; testFlow?: string }): string {
    if (inbound.settings?.flow !== undefined) return inbound.settings.flow;
    return inbound.testFlow ?? '';
}

type TestUser = {
    id: bigint;
    vlessUuid: string;
    trojanPassword?: string;
};

type TestInbound = {
    protocol: string;
    settings?: {
        clients?: Array<Record<string, unknown>>;
        flow?: string;
    };
    testFlow?: string;
};

export class XRayConfigHarness {
    public cleanInboundClients(inbound: TestInbound): void {
        inbound.settings ??= {};
        inbound.settings!.flow = getVlessFlow(inbound);
    }

    public addUsersToInbound(inbound: TestInbound, users: TestUser[]): void {
        switch (inbound.protocol) {
            case 'trojan':
                if (!inbound.settings) {
                    inbound.settings = {};
                }
                inbound.settings.clients ??= [];

                for (const user of users) {
                    inbound.settings.clients.push({
                        password: user.trojanPassword,
                        email: user.id.toString(),
                        id: user.vlessUuid,
                    });
                }
                break;

            case 'vless':
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
                break;

            case 'hysteria':
                if (!inbound.settings) {
                    inbound.settings = {};
                }
                inbound.settings.clients ??= [];

                for (const user of users) {
                    inbound.settings.clients.push({
                        id: user.vlessUuid,
                        auth: user.vlessUuid,
                        email: user.id.toString(),
                    });
                }
                break;

            case 'shadowsocks':
                if (!inbound.settings) {
                    inbound.settings = {};
                }
                inbound.settings.clients ??= [];

                for (const user of users) {
                    inbound.settings.clients.push({
                        password: 'test-password',
                        email: user.id.toString(),
                        id: user.vlessUuid,
                    });
                }
                break;

            default:
                break;
        }
    }
}
