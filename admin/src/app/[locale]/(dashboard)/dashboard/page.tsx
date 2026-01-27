import { ServerCard } from "@/shared/ui/molecules/server-card";

const servers = [
    { id: '1', name: 'Tokyo Node 01', location: 'Japan, Tokyo', status: 'online' as const, ip: '45.32.12.90', load: 45, protocol: 'vless' as const },
    { id: '2', name: 'NYC Core', location: 'USA, New York', status: 'warning' as const, ip: '192.168.1.1', load: 82, protocol: 'wireguard' as const },
    { id: '3', name: 'London Edge', location: 'UK, London', status: 'online' as const, ip: '178.2.4.11', load: 23, protocol: 'xhttp' as const },
    { id: '4', name: 'Singapore Stealth', location: 'Singapore', status: 'maintenance' as const, ip: '201.10.3.55', load: 0, protocol: 'vless' as const },
];

export default function Dashboard() {
    return (
        <div className="p-8 space-y-8">
            <header className="flex justify-between items-center mb-8 bg-terminal-surface/30 p-4 rounded-xl border border-grid-line/30 backdrop-blur">
                <div>
                    <h1 className="text-4xl font-display text-neon-cyan drop-shadow-glow">VPN COMMAND CENTER</h1>
                    <p className="text-muted-foreground font-mono mt-1">SYSTEM STATUS: <span className="text-matrix-green">OPTIMAL</span></p>
                </div>
                <div className="text-right font-cyber text-sm text-neon-pink">
                    SECURE CONNECTION ESTABLISHED<br />
                    ENCRYPTION: QUANTUM-SAFE
                </div>
            </header>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="cyber-card p-6 rounded-xl">
                    <h2 className="text-xl font-mono text-neon-pink mb-2">SERVER STATUS</h2>
                    <div className="text-4xl font-display text-server-online drop-shadow-glow">
                        {servers.filter(s => s.status === 'online').length} / {servers.length}
                    </div>
                    <p className="text-sm text-muted-foreground mt-2">NODES ONLINE</p>
                </div>
                <div className="cyber-card p-6 rounded-xl">
                    <h2 className="text-xl font-mono text-neon-pink mb-2">ACTIVE SESSIONS</h2>
                    <div className="text-4xl font-display text-neon-cyan drop-shadow-glow">1,337</div>
                    <p className="text-sm text-muted-foreground mt-2">Current connections</p>
                </div>
                <div className="cyber-card p-6 rounded-xl">
                    <h2 className="text-xl font-mono text-neon-pink mb-2">NETWORK LOAD</h2>
                    <div className="text-4xl font-display text-matrix-green drop-shadow-glow">42 Pb/s</div>
                    <p className="text-sm text-muted-foreground mt-2">Aggregate throughput</p>
                </div>
            </div>

            <h2 className="text-2xl font-display text-neon-purple mt-12 mb-6 pl-2 border-l-4 border-neon-purple">SERVER MATRIX</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {servers.map((server, index) => (
                    <ServerCard key={server.id} server={server} index={index} />
                ))}
            </div>
        </div>
    );
}
