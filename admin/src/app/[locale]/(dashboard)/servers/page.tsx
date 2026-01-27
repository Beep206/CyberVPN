import { ServersDataGrid } from '@/widgets/servers-data-grid';

export default function ServersPage() {
    return (
        <div className="p-8 space-y-8">
            <div className="flex justify-between items-center mb-8 bg-terminal-surface/30 p-6 rounded-xl border border-grid-line/30 backdrop-blur">
                <div>
                    <h1 className="text-3xl font-display text-white tracking-widest">SERVER MANAGEMENT</h1>
                    <p className="text-muted-foreground font-mono mt-2">Manage VPN nodes, protocols, and deployment regions.</p>
                </div>
                <div className="text-right">
                    <div className="text-sm font-cyber text-neon-cyan">GLOBAL STATUS: PROVISIONED</div>
                    <div className="text-xs text-muted-foreground mt-1">LAST SYNC: 14s AGO</div>
                </div>
            </div>

            <ServersDataGrid />
        </div>
    );
}
