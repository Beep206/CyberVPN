import { cn } from "@/lib/utils";

export function SystemTab({ isDark }: { isDark: boolean }) {
    return (
        <div className="space-y-4 relative z-20">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-4 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>System Diagnostics</h3>

            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className={cn("p-3 border rounded transition-colors group", isDark ? "bg-black border-gray-700 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>NODE_ENV</span>
                    <span className={cn("font-black text-sm tracking-wide", isDark ? "text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.7)]" : "text-slate-800")}>{process.env.NODE_ENV}</span>
                </div>
                <div className={cn("p-3 border rounded transition-colors group", isDark ? "bg-black border-gray-700 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>Platform</span>
                    <span className={cn("font-black text-sm tracking-wide", isDark ? "text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.7)]" : "text-slate-800")}>{typeof window !== 'undefined' ? window.navigator.platform : 'Server'}</span>
                </div>
                <div className={cn("p-3 border rounded col-span-2 transition-colors group", isDark ? "bg-black border-gray-700 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>User Agent</span>
                    <span className={cn("break-all font-semibold transition-colors", isDark ? "text-gray-100 group-hover:text-neon-cyan" : "text-slate-700")}>{typeof window !== 'undefined' ? window.navigator.userAgent : 'Server'}</span>
                </div>
            </div>
        </div>
    );
}
