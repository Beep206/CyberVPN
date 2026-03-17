import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { getCustomConfig, saveCustomConfig, getActiveCore, saveActiveCore } from "../../shared/api/ipc";
import { Button } from "../../components/ui/button";
import { toast } from "sonner";
import { FileJson, Save, Moon, Sun, Monitor, Cpu } from "lucide-react";
import { useTheme } from "../../app/theme-provider";

export function SettingsPage() {
  const [useCustomConfig, setUseCustomConfig] = useState(false);
  const [jsonConfig, setJsonConfig] = useState("");
  const [activeCore, setActiveCore] = useState<"sing-box" | "xray">("sing-box");
  const [isSaving, setIsSaving] = useState(false);
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    getCustomConfig().then((cfg) => {
      if (cfg) {
        setUseCustomConfig(true);
        setJsonConfig(cfg);
      }
    });
    getActiveCore().then((core) => {
      setActiveCore(core);
    });
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (useCustomConfig) {
        // Basic validation
        JSON.parse(jsonConfig);
        await saveCustomConfig(jsonConfig);
      } else {
        await saveCustomConfig(null);
      }
      await saveActiveCore(activeCore);
      toast.success("Settings saved successfully!");
    } catch (e: any) {
      toast.error(`Invalid JSON or Save Failed: ${e}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCoreChange = async (core: "sing-box" | "xray") => {
    setActiveCore(core);
    try {
      await saveActiveCore(core);
      toast.success(`Active core switched to ${core}`);
    } catch (e: any) {
      toast.error(`Failed to change core: ${e}`);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      transition={{ duration: 0.2 }}
      className="flex flex-col h-full gap-6 pb-6"
    >
      <header className="mb-2">
        <h1 className="text-3xl font-bold tracking-tight text-[var(--color-neon-cyan)] drop-shadow-[0_0_8px_rgba(0,255,255,0.4)]">Settings</h1>
        <p className="text-muted-foreground mt-2">Configure core app preferences and routing.</p>
      </header>

      <div className="flex-1 flex flex-col gap-6">
        {/* Theme Settings */}
        <div className="flex flex-col gap-4 p-6 rounded-xl border border-border/50 bg-black/40">
          <div className="flex items-center justify-between mb-2">
             <div className="flex items-center gap-3 text-lg font-semibold text-[var(--color-neon-cyan)]">
              <Monitor size={24} />
              <h2>Appearance</h2>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Button 
                variant={theme === "dark" ? "default" : "outline"} 
                className={theme === "dark" ? "bg-[var(--color-neon-cyan)] text-black" : ""}
                onClick={() => setTheme("dark")}
            >
                <Moon size={16} className="mr-2" /> Dark
            </Button>
            <Button 
                variant={theme === "light" ? "default" : "outline"} 
                className={theme === "light" ? "bg-[var(--color-neon-cyan)] text-black" : ""}
                onClick={() => setTheme("light")}
            >
                <Sun size={16} className="mr-2" /> Light
            </Button>
            <Button 
                variant={theme === "system" ? "default" : "outline"} 
                className={theme === "system" ? "bg-[var(--color-neon-cyan)] text-black" : ""}
                onClick={() => setTheme("system")}
            >
                <Monitor size={16} className="mr-2" /> System
            </Button>
          </div>
        </div>

        {/* Proxy Engine Core Settings */}
        <div className="flex flex-col gap-4 p-6 rounded-xl border border-border/50 bg-black/40">
          <div className="flex items-center justify-between mb-2">
             <div className="flex items-center gap-3 text-lg font-semibold text-[var(--color-matrix-green)]">
              <Cpu size={24} />
              <h2>Proxy Engine Core</h2>
            </div>
          </div>
          <p className="text-sm text-muted-foreground mb-2">
             Sing-box is recommended for modern protocols (Hysteria2, TUIC), while Xray-core provides legacy compatibility.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <Button 
                variant={activeCore === "sing-box" ? "default" : "outline"} 
                className={activeCore === "sing-box" ? "bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80" : ""}
                onClick={() => handleCoreChange("sing-box")}
            >
                Sing-box (Modern)
            </Button>
            <Button 
                variant={activeCore === "xray" ? "default" : "outline"} 
                className={activeCore === "xray" ? "bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80" : ""}
                onClick={() => handleCoreChange("xray")}
            >
                Xray (Legacy)
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-4 p-6 rounded-xl border border-border/50 bg-black/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 text-lg font-semibold text-[var(--color-neon-pink)]">
              <FileJson size={24} />
              <h2>Raw "Power-User" Configuration</h2>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                value="" 
                className="sr-only peer" 
                checked={useCustomConfig}
                onChange={(e) => setUseCustomConfig(e.target.checked)}
              />
              <div className="w-11 h-6 bg-muted outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--color-neon-pink)]"></div>
            </label>
          </div>
          
          <p className="text-sm text-muted-foreground">
            Override the generated sing-box configuration entirely. When enabled, this exact JSON payload will be written to `run.json` and executed. The normal connection profiles and routing settings will be ignored.
          </p>

          <AnimatePresence>
              {useCustomConfig && (
                  <motion.div
                     initial={{ opacity: 0, height: 0 }}
                     animate={{ opacity: 1, height: "auto" }}
                     exit={{ opacity: 0, height: 0 }}
                     className="flex flex-col gap-4 mt-2"
                  >
                      <textarea
                        value={jsonConfig}
                        onChange={(e) => setJsonConfig(e.target.value)}
                        className="w-full h-80 bg-[#0d0d0d] font-mono text-sm border border-border/60 rounded-md p-4 text-[#a0a0a0] focus:text-[var(--color-neon-cyan)] focus:border-[var(--color-neon-cyan)] outline-none resize-none"
                        placeholder='{\n  "log": { "level": "info" },\n  "inbounds": [...],\n  "outbounds": [...]\n}'
                        spellCheck={false}
                      />
                  </motion.div>
              )}
          </AnimatePresence>
          
          <div className="flex justify-end mt-2 pt-4 border-t border-border/30">
            <Button onClick={handleSave} disabled={isSaving} className="gap-2 bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80">
              <Save size={16} />
              {isSaving ? "Saving..." : "Save Settings"}
            </Button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
