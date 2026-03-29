import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, ShieldAlert, Activity, ShieldCheck, Zap, AlertTriangle, Play } from "lucide-react";
import { toast } from "sonner";
import {
  CensorshipReport,
  runStealthDiagnostics,
  applyStealthFix,
  listenStealthProbeLog,
  getProfiles,
  ProxyNode
} from "../../shared/api/ipc";

export function StealthLabPage() {
  const [activeNode, setActiveNode] = useState<ProxyNode | null>(null);
  const [isProbing, setIsProbing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [report, setReport] = useState<CensorshipReport | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getProfiles().then((res) => {
      // For diagnostic purposes, we grab the first profile or a specific one
      if (res && res.length > 0) {
          setActiveNode(res[0]);
      }
    });

    const unlisten = listenStealthProbeLog((log: string) => {
      setLogs((prev) => [...prev, log]);
    });

    return () => {
      unlisten();
    };
  }, []);

  useEffect(() => {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleStartDiagnostics = async () => {
    if (!activeNode) {
        toast.error("No active proxy node found to run diagnostics on.");
        return;
    }
    
    setIsProbing(true);
    setLogs([]);
    setReport(null);

    try {
        const result = await runStealthDiagnostics(activeNode.id);
        setReport(result);
        toast.success("Diagnostic Suite Complete.");
    } catch (e: any) {
        toast.error(`Diagnostic Failed: ${e}`);
        setLogs(prev => [...prev, `CRITICAL FAILURE: ${e}`]);
    } finally {
        setIsProbing(false);
    }
  };

  const handleFixIt = async () => {
      if (!report || !activeNode) return;
      try {
          toast.loading("Applying Stealth Protocols...");
          await applyStealthFix(activeNode.id, report.recommended_protocol);
          toast.success("Connection re-established with Stealth settings.");
      } catch (e: any) {
          toast.error(`Fix application failed: ${e}`);
      }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="p-8 max-w-5xl mx-auto space-y-8 min-h-full font-sans"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-[var(--color-neon-magenta)]/30 pb-6">
        <div>
          <h1 className="text-4xl font-black text-white tracking-widest uppercase flex items-center gap-4">
            <Terminal size={36} className="text-[#ff00ff] drop-shadow-[0_0_15px_rgba(255,0,255,0.7)]" />
            Stealth Lab
          </h1>
          <p className="text-muted-foreground mt-3 max-w-xl text-lg">
            Surgical deep-packet inspection diagnostics. Overcome extreme ISP censorship environments.
          </p>
        </div>
        <div className="flex flex-col items-end">
          <div className="flex items-center gap-2 p-3 rounded-xl bg-black/50 border border-[#ff00ff]/20">
             <Activity className={isProbing ? "text-[#ff00ff] animate-pulse" : "text-muted-foreground"} />
             <span className="font-mono text-xs tracking-widest uppercase text-white">
                 {isProbing ? "PROBING ACTIVE" : "SYSTEM IDLE"}
             </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 h-[500px]">
          {/* Main Terminal Window */}
          <div className="lg:col-span-3 rounded-2xl border border-white/10 bg-black/60 relative overflow-hidden flex flex-col shadow-[inset_0_0_50px_rgba(0,0,0,0.8)]">
              <div className="p-4 border-b border-white/10 flex items-center justify-between bg-black/80 z-10 w-full">
                  <span className="font-mono text-xs tracking-widest text-[#ff00ff] flex items-center gap-2">
                       {">"} root@cybervpn:/opt/diagnostics
                  </span>
                  <div className="flex gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500/50" />
                      <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                      <div className="w-3 h-3 rounded-full bg-green-500/50" />
                  </div>
              </div>
              
              <div className="flex-1 p-6 font-mono text-sm overflow-y-auto space-y-2 no-scrollbar text-[var(--color-neon-cyan)] relative z-10">
                 {logs.length === 0 && !isProbing && (
                     <div className="opacity-50 text-center flex flex-col items-center justify-center h-full space-y-4">
                        <Play size={48} className="text-white/20" />
                        <span>AWAITING EXECUTION COMMAND...</span>
                     </div>
                 )}
                 {logs.map((log, i) => (
                     <motion.div 
                        initial={{ opacity: 0, x: -10 }} 
                        animate={{ opacity: 1, x: 0 }} 
                        key={i}
                        className={log.includes("[BLOCKED]") || log.includes("[INTERCEPTED") || log.includes("FAILURE") ? "text-red-400" : "text-[var(--color-neon-cyan)]"}
                     >
                        {">"} {log}
                     </motion.div>
                 ))}
                 <div ref={logsEndRef} />
              </div>
              
              {/* Terminal Scanline overlay */}
              <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,255,0.03),rgba(0,255,255,0.02))] bg-[length:100%_4px,3px_100%] opacity-40 z-20" />
          </div>

          /* Action Panel */
          <div className="lg:col-span-2 flex flex-col gap-6">
              <div className="p-6 rounded-2xl border border-border/50 bg-black/40 backdrop-blur-md relative overflow-hidden">
                   <h3 className="text-xl font-bold flex items-center gap-2 mb-4 text-white">
                       <ShieldAlert className="text-[#ff00ff]" /> Action Center
                   </h3>
                   <div className="space-y-4">
                       <p className="text-sm text-muted-foreground leading-relaxed">
                           Initiate a comprehensive sweep of your ISP's DPI fingerprinting methods. We will identify precisely which filters are blocking connection.
                       </p>
                       <button
                           onClick={handleStartDiagnostics}
                           disabled={isProbing || !activeNode}
                           className="w-full py-4 rounded-xl bg-[#ff00ff]/10 hover:bg-[#ff00ff]/20 border border-[#ff00ff]/50 text-[#ff00ff] transition-all font-mono tracking-widest uppercase font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                       >
                           {isProbing ? <><Activity className="animate-spin" size={18} /> PROBING...</> : <><Zap size={18} /> INITIATE SWEEP</>}
                       </button>
                   </div>
              </div>

              <AnimatePresence>
                  {report && (
                       <motion.div 
                           initial={{ opacity: 0, scale: 0.95 }}
                           animate={{ opacity: 1, scale: 1 }}
                           className="flex-1 p-6 rounded-2xl border border-[#ff00ff] bg-[#ff00ff]/5 flex flex-col backdrop-blur-md shadow-[0_0_30px_rgba(255,0,255,0.15)]"
                       >
                           <h3 className="text-lg font-bold flex items-center gap-2 mb-4 text-white uppercase tracking-wider">
                               <AlertTriangle className="text-[#ff00ff]" size={20} /> Diagnostic Outcome
                           </h3>
                           
                           <div className="grid grid-cols-2 gap-3 mb-6">
                               <div className={`p-3 rounded border text-xs font-mono uppercase text-center ${report.ip_blocked ? "border-red-500/50 bg-red-500/10 text-red-400" : "border-green-500/30 text-green-400"}`}>IP BAN: {report.ip_blocked ? "DETECTED" : "CLEAR"}</div>
                               <div className={`p-3 rounded border text-xs font-mono uppercase text-center ${report.sni_filtered ? "border-red-500/50 bg-red-500/10 text-red-400" : "border-green-500/30 text-green-400"}`}>SNI FILTER: {report.sni_filtered ? "DETECTED" : "CLEAR"}</div>
                               <div className={`p-3 rounded border text-xs font-mono uppercase text-center ${report.udp_blocked ? "border-red-500/50 bg-red-500/10 text-red-400" : "border-green-500/30 text-green-400"}`}>UDP QoS: {report.udp_blocked ? "THROTTLED" : "PERMITTED"}</div>
                               <div className={`p-3 rounded border text-xs font-mono uppercase text-center ${report.tls_intercepted ? "border-red-500/50 bg-red-500/10 text-red-400" : "border-green-500/30 text-green-400"}`}>TLS MITM: {report.tls_intercepted ? "DETECTED" : "CLEAR"}</div>
                           </div>

                           <div className="bg-black/50 p-4 rounded-xl border border-white/10 mb-6 flex-1">
                               <p className="text-sm text-gray-300 leading-relaxed font-mono">
                                   {report.recommended_action}
                               </p>
                           </div>

                           <button
                               onClick={handleFixIt}
                               className="w-full py-4 rounded-xl bg-white text-black hover:bg-gray-200 transition-colors font-bold uppercase tracking-widest text-sm flex items-center justify-center gap-2 shadow-lg"
                           >
                               <ShieldCheck size={18} /> FIX IT FOR ME
                           </button>
                       </motion.div>
                  )}
              </AnimatePresence>
          </div>
      </div>
    </motion.div>
  );
}
