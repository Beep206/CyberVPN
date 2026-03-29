import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { Brain, Wifi, ShieldAlert, CheckCircle2, Home, Briefcase, Coffee, ShieldCheck, Cpu } from "lucide-react";
import { toast } from "sonner";
import {
  getSmartConnectStatus,
  setSmartConnectStatus,
  getNetworkRules,
  updateNetworkRule,
  listenNetworkChanged,
  NetworkProfile
} from "../../shared/api/ipc";

export function AutomationPage() {
  const [isSmartEnabled, setIsSmartEnabled] = useState(false);
  const [currentNetwork, setCurrentNetwork] = useState<string>("Scanning...");
  const [rules, setRules] = useState<Record<string, NetworkProfile>>({});

  useEffect(() => {
    getSmartConnectStatus().then(setIsSmartEnabled).catch(console.error);
    getNetworkRules().then(setRules).catch(console.error);

    const unlisten = listenNetworkChanged((event) => {
      setCurrentNetwork(event.ssid);
      toast.info(`Network shifted to: ${event.ssid}`);
    });

    return () => {
      unlisten();
    };
  }, []);

  const handleToggle = async (enabled: boolean) => {
    try {
      await setSmartConnectStatus(enabled);
      setIsSmartEnabled(enabled);
      toast.success(enabled ? "Intelligent Automation online." : "Automation suspended.");
    } catch (e: any) {
      toast.error(`Automation toggle failed: ${e}`);
    }
  };

  const handleCreateRule = async (ssid: string, p: NetworkProfile) => {
    try {
      await updateNetworkRule(ssid, p);
      setRules((prev) => ({ ...prev, [ssid]: p }));
      toast.success(`Network "${ssid}" classification applied.`);
    } catch (e: any) {
      toast.error(`Constraint failure: ${e}`);
    }
  };

  const getIcon = (type: string) => {
    switch(type) {
      case "home": return <Home size={18} className="text-blue-400" />;
      case "work": return <Briefcase size={18} className="text-purple-400" />;
      case "coffee": return <Coffee size={18} className="text-orange-400" />;
      default: return <Wifi size={18} className="text-gray-400" />;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="p-8 max-w-5xl mx-auto space-y-8 min-h-full"
    >
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
        <div>
          <h1 className="text-4xl font-black text-white tracking-widest uppercase flex items-center gap-4">
            <Brain size={36} className="text-[var(--color-neon-pink)] drop-shadow-[0_0_15px_rgba(255,0,255,0.7)]" />
            Smart Connect
          </h1>
          <p className="text-muted-foreground mt-3 max-w-xl text-lg">
            Neural environment awareness. Automatically shift VPN protocols and shields based on network hostility.
          </p>
        </div>
        
        <div className="flex flex-col items-end">
          <label className="flex items-center gap-3 cursor-pointer p-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors">
            <span className={`text-sm tracking-widest uppercase font-bold ${isSmartEnabled ? "text-[var(--color-neon-cyan)]" : "text-muted-foreground"}`}>
              {isSmartEnabled ? "System Active" : "System Dormant"}
            </span>
            <div className={`relative w-14 h-7 flex items-center rounded-full p-1 transition-colors ${isSmartEnabled ? "bg-[var(--color-neon-cyan)]" : "bg-black"}`}>
              <motion.div
                layout
                className="bg-white w-5 h-5 rounded-full shadow-md"
                animate={{ x: isSmartEnabled ? 28 : 0 }}
                transition={{ type: "spring", stiffness: 700, damping: 30 }}
                onClick={() => handleToggle(!isSmartEnabled)}
              />
            </div>
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 relative z-10 w-full mt-10">
        
        {/* Radar Card */}
        <div className="rounded-2xl border border-border/50 bg-black/40 backdrop-blur-md relative overflow-hidden flex flex-col items-center justify-center p-12 min-h-[300px]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.05)_0%,rgba(0,0,0,0)_70%)] pointer-events-none" />
          
          <div className="relative z-10 flex flex-col items-center gap-6">
            <div className="relative">
              <motion.div 
                animate={isSmartEnabled ? { scale: [1, 1.5, 2], opacity: [0.8, 0.4, 0] } : {}}
                transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
                className="absolute inset-0 rounded-full bg-[var(--color-neon-cyan)] z-0"
              />
              <div className="w-24 h-24 rounded-full border border-[var(--color-neon-cyan)]/50 bg-black/80 flex items-center justify-center z-10 relative backdrop-blur shadow-[0_0_30px_rgba(0,255,255,0.2)]">
                <Wifi size={40} className="text-[var(--color-neon-cyan)]" />
              </div>
            </div>
            
            <div className="text-center space-y-2">
              <p className="text-sm font-mono tracking-widest text-[var(--color-neon-cyan)] uppercase">Current Environmental Vector</p>
              <h2 className="text-3xl font-black text-white">{currentNetwork}</h2>
            </div>
            
            <div className="flex gap-4 mt-4">
              <button 
                onClick={() => handleCreateRule(currentNetwork, { auto_connect: false, stealth_required: false, kill_switch_required: false, icon_type: "home" })}
                className="flex flex-col items-center gap-2 p-3 rounded-xl hover:bg-white/5 transition-colors border border-transparent hover:border-white/10"
              >
                <Home size={24} className="text-blue-400" />
                <span className="text-xs uppercase tracking-wider font-bold text-muted-foreground">Home</span>
              </button>
              
              <button 
                onClick={() => handleCreateRule(currentNetwork, { auto_connect: true, stealth_required: true, kill_switch_required: true, icon_type: "public" })}
                className="flex flex-col items-center gap-2 p-3 rounded-xl hover:bg-white/5 transition-colors border border-transparent hover:border-white/10"
              >
                <ShieldAlert size={24} className="text-red-400" />
                <span className="text-xs uppercase tracking-wider font-bold text-muted-foreground">Hostile</span>
              </button>
            </div>
          </div>
        </div>

        {/* Configurations List */}
        <div className="space-y-6">
          <h3 className="text-xl font-bold flex items-center gap-3">
             <Cpu className="text-[var(--color-neon-pink)]" /> Enforced Policies
          </h3>
          
          <div className="grid gap-3 max-h-[400px] overflow-y-auto no-scrollbar pr-2">
            {Object.entries(rules).map(([ssid, profile]) => (
              <motion.div 
                initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                key={ssid} 
                className="p-4 rounded-xl border border-border/30 bg-black/30 flex items-center justify-between group hover:border-white/20 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                    {getIcon(profile.icon_type)}
                  </div>
                  <div>
                    <h4 className="font-bold font-mono tracking-wide text-white">{ssid}</h4>
                    <span className="text-xs text-muted-foreground uppercase tracking-widest">
                       {profile.auto_connect ? "Auto-Shield active" : "Trusted Sector"}
                    </span>
                  </div>
                </div>
                
                {profile.auto_connect ? (
                  <ShieldCheck size={20} className="text-[var(--color-matrix-green)] opacity-50 group-hover:opacity-100 transition-opacity" />
                ) : (
                  <CheckCircle2 size={20} className="text-blue-400 opacity-50 group-hover:opacity-100 transition-opacity" />
                )}
              </motion.div>
            ))}
            
            {Object.keys(rules).length === 0 && (
              <div className="p-8 border border-dashed border-white/10 rounded-2xl flex flex-col items-center text-center text-muted-foreground/50 gap-4">
                 <ShieldAlert size={32} />
                 <p className="font-mono text-sm tracking-widest">NO RULES CONFIGURED</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
