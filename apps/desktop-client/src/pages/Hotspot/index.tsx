import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { listen, UnlistenFn } from "@tauri-apps/api/event";
import { QRCodeSVG } from "qrcode.react";
import {
  LanInfo,
  LanDevice,
  getLanConnectionInfo,
  enableLanForwarding,
  disableLanForwarding,
  startDeviceDiscovery,
  stopDeviceDiscovery
} from "../../shared/api/ipc";
import { toast } from "sonner";
import { WifiHigh, Info, ShieldAlert, MonitorSmartphone, Power, ArrowRightLeft } from "lucide-react";

export function HotspotPage() {
  const [isActive, setIsActive] = useState(false);
  const [lanInfo, setLanInfo] = useState<LanInfo | null>(null);
  const [devices, setDevices] = useState<LanDevice[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    let unlistenDevices: UnlistenFn;

    async function init() {
      try {
        const info = await getLanConnectionInfo();
        setLanInfo(info);
      } catch (err) {
        toast.error("Failed to read LAN info");
      }

      // Subscribe to real-time ARP discovery events pushed from Rust!
      unlistenDevices = await listen<LanDevice[]>("lan-devices-updated", (event) => {
        setDevices(event.payload);
      });
    }
    init();

    return () => {
      if (unlistenDevices) unlistenDevices();
      stopDeviceDiscovery().catch(console.error);
    };
  }, []);

  const handleToggle = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    
    try {
      if (!isActive) {
        await enableLanForwarding();
        await startDeviceDiscovery();
        setIsActive(true);
        toast.success("Hotspot Proxy Started");
      } else {
        await disableLanForwarding();
        await stopDeviceDiscovery();
        setIsActive(false);
        setDevices([]);
        toast.success("Hotspot Proxy Stopped");
      }
    } catch (err: any) {
      if (err.includes("ELEVATION_REQUIRED")) {
        toast.error("Administrator / Root rights required!", {
           description: "To enable IP Forwarding, please run CyberVPN as Administrator.",
           icon: <ShieldAlert className="text-red-500" />
        });
      } else {
        toast.error(`Hotspot error: ${err}`);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const proxyString = lanInfo ? `socks5://${lanInfo.ip}:${lanInfo.port}` : "";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="max-w-4xl mx-auto space-y-8"
    >
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-[var(--color-neon-cyan)] to-[var(--color-matrix-green)] bg-clip-text text-transparent flex items-center gap-3">
          <WifiHigh size={32} className="text-[var(--color-neon-cyan)]" />
          LAN Share Pro
        </h1>
        <p className="text-muted-foreground mt-2">
          Turn your PC into a secure VPN gateway for your Smart TVs, Consoles, and Mobile devices on the local network.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left Col: Master Switch & Guide */}
        <div className="space-y-6">
           <div className="flex flex-col items-center justify-center p-8 rounded-2xl border border-border/50 bg-black/40 min-h-[300px] relative overflow-hidden">
             
             {/* The Pulse Effect */}
             <AnimatePresence>
                {isActive && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 0.5, scale: 1.5 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut", repeatType: "reverse" }}
                    className="absolute inset-0 m-auto w-48 h-48 rounded-full bg-[var(--color-neon-cyan)] blur-[80px] -z-10"
                  />
                )}
             </AnimatePresence>

             <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleToggle}
                disabled={isProcessing}
                className={`w-40 h-40 rounded-full flex flex-col items-center justify-center border-4 transition-all duration-500 ${
                  isActive 
                    ? "border-[var(--color-neon-cyan)] bg-[var(--color-neon-cyan)]/20 shadow-[0_0_40px_rgba(0,255,255,0.4)] text-[var(--color-neon-cyan)]"
                    : "border-muted-foreground/30 bg-card hover:border-muted-foreground/60 text-muted-foreground"
                }`}
             >
                <Power size={48} className={`mb-2 ${isProcessing ? "animate-pulse" : ""}`} />
                <span className="font-bold tracking-wider">{isActive ? "SHARING" : "START"}</span>
             </motion.button>
           </div>

           <div className="p-6 rounded-xl border border-border/50 bg-card/30">
             <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
               <Info size={18} className="text-[var(--color-matrix-green)]" />
               Proxy Configuration
             </h3>
             {lanInfo ? (
               <div className="space-y-4">
                 <div className="bg-black/60 p-4 rounded-lg font-mono text-sm space-y-2 border border-border/30">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Gateway IP:</span>
                      <span className="text-[var(--color-neon-cyan)] font-bold">{lanInfo.ip}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">SOCKS5 Port:</span>
                      <span className="text-[var(--color-neon-pink)] font-bold">{lanInfo.port}</span>
                    </div>
                 </div>
                 <p className="text-xs text-muted-foreground">
                   Enter these identical Proxy settings into the Wi-Fi configuration of your other devices, or scan the QR code using a supported client.
                 </p>
               </div>
             ) : (
               <div className="animate-pulse h-16 bg-muted/20 rounded-lg" />
             )}
           </div>
        </div>

        {/* Right Col: QR Code & Active Devices */}
        <div className="space-y-6 flex flex-col h-full">
           
           {/* QR Section */}
           <div className="p-6 rounded-xl border border-border/50 bg-black/40 flex items-center gap-6">
              <div className="bg-white p-3 rounded-lg shrink-0 w-32 h-32 flex items-center justify-center blur-none relative">
                 {isActive ? (
                    <QRCodeSVG value={proxyString} size={104} />
                 ) : (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/80 rounded-lg text-xs font-medium border border-border">
                       Start Hotspot
                    </div>
                 )}
              </div>
              <div>
                 <h4 className="font-medium text-lg mb-1">Auto-Configure</h4>
                 <p className="text-sm text-muted-foreground">
                   Scan this code with CyberVPN mobile apps to automatically lock onto this Desktop node.
                 </p>
              </div>
           </div>

           {/* Devices Section */}
           <div className="p-6 rounded-xl border border-border/50 bg-black/40 flex-1 flex flex-col">
              <h3 className="text-lg font-semibold mb-4 flex items-center justify-between">
                 <span className="flex items-center gap-2">
                   <MonitorSmartphone size={18} className="text-[var(--color-neon-pink)]" />
                   Active Discovery
                 </span>
                 {isActive && (
                   <span className="flex h-3 w-3 relative">
                     <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-neon-pink)] opacity-75"></span>
                     <span className="relative inline-flex rounded-full h-3 w-3 bg-[var(--color-neon-pink)]"></span>
                   </span>
                 )}
              </h3>

              {!isActive ? (
                <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground/50 h-32">
                  <ArrowRightLeft size={32} className="mb-2 opacity-50" />
                  <p className="text-sm">Hotspot is Offline</p>
                </div>
              ) : devices.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-[var(--color-neon-cyan)]/50 h-32">
                   <div className="animate-pulse flex flex-col items-center">
                      <MonitorSmartphone size={32} className="mb-2 opacity-50" />
                      <p className="text-sm tracking-widest uppercase">Scanning LAN...</p>
                   </div>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar max-h-[250px]">
                  <AnimatePresence>
                    {devices.map((dev) => (
                      <motion.div
                        layout
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, height: 0 }}
                        key={dev.mac}
                        className="flex items-center justify-between p-3 rounded bg-card/30 border border-border/30"
                      >
                         <div className="flex items-center gap-3">
                           <div className="w-8 h-8 rounded-full bg-[var(--color-neon-cyan)]/10 flex items-center justify-center shrink-0">
                             <MonitorSmartphone size={16} className="text-[var(--color-neon-cyan)]" />
                           </div>
                           <div>
                             <p className="text-sm font-medium">{dev.ip}</p>
                             <p className="text-xs text-muted-foreground font-mono">{dev.mac}</p>
                           </div>
                         </div>
                         <div className="text-xs text-[var(--color-matrix-green)] bg-[var(--color-matrix-green)]/10 px-2 py-1 rounded">
                           Connected
                         </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              )}
           </div>
        </div>
      </div>
    </motion.div>
  );
}
