import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { Activity, Shield, Settings, Route, Rss, Split, WifiHigh, Brain, Terminal, Smartphone } from "lucide-react";
import { Toaster } from "../components/ui/sonner";
import { toast } from "sonner";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { listen } from "@tauri-apps/api/event";
import { applyRoutingFix } from "../shared/api/ipc";
import { Titlebar } from "./Titlebar";
import { useTranslation } from "react-i18next";

export function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();

  useEffect(() => {
    if (!localStorage.getItem("onboarding_complete")) {
      navigate("/onboarding", { replace: true });
    }
  }, [navigate]);

  useEffect(() => {
    async function checkForUpdates() {
      try {
        const update = await check();
        if (update) {
          toast.info(t('layout.updateAvailable', { version: update.version }), {
            description: t('layout.updateDesc'),
            action: {
              label: t('layout.updateAction'),
              onClick: async () => {
                toast.loading(t('layout.updateLoading'));
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

    // AI Routing Assistant Listener
    const unlistenRouting = listen<{ domain: string, reason: string }>("routing-suggestion", (event) => {
      toast(t('layout.trafficBlockDetected'), {
        description: t('layout.trafficBlockDesc', { reason: event.payload.reason, domain: event.payload.domain }),
        duration: 20000,
        icon: <Shield className="text-[var(--color-neon-pink)] animate-pulse" />,
        action: {
          label: t('layout.magicFix'),
          onClick: async () => {
             try {
                toast.loading(t('layout.magicFixLoading'), { id: "magic-fix" });
                await applyRoutingFix(event.payload.domain);
                toast.success(t('layout.magicFixSuccess'), { id: "magic-fix" });
             } catch (e: any) {
                toast.error(t('layout.fixFailed', { error: e }), { id: "magic-fix" });
             }
          }
        },
        cancel: {
          label: t('layout.ignore'),
          onClick: () => {}
        }
      });
    });

    return () => {
       clearTimeout(timer);
       unlistenRouting.then(f => f());
    };
  }, []);

  const navItems = [
    { path: "/", label: t('sidebar.dashboard'), icon: Activity },
    { path: "/analytics", label: t('sidebar.analytics'), icon: Activity },
    { path: "/remote", label: t('sidebar.remote'), icon: Smartphone },
    { path: "/stealth-lab", label: t('sidebar.stealthLab'), icon: Terminal },
    { path: "/automation", label: t('sidebar.automation'), icon: Brain },
    { path: "/security", label: t('sidebar.security'), icon: Shield },
    { path: "/privacy-shield", label: t('sidebar.privacyShield'), icon: Shield },
    { path: "/profiles", label: t('sidebar.profiles'), icon: Shield },
    { path: "/routing", label: t('sidebar.routing'), icon: Route },
    { path: "/hotspot", label: t('sidebar.hotspot'), icon: WifiHigh },
    { path: "/split-tunneling", label: t('sidebar.splitTunneling'), icon: Split },
    { path: "/subscriptions", label: t('sidebar.subscriptions'), icon: Rss },
    { path: "/account", label: t('sidebar.account'), icon: Shield },
    { path: "/settings", label: t('sidebar.settings'), icon: Settings },
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
                  color: isActive ? (item.path === '/stealth-lab' ? "#ff00ff" : "var(--color-matrix-green)") : "var(--muted-foreground)"
                }}
              >
                {isActive && (
                  <motion.div
                    layoutId="active-nav"
                    className={`absolute inset-0 border-l-2 rounded-r-md ${item.path === '/stealth-lab' ? 'bg-[#ff00ff]/10 border-[#ff00ff]' : 'bg-[var(--color-matrix-green)]/10 border-[var(--color-matrix-green)]'}`}
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
            {t('layout.versionSlogan')}
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
