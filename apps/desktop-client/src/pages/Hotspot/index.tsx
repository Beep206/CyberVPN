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
import { desktopMotionEase, useDesktopMotionBudget } from "../../shared/lib/motion";
import { toast } from "sonner";
import { WifiHigh, Info, ShieldAlert, MonitorSmartphone, Power, ArrowRightLeft } from "lucide-react";
import { useTranslation } from "react-i18next";

export function HotspotPage() {
  const { t } = useTranslation();
  const { prefersReducedMotion, durations, offsets, scales } = useDesktopMotionBudget();
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
        toast.error(t('hotspot.readError'));
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
        toast.success(t('hotspot.started'));
      } else {
        await disableLanForwarding();
        await stopDeviceDiscovery();
        setIsActive(false);
        setDevices([]);
        toast.success(t('hotspot.stopped'));
      }
    } catch (err: any) {
      if (err.includes("ELEVATION_REQUIRED")) {
        toast.error(t('hotspot.adminRequired'), {
           description: t('hotspot.adminDesc'),
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
      initial={{ opacity: 0, y: offsets.page }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -4 }}
      transition={{ duration: durations.page, ease: desktopMotionEase }}
      className="max-w-4xl mx-auto space-y-8"
    >
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-[var(--color-neon-cyan)] to-[var(--color-matrix-green)] bg-clip-text text-transparent flex items-center gap-3">
          <WifiHigh size={32} className="text-[var(--color-neon-cyan)]" />
          {t('hotspot.title')}
        </h1>
        <p className="text-muted-foreground mt-2">
          {t('hotspot.description')}
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
                    initial={{ opacity: 0, scale: prefersReducedMotion ? 1 : 0.9 }}
                    animate={{ opacity: prefersReducedMotion ? 0.2 : 0.35, scale: prefersReducedMotion ? 1.04 : 1.35 }}
                    exit={{ opacity: 0, scale: prefersReducedMotion ? 1 : 0.9 }}
                    transition={{
                      duration: prefersReducedMotion ? durations.micro : 1.6,
                      repeat: prefersReducedMotion ? 0 : Infinity,
                      ease: desktopMotionEase,
                      repeatType: "reverse",
                    }}
                    className="absolute inset-0 m-auto w-48 h-48 rounded-full bg-[var(--color-neon-cyan)] blur-[80px] -z-10"
                  />
                )}
             </AnimatePresence>

             <motion.button
                whileHover={{ scale: scales.hover }}
                whileTap={{ scale: scales.tap }}
                onClick={handleToggle}
                disabled={isProcessing}
                className={`w-40 h-40 rounded-full flex flex-col items-center justify-center border-4 transition-all duration-500 ${
                  isActive 
                    ? "border-[var(--color-neon-cyan)] bg-[var(--color-neon-cyan)]/20 shadow-[0_0_40px_rgba(0,255,255,0.4)] text-[var(--color-neon-cyan)]"
                    : "border-muted-foreground/30 bg-card hover:border-muted-foreground/60 text-muted-foreground"
                }`}
             >
                <Power size={48} className={`mb-2 ${isProcessing ? "animate-pulse" : ""}`} />
                <span className="font-bold tracking-wider">{isActive ? t('hotspot.sharing') : t('hotspot.start')}</span>
             </motion.button>
           </div>

           <div className="p-6 rounded-xl border border-border/50 bg-card/30">
             <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
               <Info size={18} className="text-[var(--color-matrix-green)]" />
               {t('hotspot.proxyConfig')}
             </h3>
             {lanInfo ? (
               <div className="space-y-4">
                 <div className="bg-black/60 p-4 rounded-lg font-mono text-sm space-y-2 border border-border/30">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">{t('hotspot.gatewayIp')}</span>
                      <span className="text-[var(--color-neon-cyan)] font-bold">{lanInfo.ip}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">{t('hotspot.socksPort')}</span>
                      <span className="text-[var(--color-neon-pink)] font-bold">{lanInfo.port}</span>
                    </div>
                 </div>
                 <p className="text-xs text-muted-foreground">
                   {t('hotspot.proxyDesc')}
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
                    <div className="absolute inset-0 flex items-center justify-center bg-black/80 rounded-lg text-xs font-medium border border-border text-center px-2">
                       {t('hotspot.startHotspot')}
                    </div>
                 )}
              </div>
              <div>
                 <h4 className="font-medium text-lg mb-1">{t('hotspot.autoConfigure')}</h4>
                 <p className="text-sm text-muted-foreground">
                   {t('hotspot.autoConfigureDesc')}
                 </p>
              </div>
           </div>

           {/* Devices Section */}
           <div className="p-6 rounded-xl border border-border/50 bg-black/40 flex-1 flex flex-col">
              <h3 className="text-lg font-semibold mb-4 flex items-center justify-between">
                 <span className="flex items-center gap-2">
                   <MonitorSmartphone size={18} className="text-[var(--color-neon-pink)]" />
                   {t('hotspot.activeDiscovery')}
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
                  <p className="text-sm">{t('hotspot.offline')}</p>
                </div>
              ) : devices.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-[var(--color-neon-cyan)]/50 h-32">
                   <div className="animate-pulse flex flex-col items-center">
                      <MonitorSmartphone size={32} className="mb-2 opacity-50" />
                      <p className="text-sm tracking-widest uppercase">{t('hotspot.scanning')}</p>
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
                           {t('hotspot.connected')}
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
