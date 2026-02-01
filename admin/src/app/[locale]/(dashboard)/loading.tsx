export default function DashboardLoading() {
    return (
        <div className="p-8 space-y-8 animate-pulse">
            {/* Header skeleton */}
            <div className="bg-terminal-surface/30 p-6 rounded-xl border border-grid-line/30">
                <div className="h-8 w-64 bg-neon-cyan/10 rounded mb-3" />
                <div className="h-4 w-48 bg-muted/20 rounded" />
            </div>

            {/* Stats grid skeleton */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {Array.from({ length: 3 }).map((_, i) => (
                    <div
                        key={i}
                        className="bg-terminal-surface/30 p-6 rounded-xl border border-grid-line/30"
                    >
                        <div className="h-5 w-32 bg-neon-pink/10 rounded mb-4" />
                        <div className="h-10 w-24 bg-neon-cyan/10 rounded mb-2" />
                        <div className="h-3 w-40 bg-muted/20 rounded" />
                    </div>
                ))}
            </div>

            {/* Content skeleton */}
            <div className="space-y-4">
                <div className="h-6 w-48 bg-neon-purple/10 rounded" />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div
                            key={i}
                            className="bg-terminal-surface/30 h-48 rounded-xl border border-grid-line/30"
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
