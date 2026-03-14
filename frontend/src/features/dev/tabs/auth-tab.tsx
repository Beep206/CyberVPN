import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";
import { Copy, Key, UserCog, Clock, AlertCircle, CheckCircle2, ShieldAlert } from "lucide-react";

export function AuthTab({ enabled, onToggle, isDark }: { enabled: boolean; onToggle: () => void, isDark: boolean }) {
    const [jwtInput, setJwtInput] = useState("");
    const [decodedJwt, setDecodedJwt] = useState<{ header: any; payload: any } | null>(null);
    const [jwtError, setJwtError] = useState("");
    
    const [activeRole, setActiveRole] = useState<string>("");

    useEffect(() => {
        if (typeof window !== 'undefined') {
            const currentRole = localStorage.getItem('USER_ROLE') || "guest";
            setActiveRole(currentRole);
        }
    }, []);

    // JWT Decoder Logic
    useEffect(() => {
        if (!jwtInput.trim()) {
            setDecodedJwt(null);
            setJwtError("");
            return;
        }

        try {
            const parts = jwtInput.split('.');
            if (parts.length !== 3) throw new Error("Invalid JWT format (requires 3 parts)");
            
            const decodeBase64Url = (str: string) => {
                const base64 = str.replace(/-/g, '+').replace(/_/g, '/');
                const pad = base64.length % 4;
                const paddedStr = pad ? base64 + new Array(5 - pad).join('=') : base64;
                return JSON.parse(atob(paddedStr));
            };

            const header = decodeBase64Url(parts[0]);
            const payload = decodeBase64Url(parts[1]);
            
            setDecodedJwt({ header, payload });
            setJwtError("");
        } catch (err: any) {
            setDecodedJwt(null);
            setJwtError(err.message || "Failed to decode JWT");
        }
    }, [jwtInput]);

    const setRole = (role: string) => {
        if (typeof window !== 'undefined') {
            localStorage.setItem('USER_ROLE', role);
            // Optional: also set a generic cookie just in case
            document.cookie = `USER_ROLE=${role}; path=/; max-age=31536000`;
            setActiveRole(role);
        }
    };

    const isTokenExpired = decodedJwt?.payload?.exp ? (decodedJwt.payload.exp * 1000) < Date.now() : false;

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-2 border-b pb-2 shrink-0", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>Security Protocols</h3>

            {/* Auth Bypass */}
            <div className={cn(
                "flex items-center justify-between p-4 border rounded backdrop-blur-md transition-colors shrink-0",
                isDark
                    ? "border-neon-cyan/40 bg-black hover:border-neon-cyan/60"
                    : "border-slate-200 bg-white hover:border-blue-300"
            )}>
                <div>
                    <h4 className={cn("text-base font-extrabold flex items-center gap-2", isDark ? "text-neon-cyan drop-shadow-[0_0_10px_rgba(0,255,255,0.9)]" : "text-slate-800")}>
                        <ShieldAlert className="w-4 h-4" /> Auth Bypass Mode
                    </h4>
                    <p className={cn("text-[10px] mt-1 font-semibold transition-colors", isDark ? "text-gray-400 group-hover:text-white" : "text-slate-500")}>Simulate authenticated session via DEV_BYPASS_AUTH cookie.</p>
                </div>
                <button
                    onClick={onToggle}
                    className={cn(
                        "relative w-14 h-7 rounded-full transition-colors duration-300 focus:outline-none border-2 shrink-0",
                        enabled
                            ? (isDark ? "bg-neon-cyan/30 border-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.5)]" : "bg-blue-100 border-blue-500")
                            : (isDark ? "bg-gray-800 border-gray-500 hover:border-neon-pink/50 shadow-[0_0_15px_rgba(0,0,0,0.5)]" : "bg-slate-200 border-slate-300")
                    )}
                >
                    <motion.div
                        className={cn(
                            "absolute top-0.5 left-0.5 w-5 h-5 rounded-full shadow-md transition-transform duration-300",
                            enabled
                                ? (isDark ? "translate-x-7 bg-neon-cyan shadow-[0_0_15px_#00ffff]" : "translate-x-7 bg-blue-500")
                                : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                        )}
                        layout
                    />
                </button>
            </div>

            {/* Role Spoofer */}
            <div className={cn("p-4 border rounded flex flex-col gap-3 shrink-0", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-purple-400" : "text-purple-600")}>
                        <UserCog className="w-4 h-4" /> Client Role Spoofer
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>
                        Instantly override the <code className="px-1 bg-black/20 rounded">USER_ROLE</code> flag in localStorage/cookies.
                    </p>
                </div>
                
                <div className="flex gap-2 flex-wrap">
                    {["admin", "user", "moderator", "banned", "guest"].map(role => (
                        <button
                            key={role}
                            onClick={() => setRole(role)}
                            className={cn(
                                "px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider border transition-all",
                                activeRole === role
                                    ? (isDark ? "bg-purple-500/20 text-purple-300 border-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.4)]" : "bg-purple-100 text-purple-700 border-purple-500")
                                    : (isDark ? "bg-gray-900 border-gray-700 text-gray-400 hover:border-purple-500/50 hover:text-purple-400" : "bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100")
                            )}
                        >
                            {role}
                        </button>
                    ))}
                </div>
            </div>

            {/* JWT Decoder */}
            <div className={cn("p-4 border rounded flex flex-col gap-3 flex-1 min-h-0", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="shrink-0">
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-green-400" : "text-green-600")}>
                        <Key className="w-4 h-4" /> Local JWT Decoder
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>
                        Paste a JSON Web Token to inspect its payload locally. (Tokens are NOT sent over the network).
                    </p>
                </div>
                
                <textarea
                    value={jwtInput}
                    onChange={(e) => setJwtInput(e.target.value)}
                    placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                    className={cn(
                        "w-full h-20 p-2 text-xs font-mono rounded border outline-none resize-none shrink-0 transition-colors",
                        isDark ? "bg-gray-900 border-gray-700 text-green-300 focus:border-green-500" : "bg-slate-50 border-slate-200 focus:border-green-400",
                        jwtError && (isDark ? "border-red-500/50 text-red-300" : "border-red-400 text-red-600")
                    )}
                />

                {jwtError && jwtInput.length > 0 && (
                    <div className="text-xs text-red-500 flex items-center gap-1 font-bold shrink-0">
                        <AlertCircle className="w-3 h-3" /> {jwtError}
                    </div>
                )}

                {decodedJwt && (
                    <div className="flex-1 min-h-0 overflow-y-auto space-y-3 font-mono text-[10px]">
                        {/* Status Bar */}
                        <div className={cn("p-2 rounded flex items-center justify-between border", 
                            isTokenExpired 
                                ? (isDark ? "bg-red-900/30 border-red-500/50 text-red-400" : "bg-red-50 border-red-200 text-red-700") 
                                : (isDark ? "bg-green-900/30 border-green-500/50 text-green-400" : "bg-green-50 border-green-200 text-green-700")
                        )}>
                            <div className="flex items-center gap-2 font-bold">
                                {isTokenExpired ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                                {isTokenExpired ? "TOKEN EXPIRED" : "TOKEN VALID (Signature not verifiable locally)"}
                            </div>
                            {decodedJwt.payload.exp && (
                                <div className="flex items-center gap-1 opacity-80">
                                    <Clock className="w-3 h-3" />
                                    Exp: {new Date(decodedJwt.payload.exp * 1000).toLocaleString()}
                                </div>
                            )}
                        </div>

                        <div className="grid grid-cols-1 gap-3">
                            <div className={cn("p-2 rounded border", isDark ? "bg-gray-900/50 border-gray-800" : "bg-slate-50 border-slate-200")}>
                                <div className="font-bold opacity-50 mb-1 border-b pb-1 border-dashed border-gray-700 text-[9px] uppercase">Header / Algorithm</div>
                                <pre className={cn("whitespace-pre-wrap break-all", isDark ? "text-pink-300" : "text-pink-600")}>
                                    {JSON.stringify(decodedJwt.header, null, 2)}
                                </pre>
                            </div>
                            <div className={cn("p-2 rounded border", isDark ? "bg-gray-900/50 border-gray-800" : "bg-slate-50 border-slate-200")}>
                                <div className="font-bold opacity-50 mb-1 border-b pb-1 border-dashed border-gray-700 text-[9px] uppercase">Data / Payload</div>
                                <pre className={cn("whitespace-pre-wrap break-all", isDark ? "text-cyan-300" : "text-cyan-600")}>
                                    {JSON.stringify(decodedJwt.payload, null, 2)}
                                </pre>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
