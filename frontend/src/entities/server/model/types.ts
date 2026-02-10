import type { components } from '@/lib/api/generated/types';

/** Re-exported from OpenAPI generated types — matches backend ServerStatus enum exactly */
export type ServerStatus = components['schemas']['ServerStatus'];

/** Frontend-only — backend does not expose a VpnProtocol enum */
export type VpnProtocol = 'wireguard' | 'vless' | 'xhttp';

/**
 * Frontend-only display model for the servers data grid / cards.
 * The backend ServerResponse uses a different shape (uuid, address, port,
 * is_connected, traffic_used_bytes, etc.), so this type is intentionally
 * kept hand-written as a presentation-layer model.
 */
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
