import { Construction } from 'lucide-react';

export default function PlaceholderPage() {
    return (
        <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-4">
            <div className="relative">
                <Construction className="h-24 w-24 text-neon-cyan opacity-80 animate-pulse" />
                <div className="absolute inset-0 blur-xl bg-neon-cyan/20 rounded-full" />
            </div>
            <h1 className="text-3xl font-display text-white tracking-widest">SYSTEM MODULE OFFLINE</h1>
            <p className="text-muted-foreground font-mono max-w-md">
                This cyber-deck module is currently under development.
                Check back later for firmware updates.
            </p>
            <div className="text-xs font-cyber text-neon-pink mt-8">ERROR_CODE: FEATURE_NOT_READY</div>
        </div>
    );
}
