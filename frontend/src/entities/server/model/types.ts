export type ServerStatus = 'online' | 'offline' | 'warning' | 'maintenance';
export type VpnProtocol = 'wireguard' | 'vless' | 'xhttp';

export interface Server {
    id: string;
    name: string;
    location: string;
    ip: string;
    protocol: VpnProtocol;
    status: ServerStatus;
    load: number; // 0-100
    uptime: string;
    clients: number;
}
