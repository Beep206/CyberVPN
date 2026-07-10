"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.XRayConfigHarness = void 0;
const get_vless_flow_1 = {
    getVlessFlow(inbound) {
        return inbound.__testFlow ?? '';
    },
};
class XRayConfigHarness {
    cleanInboundClients(inbound) {
        if (!inbound.settings) {
            inbound.settings = {};
        }
        inbound.settings.flow = (0, get_vless_flow_1.getVlessFlow)(inbound);
    }
    addUsersToInbound(inbound, users) {
        switch (inbound.protocol) {
            case 'trojan':
                if (!inbound.settings) {
                    inbound.settings = {};
                }
                inbound.settings.clients ??= [];
                for (const user of users) {
                    inbound.settings.clients.push({
                        password: user.trojanPassword,
                        email: user.tId.toString(),
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
                        email: user.tId.toString(),
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
                        email: user.tId.toString(),
                    });
                }
                break;
            default:
                break;
        }
    }
}
exports.XRayConfigHarness = XRayConfigHarness;
