import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

export function NavigationTab({ onClose, isDark }: { onClose: () => void, isDark: boolean }) {
    const router = useRouter();
    const links = [
        { label: "Dashboard (User)", path: "/dashboard" },
        { label: "Login Page", path: "/login" },
        { label: "Landing Page", path: "/" },
        { label: "Registration Page", path: "/register" },
        { label: "OTP Verification", path: "/verify" },
        { label: "Inception Test", path: "/test-animation" },
        { label: "Error Test", path: "/test-error" },
    ];

    return (
        <div className="space-y-4 relative z-20">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-4 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>Quick Jump</h3>
            <div className="grid gap-2">
                {links.map((link) => (
                    <button
                        key={link.path}
                        onClick={() => {
                            router.push(link.path);
                            onClose();
                        }}
                        className={cn(
                            "group flex items-center justify-between p-3 border transition-all rounded text-left",
                            isDark
                                ? "border-gray-700 bg-black hover:border-neon-cyan hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,255,255,0.4)]"
                                : "border-slate-200 bg-white hover:border-blue-400 hover:bg-blue-50 shadow-sm"
                        )}
                    >
                        <span className={cn("text-base font-bold transition-colors", isDark ? "text-white group-hover:text-neon-cyan group-hover:drop-shadow-[0_0_8px_rgba(0,255,255,1)]" : "text-slate-700 group-hover:text-blue-600")}>{link.label}</span>
                        <span className={cn("text-xs font-mono transition-colors font-medium", isDark ? "text-gray-400 group-hover:text-neon-pink" : "text-slate-400 group-hover:text-blue-400")}>{link.path}</span>
                    </button>
                ))}
            </div>
        </div>
    );
}
