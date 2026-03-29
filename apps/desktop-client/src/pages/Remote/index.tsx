import { useState } from "react";
import { motion } from "framer-motion";
import { invoke } from "@tauri-apps/api/core";
import { Smartphone, QrCode, Server, WifiOff, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { QRCodeSVG } from "qrcode.react";

export function RemotePage() {
    const [remoteUrl, setRemoteUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    // Initial load check if it's already running somewhere or could auto-start based on a setting
    // But for Phase 31 manual toggle is preferred
    
    const toggleRemote = async () => {
        setLoading(true);
        try {
            if (remoteUrl) {
                await invoke("stop_remote_server");
                setRemoteUrl(null);
                toast.success("Remote Controller Offline");
            } else {
                const url = await invoke<string>("start_remote_server");
                setRemoteUrl(url);
                toast.success("Remote Controller Online");
            }
        } catch (err: any) {
            toast.error(`Remote Server Error: ${err}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto space-y-8"
        >
            <header className="border-b border-white/5 pb-4">
                <h1 className="text-4xl font-extrabold tracking-tighter text-[#00ff88] uppercase" style={{ textShadow: "0 0 15px rgba(0,255,136,0.4)" }}>
                    Remote Controller
                </h1>
                <p className="text-muted-foreground font-mono text-sm mt-2 flex items-center gap-2">
                    <Smartphone className="text-[#00ff88]" size={16} /> Manage the VPN connection via Mobile Dashboard
                </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Pairing UI */}
                <div className="bg-black/40 border border-[#00ff88]/20 rounded-xl p-8 backdrop-blur relative overflow-hidden flex flex-col items-center justify-center text-center">
                    <div className="absolute inset-0 bg-[#00ff88]/5 pointer-events-none" />
                    
                    <h3 className="text-xl font-bold font-mono tracking-widest text-[#00ff88] mb-6 flex items-center gap-2 relative z-10">
                        <QrCode size={24} /> DEVICE PAIRING
                    </h3>

                    {remoteUrl ? (
                        <div className="bg-white p-4 rounded-xl shadow-[0_0_30px_rgba(0,255,136,0.3)] mb-6 transition-all">
                            <QRCodeSVG value={remoteUrl} size={200} bgColor={"#ffffff"} fgColor={"#000000"} level={"Q"} />
                        </div>
                    ) : (
                        <div className="w-[200px] h-[200px] border-2 border-dashed border-[#00ff88]/20 rounded-xl mb-6 flex flex-col items-center justify-center text-[#00ff88]/40">
                            <WifiOff size={48} className="mb-2" />
                            <span className="font-mono text-xs">OFFLINE</span>
                        </div>
                    )}

                    <button 
                        onClick={toggleRemote}
                        disabled={loading}
                        className={`relative z-10 px-8 py-3 rounded-lg font-bold tracking-widest transition-all ${
                            remoteUrl 
                                ? "bg-red-500/20 text-red-500 border border-red-500/50 hover:bg-red-500/30" 
                                : "bg-[#00ff88]/20 text-[#00ff88] border border-[#00ff88]/50 hover:bg-[#00ff88]/30 hover:shadow-[0_0_20px_rgba(0,255,136,0.4)]"
                        }`}
                    >
                        {loading ? "INITIALIZING..." : remoteUrl ? "DISABLE REMOTE" : "ENABLE REMOTE"}
                    </button>

                    {remoteUrl && (
                        <div className="mt-6 text-xs font-mono text-white/50 break-all w-full max-w-[250px] relative z-10">
                            Or browse to:<br/>
                            <a href={remoteUrl} target="_blank" className="text-[#00ffff] hover:underline selection:bg-[#ff00ff]/30">{remoteUrl}</a>
                        </div>
                    )}
                </div>

                {/* Instructions & Sessions */}
                <div className="flex flex-col gap-6">
                    <div className="bg-black/40 border border-white/10 rounded-xl p-6 backdrop-blur">
                        <h3 className="text-lg font-bold font-mono tracking-wider mb-4 text-white/80">INSTRUCTIONS</h3>
                        <ul className="space-y-4 text-sm text-muted-foreground font-mono">
                            <li className="flex gap-3 items-start">
                                <span className="bg-[#00ff88]/20 text-[#00ff88] px-2 py-0.5 rounded text-xs font-bold shrink-0">1</span>
                                <div>Click <strong>ENABLE REMOTE</strong> to deploy the hardened Axum HTTP server on your local network zero-trust boundary.</div>
                            </li>
                            <li className="flex gap-3 items-start">
                                <span className="bg-[#00ff88]/20 text-[#00ff88] px-2 py-0.5 rounded text-xs font-bold shrink-0">2</span>
                                <div>Take your primary smart device (Mobile/Tablet) ensuring it is connected to the same Local Area Network (WiFi).</div>
                            </li>
                            <li className="flex gap-3 items-start">
                                <span className="bg-[#00ff88]/20 text-[#00ff88] px-2 py-0.5 rounded text-xs font-bold shrink-0">3</span>
                                <div>Scan the <strong>QR Code</strong> with the device camera to instantly authenticate a bearer token mapped natively without cloud brokering.</div>
                            </li>
                        </ul>
                    </div>

                    <div className="bg-black/40 border border-white/10 rounded-xl p-6 backdrop-blur flex-1">
                        <h3 className="text-lg font-bold font-mono tracking-wider mb-4 text-white/80 flex items-center gap-2">
                            <Server size={18} /> ACTIVE SESSIONS
                        </h3>
                        {remoteUrl ? (
                            <div className="flex items-center justify-between p-3 border border-[#00ff88]/30 bg-[#00ff88]/10 rounded-lg font-mono">
                                <div className="flex items-center gap-3">
                                    <CheckCircle className="text-[#00ff88]" size={16} />
                                    <div>
                                        <div className="text-sm font-bold text-white">LAN Server Online</div>
                                        <div className="text-xs text-[#00ff88]">Awaiting Bearer Handshake...</div>
                                    </div>
                                </div>
                                <span className="text-[10px] text-white/40">PORT: 8080</span>
                            </div>
                        ) : (
                            <div className="text-center text-sm font-mono text-white/30 mt-6">
                                Server is offline.
                            </div>
                        )}
                    </div>
                </div>
            </div>
            
            {/* Aesthetic Scanline overlay */}
            <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(0,0,0,0)_50%,rgba(0,0,0,0.1)_50%)] bg-[length:100%_4px] mix-blend-overlay z-50 opacity-10" />
        </motion.div>
    );
}
