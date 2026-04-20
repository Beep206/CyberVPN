import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { Shield, ShieldAlert, ShieldCheck, Activity, AlertTriangle, EyeOff, RadioTower, RotateCw } from "lucide-react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import {
  getPrivacyShieldLevel,
  setPrivacyShieldLevel,
  forceUpdateBlocklists,
  getThreatCount,
  listenTrackerBlocked
} from "../../shared/api/ipc";
import { desktopMotionEase, useDesktopMotionBudget } from "../../shared/lib/motion";

export function PrivacyShieldPage() {
  const { t } = useTranslation();
  const { prefersReducedMotion, durations, offsets } = useDesktopMotionBudget();
  const [level, setLevel] = useState("disabled");
  const [threatCount, setThreatCount] = useState<number>(0);
  const [isUpdating, setIsUpdating] = useState(false);
  const [recentBlocks, setRecentBlocks] = useState<{ id: number; domain: string; time: Date }[]>([]);

  useEffect(() => {
    getPrivacyShieldLevel().then(setLevel).catch(console.error);
    getThreatCount().then(setThreatCount).catch(console.error);

    const unlisten = listenTrackerBlocked((domain) => {
      setThreatCount((prev) => prev + 1);
      setRecentBlocks((prev) => {
        const newBlocks = [{ id: Date.now(), domain, time: new Date() }, ...prev];
        return newBlocks.slice(0, 50); // keep last 50
      });
    });

    return () => {
      unlisten();
    };
  }, []);

  const handleLevelChange = async (newLevel: string) => {
    try {
      await setPrivacyShieldLevel(newLevel);
      setLevel(newLevel);
      toast.success(t('privacyShield.setSuccess', { level: newLevel }));
    } catch (e: any) {
      toast.error(t('privacyShield.setError', { error: e }));
    }
  };

  const handleForceUpdate = async () => {
    if (isUpdating) return;
    setIsUpdating(true);
    toast.info(t('privacyShield.updating'));
    try {
      await forceUpdateBlocklists();
      toast.success(t('privacyShield.updateSuccess'));
    } catch (e: any) {
      toast.error(e.toString());
    } finally {
      setIsUpdating(false);
    }
  };

  const isActive = level !== "disabled";

  return (
    <motion.div
      initial={{ opacity: 0, y: offsets.page }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -4 }}
      transition={{ duration: durations.page, ease: desktopMotionEase }}
      className="p-8 max-w-5xl mx-auto space-y-8 min-h-full"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative">
        <div className="z-10 relative">
          <h1 className="text-4xl font-black text-white tracking-widest uppercase flex items-center gap-4">
            <motion.div
               animate={isActive && !prefersReducedMotion ? { rotate: 360 } : { rotate: 0 }}
               transition={
                 isActive && !prefersReducedMotion
                   ? { duration: 12, repeat: Infinity, ease: "linear" }
                   : { duration: durations.micro, ease: desktopMotionEase }
               }
            >
              <EyeOff size={36} className={isActive ? "text-[var(--color-matrix-green)]" : "text-muted-foreground"} />
            </motion.div>
            {t('privacyShield.title')}
          </h1>
          <p className="text-muted-foreground mt-3 max-w-xl text-lg relative">
            <span className="relative z-10">{t('privacyShield.description')}</span>
          </p>
        </div>
        
        <div className="flex flex-col items-end z-10">
          <motion.div 
            key={threatCount}
            initial={{
              opacity: 0,
              scale: prefersReducedMotion ? 1 : 1.08,
              textShadow: "0 0 18px var(--color-matrix-green)",
            }}
            animate={{
              opacity: 1,
              scale: 1,
              textShadow: isActive ? "0 0 10px var(--color-matrix-green)" : "0 0 0px transparent",
            }}
            transition={{ duration: durations.page, ease: desktopMotionEase }}
            className={`text-6xl font-mono font-black tracking-tighter ${isActive ? "text-[var(--color-matrix-green)]" : "text-muted-foreground"}`}
          >
            {threatCount.toLocaleString()}
          </motion.div>
          <p className={`text-sm tracking-[0.2em] font-bold ${isActive ? "text-[var(--color-matrix-green)]" : "text-muted-foreground"} uppercase`}>{t('privacyShield.threatsNeutralized')}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
        <div className="space-y-6">
          <div className="p-6 rounded-2xl border border-border/50 bg-black/40 backdrop-blur-md relative overflow-hidden group">
            <h3 className="text-xl font-bold flex items-center gap-2 mb-4">
              <ShieldCheck className="text-[var(--color-neon-cyan)]" /> {t('privacyShield.configuration')}
            </h3>
            
            <div className="space-y-4">
              <button
                onClick={() => handleLevelChange("disabled")}
                className={`w-full p-4 rounded-xl border transition-all text-left flex items-start gap-4 ${level === "disabled" ? "border-red-500 bg-red-500/10 shadow-[0_0_15px_rgba(239,68,68,0.2)]" : "border-border/50 hover:bg-white/5"}`}
              >
                <ShieldAlert className={level === "disabled" ? "text-red-500" : "text-muted-foreground"} size={24} />
                <div>
                  <h4 className={`font-bold ${level === "disabled" ? "text-red-500" : ""}`}>{t('privacyShield.disabled')}</h4>
                  <p className="text-sm text-muted-foreground mt-1">{t('privacyShield.disabledDesc')}</p>
                </div>
              </button>

              <button
                onClick={() => handleLevelChange("standard")}
                className={`w-full p-4 rounded-xl border transition-all text-left flex items-start gap-4 ${level === "standard" ? "border-[var(--color-neon-cyan)] bg-[var(--color-neon-cyan)]/10 shadow-[0_0_15px_rgba(0,255,255,0.2)]" : "border-border/50 hover:bg-white/5"}`}
              >
                <Shield className={level === "standard" ? "text-[var(--color-neon-cyan)]" : "text-muted-foreground"} size={24} />
                <div>
                  <h4 className={`font-bold ${level === "standard" ? "text-[var(--color-neon-cyan)]" : ""}`}>{t('privacyShield.standard')}</h4>
                  <p className="text-sm text-muted-foreground mt-1">{t('privacyShield.standardDesc')}</p>
                </div>
              </button>

              <button
                onClick={() => handleLevelChange("strict")}
                className={`w-full p-4 rounded-xl border transition-all text-left flex items-start gap-4 ${level === "strict" ? "border-[var(--color-matrix-green)] bg-[var(--color-matrix-green)]/10 shadow-[0_0_15px_rgba(0,255,136,0.2)]" : "border-border/50 hover:bg-white/5"}`}
              >
                <ShieldCheck className={level === "strict" ? "text-[var(--color-matrix-green)]" : "text-muted-foreground"} size={24} />
                <div>
                  <h4 className={`font-bold ${level === "strict" ? "text-[var(--color-matrix-green)]" : ""}`}>{t('privacyShield.strict')}</h4>
                  <p className="text-sm text-muted-foreground mt-1">{t('privacyShield.strictDesc')}</p>
                </div>
              </button>
            </div>
            
            <div className="mt-6 pt-6 border-t border-border/30">
              <button 
                onClick={handleForceUpdate}
                disabled={isUpdating}
                className="w-full py-3 rounded-lg bg-black/50 border border-white/10 hover:border-white/30 transition-all font-mono text-sm uppercase flex items-center justify-center gap-2"
              >
                <RotateCw className={isUpdating ? "animate-spin" : ""} size={16} /> 
                {isUpdating ? t('privacyShield.syncing') : t('privacyShield.updateDb')}
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-[var(--color-neon-cyan)]/30 bg-black/60 relative overflow-hidden flex flex-col h-[500px]">
          <div className="p-4 border-b border-white/10 flex items-center justify-between bg-black/80 z-10">
            <h3 className="font-bold font-mono tracking-widest text-sm flex items-center gap-2 text-[var(--color-neon-cyan)]">
              <Activity size={16} /> {t('privacyShield.liveFeed')}
            </h3>
            {isActive && <span className="flex h-3 w-3"><span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-[var(--color-matrix-green)] opacity-75"></span><span className="relative inline-flex rounded-full h-3 w-3 bg-[var(--color-matrix-green)]"></span></span>}
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-2 relative no-scrollbar">
            {!isActive && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground/50 opacity-50 z-20">
                <ShieldAlert size={64} className="mb-4" />
                <p className="font-mono">{t('privacyShield.offline')}</p>
              </div>
            )}
            
            <AnimatePresence>
              {recentBlocks.map((block) => (
                <motion.div
                  key={block.id}
                  initial={{ opacity: 0, x: -20, backgroundColor: "rgba(0, 255, 136, 0.2)" }}
                  animate={{ opacity: 1, x: 0, backgroundColor: "rgba(0,0,0,0)" }}
                  className="p-3 rounded border border-white/5 font-mono text-sm flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <AlertTriangle size={14} className="text-red-500 shrink-0" />
                    <span className="truncate text-red-50">{block.domain}</span>
                  </div>
                  <span className="text-xs text-muted-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    {block.time.toLocaleTimeString()}
                  </span>
                </motion.div>
              ))}
            </AnimatePresence>
            
            {isActive && recentBlocks.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground/30 space-y-4">
                <RadioTower size={48} className="animate-pulse" />
                <p className="font-mono text-sm tracking-widest">{t('privacyShield.monitoring')}</p>
              </div>
            )}
          </div>
          
          {/* Scanline overlay */}
          <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] opacity-20 z-10" />
        </div>
      </div>
    </motion.div>
  );
}
