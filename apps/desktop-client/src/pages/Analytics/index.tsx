import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { getUsageHistory, getGlobalFootprint, UsageRecord } from "../../shared/api/ipc";
import { BarChart, Bar, ResponsiveContainer, XAxis, Tooltip, PieChart, Pie, Cell, Label } from "recharts";
import { Globe, Shield, Activity, HardDrive } from "lucide-react";
import { toast } from "sonner";

// High tech formatting tools
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export function AnalyticsPage() {
  const [history, setHistory] = useState<UsageRecord[]>([]);
  const [footprint, setFootprint] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTelemetry() {
      try {
        const hist = await getUsageHistory("30d");
        const foot = await getGlobalFootprint();
        setHistory(hist);
        setFootprint(foot);
      } catch (err: any) {
        toast.error(`SysError pulling telemetry graph: ${err}`);
      } finally {
        setLoading(false);
      }
    }
    fetchTelemetry();
  }, []);

  // Compute charts aggregations
  const aggregateDaily = () => {
    const map = new Map<string, number>();
    history.forEach(r => {
      map.set(r.date, (map.get(r.date) || 0) + r.bytes_up + r.bytes_down);
    });
    return Array.from(map.entries()).map(([date, bytes]) => ({ date: date.split('-').slice(1).join('/'), bytes })).slice(-14);
  };

  const aggregateProtocols = () => {
    const map = new Map<string, number>();
    history.forEach(r => {
      map.set(r.protocol, (map.get(r.protocol) || 0) + r.bytes_up + r.bytes_down);
    });
    const colors = ["#00ffff", "#ff00ff", "#00ff88", "#ffff00", "#ff3333"];
    return Array.from(map.entries()).map(([name, value], idx) => ({ name, value, color: colors[idx % colors.length] }));
  };

  const dailyData = aggregateDaily();
  const protocolData = aggregateProtocols();

  const totalBytes = history.reduce((acc, r) => acc + r.bytes_up + r.bytes_down, 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-6xl mx-auto space-y-6"
    >
      <header className="flex justify-between items-end border-b border-white/5 pb-4 mb-8">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tighter text-[var(--color-neon-cyan)] uppercase" style={{ textShadow: "0 0 15px rgba(0,255,255,0.4)" }}>
            Command Center
          </h1>
          <p className="text-muted-foreground font-mono text-sm mt-2 flex items-center gap-2">
            <Activity className="text-[var(--color-neon-cyan)]" size={16} /> Global Telemetry & Traffic Historian
          </p>
        </div>
      </header>

      {/* Top Banner Stats */}
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-black/40 border border-[var(--color-neon-cyan)]/20 rounded-xl p-6 backdrop-blur">
          <Globe className="text-[var(--color-neon-cyan)] mb-4" size={24} />
          <div className="text-sm font-mono text-muted-foreground uppercase">Global Footprint</div>
          <div className="text-3xl font-bold mt-1">{Object.keys(footprint).length} <span className="text-base text-white/50">Regions</span></div>
        </div>
        <div className="bg-black/40 border border-[#ff00ff]/20 rounded-xl p-6 backdrop-blur relative overflow-hidden">
          <div className="absolute inset-0 bg-[#ff00ff]/5" />
          <HardDrive className="text-[#ff00ff] mb-4 relative z-10" size={24} />
          <div className="text-sm font-mono text-muted-foreground uppercase relative z-10">Total Bandwidth (30d)</div>
          <div className="text-3xl font-bold mt-1 text-white relative z-10">{formatBytes(totalBytes)}</div>
        </div>
        <div className="bg-black/40 border border-[var(--color-matrix-green)]/20 rounded-xl p-6 backdrop-blur">
          <Shield className="text-[var(--color-matrix-green)] mb-4" size={24} />
          <div className="text-sm font-mono text-muted-foreground uppercase">Privacy Actions</div>
          <div className="text-3xl font-bold mt-1 text-[var(--color-matrix-green)]">Secured</div>
          {/* Milestone text */}
          <div className="text-xs text-[var(--color-matrix-green)]/70 mt-2 font-mono">You've saved roughly {formatBytes(totalBytes * 0.15)} of ad-data this month.</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6 h-[400px]">
        {/* Main Bar Chart */}
        <div className="col-span-2 bg-black/40 border border-white/10 rounded-xl p-6 backdrop-blur flex flex-col">
          <h3 className="text-lg font-bold font-mono tracking-wider mb-6 text-white/80">DATA USAGE OVER TIME</h3>
          <div className="flex-1 w-full relative">
            {loading ? (
              <div className="absolute inset-0 flex items-center justify-center font-mono text-[var(--color-neon-cyan)] animate-pulse">Loading Telemetry...</div>
            ) : dailyData.length === 0 ? (
                <div className="absolute inset-0 flex items-center justify-center font-mono text-white/30">No usage data found for this period.</div>
            ) : (
                <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dailyData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <XAxis dataKey="date" stroke="rgba(255,255,255,0.2)" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip 
                        cursor={{fill: 'rgba(0,255,255,0.05)'}} 
                        contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', borderColor: 'var(--color-neon-cyan)', borderRadius: '8px', color: '#fff' }}
                        formatter={(value: any) => [formatBytes(value as number), "Traffic"]}
                    />
                    <Bar dataKey="bytes" fill="var(--color-neon-cyan)" radius={[4, 4, 0, 0]} />
                </BarChart>
                </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Protocol Donut Chart */}
        <div className="col-span-1 bg-black/40 border border-white/10 rounded-xl p-6 backdrop-blur flex flex-col">
          <h3 className="text-lg font-bold font-mono tracking-wider mb-6 text-white/80 text-center">PROTOCOL DISTRIBUTION</h3>
          <div className="flex-1 w-full relative -mt-4">
             <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={protocolData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {protocolData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                  <Label 
                    value="PROTOCOLS" position="center" 
                    style={{ fill: 'var(--color-neon-cyan)', fontSize: '12px', fontWeight: 'bold', fontFamily: 'monospace', opacity: 0.7 }}
                  />
                </Pie>
                <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(0,0,0,0.9)', borderColor: '#333', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff' }}
                    formatter={(value: any) => formatBytes(value as number)}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          {/* Legend */}
          <div className="mt-4 flex flex-col gap-2 font-mono text-xs">
              {protocolData.map(p => (
                  <div key={p.name} className="flex justify-between items-center border-b border-white/5 pb-1">
                      <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
                          <span className="uppercase text-white/80">{p.name}</span>
                      </div>
                      <span className="text-white/60">{formatBytes(p.value)}</span>
                  </div>
              ))}
          </div>
        </div>
      </div>

      {/* Interactive Map (Stylized CSS Grid instead of raw SVG path for native feeling) */}
      <div className="bg-black/60 border border-[var(--color-neon-cyan)]/20 rounded-xl p-6 backdrop-blur overflow-hidden relative group">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.05)_0%,transparent_100%)] opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
          <h3 className="text-lg font-bold font-mono tracking-wider mb-6 text-[var(--color-neon-cyan)] flex items-center gap-2">
              <Globe size={18} /> ACTIVE GLOBAL MAPPING
          </h3>
          
          <div className="flex flex-wrap gap-4 relative z-10">
              {Object.entries(footprint).length === 0 ? (
                  <div className="text-muted-foreground font-mono text-sm">No telemetry footprint captured yet.</div>
              ) : (
                  Object.entries(footprint).map(([country, bytes]) => (
                      <div key={country} className="flex items-center gap-3 px-4 py-3 bg-[var(--color-neon-cyan)]/10 border border-[var(--color-neon-cyan)]/30 rounded-lg">
                          <div className="relative flex h-3 w-3">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-neon-cyan)] opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-3 w-3 bg-[var(--color-neon-cyan)]"></span>
                          </div>
                          <div className="font-mono">
                              <div className="font-bold text-lg text-white">{country}</div>
                              <div className="text-xs text-[var(--color-neon-cyan)]">{formatBytes(bytes)} Transmitted</div>
                          </div>
                      </div>
                  ))
              )}
          </div>

          {/* Aesthetic Scanline overlay */}
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(0,0,0,0)_50%,rgba(0,0,0,0.1)_50%)] bg-[length:100%_4px] mix-blend-overlay z-20 opacity-30" />
      </div>

    </motion.div>
  );
}
