export default function RootLoading() {
    return (
        <div className="flex items-center justify-center min-h-screen bg-terminal-bg">
            <div className="relative">
                <div className="h-12 w-12 rounded-full border-2 border-neon-cyan/30 border-t-neon-cyan animate-spin" />
                <div className="absolute inset-0 blur-lg bg-neon-cyan/20 rounded-full animate-pulse" />
            </div>
        </div>
    );
}
