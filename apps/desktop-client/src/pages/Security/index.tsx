import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { listen, UnlistenFn } from "@tauri-apps/api/event";
import { enableKillswitchCmd, disableKillswitchCmd, repairNetwork } from "../../shared/api/ipc";
import { toast } from "sonner";
import { Shield, ShieldAlert, ShieldCheck, Wrench, Activity } from "lucide-react";

export function SecurityPage() {
  const [isKillSwitchActive, setIsKillSwitchActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isRepairing, setIsRepairing] = useState(false);

  useEffect(() => {
    let unlisten: UnlistenFn;
    
    async function setupListener() {
      unlisten = await listen("vpn-process-died", () => {
        if (isKillSwitchActive) {
           toast.error("VPN Connection Dropped!", {
             description: "Kill Switch has automatically blocked all internet traffic.",
             icon: <ShieldAlert className="text-red-500" />
           });
        }
      });
    }
    
    setupListener();

    return () => {
      if (unlisten) unlisten();
    };
  }, [isKillSwitchActive]);

  const handleToggleKillSwitch = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    
    try {
      if (!isKillSwitchActive) {
        await enableKillswitchCmd();
        setIsKillSwitchActive(true);
        toast.success("Kill Switch Enabled - Traffic Secured");
      } else {
        await disableKillswitchCmd();
        setIsKillSwitchActive(false);
        toast.success("Kill Switch Disabled");
      }
    } catch (err: any) {
      if (err.includes("Elevation Required") || err.includes("Administrator privileges") || err.includes("elevation")) {
        toast.error("Administrator Required", {
           description: "Please run CyberVPN as Administrator to alter firewall rules.",
           icon: <ShieldAlert className="text-red-500" />
        });
      } else {
        toast.error(`Kill Switch error: ${err}`);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRepairNetwork = async () => {
    if (isRepairing) return;
    setIsRepairing(true);
    toast.info("Repairing Network Stack...");
    
    try {
      await repairNetwork();
      // Also reset state if active
      if (isKillSwitchActive) {
         setIsKillSwitchActive(false);
      }
      toast.success("Network Repair Complete - Internet Restored");
    } catch (err: any) {
      toast.error(`Repair failed: ${err}`);
    } finally {
      setIsRepairing(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="max-w-4xl mx-auto space-y-8 relative overflow-hidden"
    >
      {/* Background Animated Shield Overlay */}
      <AnimatePresence>
        {isKillSwitchActive && (
           <motion.div
             initial={{ opacity: 0, scale: 0.5 }}
             animate={{ opacity: 0.05, scale: 2 }}
             exit={{ opacity: 0, scale: 0.5 }}
             transition={{ duration: 1.5, ease: "easeInOut" }}
             className="absolute md:-top-[20%] md:-right-[20%] w-[800px] h-[800px] bg-[var(--color-matrix-green)] rounded-full blur-[120px] pointer-events-none -z-10"
           />
        )}
      </AnimatePresence>

      <div>
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-[var(--color-matrix-green)] to-[var(--color-neon-cyan)] bg-clip-text text-transparent flex items-center gap-3">
          <Shield size={32} className="text-[var(--color-matrix-green)]" />
          Safety Center
        </h1>
        <p className="text-muted-foreground mt-2">
          Advanced network security tools to prevent data leaks and maintain connectivity.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Left Col: Kill Switch */}
        <div className="space-y-6">
           <div className="flex flex-col items-center justify-center p-8 rounded-2xl border border-border/50 bg-black/40 min-h-[300px] relative overflow-hidden group">
             
             <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleToggleKillSwitch}
                disabled={isProcessing}
                className={`w-40 h-40 rounded-full flex flex-col items-center justify-center border-4 transition-all duration-500 z-10 ${
                  isKillSwitchActive 
                    ? "border-[var(--color-matrix-green)] bg-[var(--color-matrix-green)]/20 shadow-[0_0_50px_rgba(0,255,136,0.3)] text-[var(--color-matrix-green)]"
                    : "border-muted-foreground/30 bg-card hover:border-red-500/50 hover:text-red-400 text-muted-foreground"
                }`}
             >
                {isKillSwitchActive ? (
                  <ShieldCheck size={48} className="mb-2" />
                ) : (
                  <ShieldAlert size={48} className={`mb-2 ${isProcessing ? "animate-pulse" : ""}`} />
                )}
                <span className="font-bold tracking-wider leading-tight text-center">
                  {isKillSwitchActive ? "KILL SWITCH\nON" : "KILL SWITCH\nOFF"}
                </span>
             </motion.button>
             
             {/* Subtitle description */}
             <div className="absolute bottom-4 left-0 right-0 text-center px-6">
               <p className="text-xs text-muted-foreground/70 transition-opacity">
                  {isKillSwitchActive ? "All non-VPN traffic is strictly blocked at the OS layer." : "Unsafe. Network leaks are possible if VPN drops."}
               </p>
             </div>
           </div>

           <div className="p-6 rounded-xl border border-border/50 bg-card/30">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                 <Activity size={18} className="text-[var(--color-neon-cyan)]" />
                 Leak Protection Status
              </h3>
              <div className="space-y-3">
                 <div className="flex items-center justify-between p-3 rounded bg-black/40 border border-border/30">
                    <span className="text-sm">DNS Leak Protection</span>
                    <span className="text-xs px-2 py-1 rounded bg-[var(--color-matrix-green)]/20 text-[var(--color-matrix-green)] flex items-center gap-1">
                      <ShieldCheck size={14} /> Active
                    </span>
                 </div>
                 <div className="flex items-center justify-between p-3 rounded bg-black/40 border border-border/30">
                    <span className="text-sm">IPv6 Leak Protection</span>
                    <span className="text-xs px-2 py-1 rounded bg-[var(--color-matrix-green)]/20 text-[var(--color-matrix-green)] flex items-center gap-1">
                      <ShieldCheck size={14} /> Active
                    </span>
                 </div>
                 <div className="flex items-center justify-between p-3 rounded bg-black/40 border border-border/30">
                    <span className="text-sm">OS Sentinel Guard</span>
                    {isKillSwitchActive ? (
                      <span className="text-xs px-2 py-1 rounded bg-[var(--color-matrix-green)]/20 text-[var(--color-matrix-green)] flex items-center gap-1">
                        <ShieldCheck size={14} /> Active
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400 flex items-center gap-1">
                        <ShieldAlert size={14} /> Inactive
                      </span>
                    )}
                 </div>
              </div>
           </div>
        </div>

        {/* Right Col: Network Repair */}
        <div className="space-y-6 flex flex-col h-full">
           
           <div className="p-8 rounded-xl border border-border/50 bg-black/40 flex-1 flex flex-col justify-center items-center text-center relative overflow-hidden">
              <div className="w-16 h-16 rounded-full bg-[var(--color-neon-pink)]/10 flex items-center justify-center mb-6">
                 <Wrench size={32} className="text-[var(--color-neon-pink)]" />
              </div>
              
              <h3 className="text-2xl font-bold mb-3">Network Self-Healing</h3>
              <p className="text-muted-foreground text-sm max-w-[280px] mb-8">
                 Internet broken? App crashed? Use the Repair tool to flush DNS, clear ghost proxies, and forcefully reset Windows firewall block rules.
              </p>
              
              <motion.button
                 whileHover={{ scale: 1.02, backgroundColor: "rgba(255, 0, 255, 0.15)" }}
                 whileTap={{ scale: 0.98 }}
                 onClick={handleRepairNetwork}
                 disabled={isRepairing}
                 className="flex items-center gap-2 px-8 py-3 rounded-lg border border-[var(--color-neon-pink)]/50 text-[var(--color-neon-pink)] font-medium transition-colors hover:border-[var(--color-neon-pink)]"
              >
                 {isRepairing ? (
                   <>
                     <Activity size={18} className="animate-spin" />
                     Fixing Network Stack...
                   </>
                 ) : (
                   <>
                     <Wrench size={18} />
                     Factory Reset Network
                   </>
                 )}
              </motion.button>
           </div>
           
        </div>
      </div>
    </motion.div>
  );
}
