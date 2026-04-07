import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { ShieldAlert, Shield, Activity, GitCommitHorizontal, Play, Square, Settings2 } from "lucide-react";
import { useTranslation } from "react-i18next";

const bgpConfigSchema = z.object({
  remote_address: z.string().min(7, "Invalid IP").max(15),
  remote_port: z.number().min(1).max(65535),
  local_address: z.string().min(7, "Invalid IP").max(15),
  router_id: z.string().min(7, "Invalid IP"),
  as_number: z.number().min(1).max(4294967295),
  remote_as: z.number().min(1).max(4294967295),
  hold_time: z.number().min(3).max(65535),
});

type BgpConfig = z.infer<typeof bgpConfigSchema>;

export function RoutingPage() {
  const { t } = useTranslation();
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [routes, setRoutes] = useState<string[]>([]);

  const form = useForm<BgpConfig>({
    resolver: zodResolver(bgpConfigSchema),
    defaultValues: {
      remote_address: "10.0.0.1",
      remote_port: 179,
      local_address: "10.0.0.2",
      router_id: "10.0.0.2",
      as_number: 64999,
      remote_as: 64999,
      hold_time: 180,
    },
  });

  const fetchStatus = async () => {
    try {
      const adminRes = await invoke<boolean>("check_is_admin");
      setIsAdmin(adminRes);

      const res = await invoke("get_bgp_status");
      setStatus(res);
      const rt = await invoke<string[]>("get_bgp_routes");
      setRoutes(rt);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const onConnect = async (data: BgpConfig) => {
    try {
      await invoke("start_bgp_session", { config: data });
      fetchStatus();
    } catch (e) {
      alert("Failed to start: " + e);
    }
  };

  const onDisconnect = async () => {
    try {
      await invoke("stop_bgp_session");
      fetchStatus();
    } catch (e) {
      alert("Failed to stop: " + e);
    }
  };

  return (
    <div className="flex h-full flex-col p-8 bg-zinc-950 text-white">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-zinc-100 flex items-center gap-2">
          <GitCommitHorizontal className="text-emerald-500 w-8 h-8" />
          {t('routing.title')}
        </h1>
        <p className="text-zinc-400 mt-2 max-w-2xl">
          {t('routing.description')}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 flex-1 min-h-0">
        {/* Left Col: Setup */}
        <div className="space-y-6 flex flex-col">
          <div className="border border-zinc-800 rounded-xl p-6 bg-zinc-900/50">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-zinc-400" /> {t('routing.sessionConfig')}
            </h2>
            <form onSubmit={form.handleSubmit(onConnect)} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400 font-medium uppercase tracking-wider">{t('routing.remoteAddress')}</label>
                  <input {...form.register("remote_address")} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none transition-colors" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400 font-medium uppercase tracking-wider">{t('routing.remotePort')}</label>
                  <input type="number" {...form.register("remote_port", { valueAsNumber: true })} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none transition-colors" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400 font-medium uppercase tracking-wider">{t('routing.localAddress')}</label>
                  <input {...form.register("local_address")} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none transition-colors" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400 font-medium uppercase tracking-wider">{t('routing.routerId')}</label>
                  <input {...form.register("router_id")} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none transition-colors" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400 font-medium uppercase tracking-wider">{t('routing.localAs')}</label>
                  <input type="number" {...form.register("as_number", { valueAsNumber: true })} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none transition-colors" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400 font-medium uppercase tracking-wider">{t('routing.remoteAs')}</label>
                  <input type="number" {...form.register("remote_as", { valueAsNumber: true })} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none transition-colors" />
                </div>
                <div className="space-y-1 col-span-2">
                  <label className="text-xs text-zinc-400 font-medium uppercase tracking-wider">{t('routing.holdTime')}</label>
                  <input type="number" {...form.register("hold_time", { valueAsNumber: true })} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none transition-colors" />
                </div>
              </div>

              <div className="pt-4 flex flex-col gap-3">
                {isAdmin === false ? (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex flex-col items-center justify-center text-center gap-3">
                    <Shield className="w-8 h-8 text-red-500 mb-1" />
                    <p className="text-red-200 text-sm font-medium">{t('routing.adminRequired')}</p>
                    <button type="button" onClick={() => invoke("restart_as_admin")} className="mt-2 w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors">
                      <Shield className="w-4 h-4" /> {t('routing.restartAdmin')}
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-3">
                    <button type="submit" className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-black font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors">
                      <Play className="w-4 h-4 fill-current" /> {t('routing.connectSession')}
                    </button>
                    <button type="button" onClick={onDisconnect} className="px-4 py-2 border border-red-500/50 text-red-500 hover:bg-red-500/10 font-semibold rounded-lg flex items-center gap-2 transition-colors">
                      <Square className="w-4 h-4 fill-current" /> {t('routing.stop')}
                    </button>
                  </div>
                )}
              </div>
            </form>
          </div>
        </div>

        {/* Right Col: Status and Routes */}
        <div className="flex flex-col gap-6">
          <div className="border border-zinc-800 rounded-xl p-6 bg-zinc-900/50 flex flex-col items-center justify-center">
             <Activity className={`w-12 h-12 mb-4 ${status?.state === 'Established' ? 'text-emerald-500' : 'text-zinc-600'}`} />
             <div className="text-2xl font-bold mb-1">{status?.state || "Unknown"}</div>
             <div className="text-zinc-400 text-sm">{t('routing.state')}</div>
             
             {status?.state === 'Established' && (
                <div className="mt-6 flex items-center gap-8 text-center">
                    <div>
                        <div className="text-xl font-mono text-emerald-400">{status.routes_count}</div>
                        <div className="text-xs text-zinc-500 uppercase">{t('routing.routes')}</div>
                    </div>
                    <div>
                        <div className="text-xl font-mono text-blue-400">{status.uptime}s</div>
                        <div className="text-xs text-zinc-500 uppercase">{t('routing.uptime')}</div>
                    </div>
                </div>
             )}
          </div>

          <div className="border border-zinc-800 rounded-xl p-6 bg-zinc-900/50 flex-1 flex flex-col min-h-0">
             <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
               <ShieldAlert className="w-5 h-5 text-amber-500" /> {t('routing.receivedPrefixes')}
             </h3>
             <div className="flex-1 overflow-y-auto bg-zinc-950 rounded-lg border border-zinc-800 p-2 font-mono text-sm text-zinc-400 relative">
               {routes.length === 0 ? (
                  <div className="absolute inset-0 flex items-center justify-center text-zinc-600">
                    {t('routing.noRoutes')}
                  </div>
               ) : (
                  <ul className="space-y-1">
                      {routes.map(r => <li key={r}>{r}</li>)}
                  </ul>
               )}
             </div>
          </div>
        </div>

      </div>
    </div>
  );
}
