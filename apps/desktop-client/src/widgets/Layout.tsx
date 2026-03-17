import { Outlet, Link, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { Activity, Shield, Settings, Route, Rss, Split, WifiHigh } from "lucide-react";
import { Toaster } from "../components/ui/sonner";
import { toast } from "sonner";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { Titlebar } from "./Titlebar";

export function Layout() {
  const location = useLocation();

  useEffect(() => {
    async function checkForUpdates() {
      try {
        const update = await check();
        if (update) {
          toast.info(`Update Available: ${update.version}`, {
            description: "A new version of CyberVPN is ready to install.",
            action: {
              label: "Install & Relaunch",
              onClick: async () => {
                toast.loading("Downloading and installing update...");
                await update.downloadAndInstall();
                await relaunch();
              }
            },
            duration: Number.POSITIVE_INFINITY,
          });
        }
      } catch (err) {
        console.error("Failed to check for updates:", err);
      }
    }

    const timer = setTimeout(checkForUpdates, 3000);
    return () => clearTimeout(timer);
  }, []);

  const navItems = [
    { path: "/", label: "Dashboard", icon: Activity },
    { path: "/security", label: "Safety Center", icon: Shield },
    { path: "/profiles", label: "Profiles", icon: Shield },
    { path: "/routing", label: "Routing", icon: Route },
    { path: "/hotspot", label: "Hotspot", icon: WifiHigh },
    { path: "/split-tunneling", label: "Split Tunneling", icon: Split },
    { path: "/subscriptions", label: "Subscriptions", icon: Rss },
    { path: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans pt-10">
      <Titlebar />
      {/* Sidebar */}
      <aside className="w-64 border-r border-border/40 bg-card/30 backdrop-blur flex flex-col items-center py-8 z-10">
        <div className="mb-12 font-bold text-2xl tracking-widest text-[var(--color-matrix-green)] drop-shadow-[0_0_10px_rgba(0,255,136,0.8)] flex items-center gap-3">
           <Shield size={28} />
           CYBERVPN
        </div>

        <nav className="w-full flex-1 px-4 space-y-2">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            
            return (
              <Link 
                to={item.path} 
                key={item.path}
                className="relative flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors"
                style={{
                  color: isActive ? "var(--color-matrix-green)" : "var(--muted-foreground)"
                }}
              >
                {isActive && (
                  <motion.div
                    layoutId="active-nav"
                    className="absolute inset-0 bg-[var(--color-matrix-green)]/10 border-l-2 border-[var(--color-matrix-green)] rounded-r-md"
                    initial={false}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-3">
                    <item.icon size={18} className="drop-shadow-sm" />
                    <span className="tracking-wide">{item.label}</span>
                </span>
              </Link>
            );
          })}
        </nav>
        
        <div className="mt-auto px-4 py-4 w-full text-xs text-muted-foreground/60 text-center font-mono">
            Tauri v2 • Rust + Sing-box
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 relative overflow-y-auto">
        <div className="absolute inset-0 max-w-5xl mx-auto p-8">
            <Outlet />
        </div>
      </main>
      <Toaster theme="dark" position="bottom-right" />
    </div>
  );
}
