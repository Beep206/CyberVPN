import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { listen, UnlistenFn } from "@tauri-apps/api/event";
import { enableKillswitchCmd, disableKillswitchCmd, repairNetwork, auditQuantumReadiness, AuditResult } from "../../shared/api/ipc";
import { toast } from "sonner";
import { Shield, ShieldAlert, ShieldCheck, Wrench, Activity, Fingerprint, Search, Server } from "lucide-react";
import { useTranslation } from "react-i18next";

export function SecurityPage() {
  const { t } = useTranslation();
  const [isKillSwitchActive, setIsKillSwitchActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isRepairing, setIsRepairing] = useState(false);

  // Quantum Forge State
  const [auditResults, setAuditResults] = useState<AuditResult[] | null>(null);
  const [isScanning, setIsScanning] = useState(false);

  useEffect(() => {
    let unlisten: UnlistenFn;
    
    async function setupListener() {
      unlisten = await listen("vpn-process-died", () => {
        if (isKillSwitchActive) {
           toast.error(t('security.vpnDropped'), {
             description: t('security.killSwitchBlocked'),
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
        toast.success(t('security.killSwitchEnabled'));
      } else {
        await disableKillswitchCmd();
        setIsKillSwitchActive(false);
        toast.success(t('security.killSwitchDisabled'));
      }
    } catch (err: any) {
      if (err.includes("Elevation Required") || err.includes("Administrator privileges") || err.includes("elevation")) {
        toast.error(t('security.adminRequired'), {
           description: t('security.runAsAdmin'),
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
    toast.info(t('security.repairing'));
    
    try {
      await repairNetwork();
      // Also reset state if active
      if (isKillSwitchActive) {
         setIsKillSwitchActive(false);
      }
      toast.success(t('security.repairComplete'));
    } catch (err: any) {
      toast.error(`Repair failed: ${err}`);
    } finally {
      setIsRepairing(false);
    }
  };

  const handleQuantumScan = async () => {
    setIsScanning(true);
    setAuditResults(null);
    try {
      // Simulate scan delay for visual effect
      await new Promise(r => setTimeout(r, 1500));
      const results = await auditQuantumReadiness();
      setAuditResults(results);
      toast.success(t('security.quantumComplete'));
    } catch (err: any) {
      toast.error(`Quantum Audit Failed: ${err}`);
    } finally {
      setIsScanning(false);
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
          {t('security.title')}
        </h1>
        <p className="text-muted-foreground mt-2">
          {t('security.description')}
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
                  {isKillSwitchActive ? t('security.killSwitchOn') : t('security.killSwitchOff')}
                </span>
             </motion.button>
             
             {/* Subtitle description */}
             <div className="absolute bottom-4 left-0 right-0 text-center px-6">
               <p className="text-xs text-muted-foreground/70 transition-opacity">
                  {isKillSwitchActive ? t('security.strictBlock') : t('security.unsafe')}
               </p>
             </div>
           </div>

           <div className="p-6 rounded-xl border border-border/50 bg-card/30">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                 <Activity size={18} className="text-[var(--color-neon-cyan)]" />
                 {t('security.leakProtection')}
              </h3>
              <div className="space-y-3">
                 <div className="flex items-center justify-between p-3 rounded bg-black/40 border border-border/30">
                    <span className="text-sm">{t('security.dnsLeak')}</span>
                    <span className="text-xs px-2 py-1 rounded bg-[var(--color-matrix-green)]/20 text-[var(--color-matrix-green)] flex items-center gap-1">
                      <ShieldCheck size={14} /> {t('security.active')}
                    </span>
                 </div>
                 <div className="flex items-center justify-between p-3 rounded bg-black/40 border border-border/30">
                    <span className="text-sm">{t('security.ipv6Leak')}</span>
                    <span className="text-xs px-2 py-1 rounded bg-[var(--color-matrix-green)]/20 text-[var(--color-matrix-green)] flex items-center gap-1">
                      <ShieldCheck size={14} /> {t('security.active')}
                    </span>
                 </div>
                 <div className="flex items-center justify-between p-3 rounded bg-black/40 border border-border/30">
                    <span className="text-sm">{t('security.osGuard')}</span>
                    {isKillSwitchActive ? (
                      <span className="text-xs px-2 py-1 rounded bg-[var(--color-matrix-green)]/20 text-[var(--color-matrix-green)] flex items-center gap-1">
                        <ShieldCheck size={14} /> {t('security.active')}
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400 flex items-center gap-1">
                        <ShieldAlert size={14} /> {t('security.inactive')}
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
              
              <h3 className="text-2xl font-bold mb-3">{t('security.selfHealing')}</h3>
              <p className="text-muted-foreground text-sm max-w-[280px] mb-8">
                 {t('security.repairDesc')}
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
                     {t('security.fixing')}
                   </>
                 ) : (
                   <>
                     <Wrench size={18} />
                     {t('security.factoryReset')}
                   </>
                 )}
              </motion.button>
           </div>
           
        </div>
      </div>

      {/* Quantum Forge Section */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mt-8 p-8 rounded-2xl border border-[var(--color-neon-cyan)]/30 bg-black/60 relative overflow-hidden"
      >
        {/* Particles during scanning */}
        <AnimatePresence>
          {isScanning && (
             <motion.div
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               exit={{ opacity: 0 }}
               className="absolute inset-0 pointer-events-none overflow-hidden"
             >
               {[...Array(20)].map((_, i) => (
                 <motion.div
                   key={i}
                   className="absolute w-1 h-12 bg-gradient-to-b from-transparent to-[var(--color-neon-cyan)] opacity-50"
                   initial={{ top: "-10%", left: `${Math.random() * 100}%` }}
                   animate={{ top: "110%" }}
                   transition={{ duration: 1 + Math.random(), repeat: Infinity, ease: "linear", delay: Math.random() }}
                 />
               ))}
             </motion.div>
          )}
        </AnimatePresence>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 relative z-10">
          <div>
            <h3 className="text-2xl font-bold flex items-center gap-3 text-[var(--color-neon-cyan)]">
              <Fingerprint size={28} />
              {t('security.quantumForge')}
            </h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-lg">
              {t('security.quantumDesc')}
            </p>
          </div>
          <motion.button
             onClick={handleQuantumScan}
             disabled={isScanning}
             whileHover={{ scale: 1.05 }}
             whileTap={{ scale: 0.95 }}
             className={`px-6 py-3 rounded-lg border transition-all flex items-center justify-center gap-2 font-medium min-w-[180px] ${
               isScanning 
                 ? 'border-transparent bg-[var(--color-neon-cyan)]/20 text-[var(--color-neon-cyan)]/50' 
                 : 'border-[var(--color-neon-cyan)]/50 text-[var(--color-neon-cyan)] hover:bg-[var(--color-neon-cyan)]/10 hover:shadow-[0_0_20px_rgba(0,255,255,0.2)]'
             }`}
          >
            {isScanning ? <Activity className="animate-spin" size={18} /> : <Search size={18} />}
            {isScanning ? t('security.scanning') : t('security.quantumScan')}
          </motion.button>
        </div>

        {/* Results Container */}
        <div className="space-y-3 relative z-10 mt-6 min-h-[100px]">
          {!auditResults && !isScanning && (
            <div className="flex flex-col items-center justify-center py-10 text-muted-foreground/50">
              <Shield size={48} className="mb-4 opacity-20" />
              <p>{t('security.initScan')}</p>
            </div>
          )}
          {auditResults && auditResults.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-10">{t('security.noProfiles')}</p>
          )}
          
          <AnimatePresence>
            {auditResults?.map((res, idx) => (
              <motion.div 
                key={res.id} 
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl bg-black/40 border border-border/30 hover:bg-black/60 hover:border-border/60 transition-colors gap-4"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-card border border-border/50 flex items-center justify-center">
                    <Server size={20} className="text-muted-foreground" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground tracking-wide">{res.name}</h4>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground uppercase font-mono tracking-wider">{res.protocol}</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-end">
                  {res.status === "Ready" && (
                    <div className="relative group cursor-help">
                       <span className="text-xs px-3 py-1.5 rounded-md bg-[var(--color-matrix-green)]/10 text-[var(--color-matrix-green)] flex items-center gap-1.5 border border-[#8a2be2]/50 shadow-[0_0_15px_rgba(138,43,226,0.3)] font-medium tracking-wide">
                         <ShieldCheck size={16} className="text-[#8a2be2] drop-shadow-[0_0_8px_rgba(138,43,226,0.8)]" /> 
                         {t('security.quantumShieldActive')}
                       </span>
                       <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity bottom-full right-0 mb-2 w-64 p-3 bg-black border border-border/50 rounded-lg text-xs text-muted-foreground z-50 pointer-events-none">
                          {t('security.quantumShieldDesc')}
                       </div>
                    </div>
                  )}
                  {res.status === "Partially Ready" && (
                    <div className="relative group cursor-help">
                       <span className="text-xs px-3 py-1.5 rounded-md bg-yellow-500/10 text-yellow-500 flex items-center gap-1.5 border border-yellow-500/20 font-medium tracking-wide">
                         <ShieldAlert size={16} /> 
                         {t('security.partiallyReady')}
                       </span>
                       <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity bottom-full right-0 mb-2 w-64 p-3 bg-black border border-border/50 rounded-lg text-xs text-muted-foreground z-50 pointer-events-none">
                          {t('security.partiallyReadyDesc')}
                       </div>
                    </div>
                  )}
                  {res.status === "Not Ready" && (
                    <div className="relative group cursor-help">
                       <span className="text-xs px-3 py-1.5 rounded-md bg-red-500/10 text-red-500 flex items-center gap-1.5 border border-red-500/20 font-medium tracking-wide">
                         <ShieldAlert size={16} /> 
                         {t('security.vulnerable')}
                       </span>
                       <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity bottom-full right-0 mb-2 w-64 p-3 bg-black border border-border/50 rounded-lg text-xs text-muted-foreground z-50 pointer-events-none">
                          {t('security.vulnerableDesc')}
                       </div>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </motion.div>
    </motion.div>
  );
}
