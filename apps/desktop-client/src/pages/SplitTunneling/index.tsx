import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect, useMemo } from "react";
import {
  AppInfo,
  getInstalledApps,
  getSplitTunnelingApps,
  saveSplitTunnelingApps,
  getSplitTunnelingMode,
  saveSplitTunnelingMode,
} from "../../shared/api/ipc";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Switch } from "../../components/ui/switch";
import { toast } from "sonner";
import {
  Search,
  Gamepad2,
  Globe,
  ShieldCheck,
  ShieldAlert,
  Check,
  Loader2,
  Box,
  Route
} from "lucide-react";

export function SplitTunnelingPage() {
  const [apps, setApps] = useState<AppInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  
  const [selectedApps, setSelectedApps] = useState<Set<string>>(new Set());
  const [mode, setMode] = useState<"allow" | "disallow">("allow");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [sysApps, savedApps, savedMode] = await Promise.all([
          getInstalledApps(),
          getSplitTunnelingApps(),
          getSplitTunnelingMode(),
        ]);
        setApps(sysApps);
        setSelectedApps(new Set(savedApps));
        setMode(savedMode as "allow" | "disallow");
      } catch (e: any) {
        toast.error(`Failed to load apps: ${e}`);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const filteredApps = useMemo(() => {
    if (!search) return apps;
    const lower = search.toLowerCase();
    return apps.filter(
      (a) =>
        a.name.toLowerCase().includes(lower) ||
        a.packageName.toLowerCase().includes(lower)
    );
  }, [apps, search]);

  const handleToggleApp = (packageName: string) => {
    const next = new Set(selectedApps);
    if (next.has(packageName)) {
      next.delete(packageName);
    } else {
      next.add(packageName);
    }
    setSelectedApps(next);
  };

  const applyPreset = (preset: "gaming" | "browsing") => {
    const next = new Set(selectedApps);
    const keywords =
      preset === "gaming"
        ? ["steam", "epic", "battlenet", "gog", "riot", "origin", "xbox"]
        : ["chrome", "firefox", "brave", "edge", "safari", "opera"];

    apps.forEach((a) => {
      const lowerName = a.name.toLowerCase();
      if (keywords.some((kw) => lowerName.includes(kw))) {
        next.add(a.packageName);
      }
    });

    setSelectedApps(next);
    toast.success(`Applied ${preset} preset!`);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveSplitTunnelingMode(mode);
      await saveSplitTunnelingApps(Array.from(selectedApps));
      toast.success("Split tunneling configuration saved!");
    } catch (e: any) {
      toast.error(`Failed to save: ${e}`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="max-w-4xl mx-auto space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-[var(--color-matrix-green)] to-[var(--color-neon-cyan)] bg-clip-text text-transparent">
            Split Tunneling
          </h1>
          <p className="text-muted-foreground mt-1">
            Intelligently route specific applications through or around the VPN.
          </p>
        </div>
        <Button
          onClick={handleSave}
          disabled={isSaving || loading}
          className="bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80 gap-2"
        >
          {isSaving ? <Loader2 className="animate-spin" size={18} /> : <Check size={18} />}
          Save Configuration
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Column: Controls & Mode */}
        <div className="space-y-6">
          <div className="p-6 rounded-xl border border-[var(--color-matrix-green)]/30 bg-black/40 shadow-[0_0_15px_rgba(0,255,136,0.1)]">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Route size={20} className="text-[var(--color-matrix-green)]" />
              Operation Mode
            </h2>
            
            <div className="space-y-4">
              <button
                onClick={() => setMode("allow")}
                className={`w-full text-left p-4 rounded-lg border transition-all duration-300 ${
                  mode === "allow"
                    ? "border-[var(--color-matrix-green)] bg-[var(--color-matrix-green)]/10"
                    : "border-border/50 hover:border-border"
                }`}
              >
                <div className="flex items-center gap-3 mb-1">
                  <ShieldCheck
                    size={20}
                    className={mode === "allow" ? "text-[var(--color-matrix-green)]" : "text-muted-foreground"}
                  />
                  <span className="font-medium text-[var(--color-matrix-green)]">Exclusive VPN (Allow)</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  ONLY selected apps will be secured by the VPN. All other traffic skips the tunnel.
                </p>
              </button>

              <button
                onClick={() => setMode("disallow")}
                className={`w-full text-left p-4 rounded-lg border transition-all duration-300 ${
                  mode === "disallow"
                    ? "border-red-500 bg-red-500/10"
                    : "border-border/50 hover:border-border"
                }`}
              >
                <div className="flex items-center gap-3 mb-1">
                  <ShieldAlert
                    size={20}
                    className={mode === "disallow" ? "text-red-500" : "text-muted-foreground"}
                  />
                  <span className="font-medium text-red-500">Bypass VPN (Disallow)</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Selected apps will BYPASS the VPN. All other traffic is secured by default.
                </p>
              </button>
            </div>
          </div>

          <div className="p-6 rounded-xl border border-border/50 bg-black/40">
            <h2 className="text-lg font-semibold mb-4 text-white">Quick Presets</h2>
            <div className="space-y-3">
              <Button
                variant="outline"
                className="w-full justify-start gap-3 hover:bg-[var(--color-neon-pink)] hover:text-white hover:border-[var(--color-neon-pink)] transition-colors"
                onClick={() => applyPreset("gaming")}
                disabled={loading}
              >
                <Gamepad2 size={18} /> Add Gaming Clients
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start gap-3 hover:bg-[var(--color-neon-cyan)] hover:text-black hover:border-[var(--color-neon-cyan)] transition-colors"
                onClick={() => applyPreset("browsing")}
                disabled={loading}
              >
                <Globe size={18} /> Add Web Browsers
              </Button>
            </div>
          </div>
        </div>

        {/* Right Column: App Picker */}
        <div className="md:col-span-2 flex flex-col h-[600px]">
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
            <Input
              placeholder="Search installed applications..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 bg-black/50 border-border/50 focus-visible:ring-[var(--color-matrix-green)]"
            />
          </div>

          <div className="flex-1 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
            {loading ? (
              // Skeleton loading state
              Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 p-4 rounded-lg border border-border/20 bg-card/20 animate-pulse">
                  <div className="w-10 h-10 rounded bg-muted/50" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-muted/50 rounded w-1/3" />
                    <div className="h-3 bg-muted/50 rounded w-1/4" />
                  </div>
                  <div className="w-10 h-6 rounded-full bg-muted/50" />
                </div>
              ))
            ) : filteredApps.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50">
                <Box size={48} className="mb-4" />
                <p>No compatible applications found.</p>
              </div>
            ) : (
              <AnimatePresence>
                {filteredApps.map((app) => (
                  <motion.div
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    key={app.packageName}
                    className="flex items-center gap-4 p-3 rounded-lg border border-border/30 bg-card/40 hover:bg-card/80 transition-colors"
                    onClick={() => handleToggleApp(app.packageName)}
                  >
                    {app.iconBase64 ? (
                      <img src={app.iconBase64} alt="" className="w-10 h-10 object-contain rounded drop-shadow-md" />
                    ) : (
                      <div className="w-10 h-10 bg-muted/30 rounded flex items-center justify-center text-muted-foreground shrink-0 border border-border/50">
                        <Box size={20} />
                      </div>
                    )}
                    
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-sm truncate">{app.name}</h3>
                      <p className="text-xs text-muted-foreground truncate opacity-70" title={app.execPath}>
                        {app.packageName}
                      </p>
                    </div>

                    <Switch
                      checked={selectedApps.has(app.packageName)}
                      onCheckedChange={() => handleToggleApp(app.packageName)}
                      className="data-[state=checked]:bg-[var(--color-matrix-green)]"
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
