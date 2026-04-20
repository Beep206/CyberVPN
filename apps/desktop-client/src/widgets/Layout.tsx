import { Outlet, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Suspense, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  Shield,
  Settings,
  Route,
  Rss,
  Split,
  WifiHigh,
  Brain,
  Terminal,
  Smartphone,
  Bug,
} from "lucide-react";
import { Toaster } from "../components/ui/sonner";
import { toast } from "sonner";
import { listen } from "@tauri-apps/api/event";
import { applyRoutingFix } from "../shared/api/ipc";
import { Titlebar } from "./Titlebar";
import { PageSkeleton } from "./PageSkeleton";
import { RouteTransition } from "./RouteTransition";
import { useTranslation } from "react-i18next";
import { desktopMotionEase, useDesktopMotionBudget } from "../shared/lib/motion";

export function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { prefersReducedMotion, durations } = useDesktopMotionBudget();

  useEffect(() => {
    if (!localStorage.getItem("onboarding_complete")) {
      navigate("/onboarding", { replace: true });
    }
  }, [navigate]);

  useEffect(() => {
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
    { path: "/logs", label: t('sidebar.logs'), icon: Bug },
    { path: "/account", label: t('sidebar.account'), icon: Shield },
    { path: "/settings", label: t('sidebar.settings'), icon: Settings },
  ];

  const getActiveChrome = (path: string) =>
    path === "/stealth-lab"
      ? {
          shell:
            "border-[color:color-mix(in_oklab,var(--color-neon-pink)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] shadow-[0_12px_28px_rgba(159,99,125,0.12)] dark:border-[color:color-mix(in_oklab,var(--color-neon-pink)_34%,var(--border))] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_18%,black)] dark:shadow-[0_16px_34px_rgba(255,104,220,0.14)]",
          text: "text-[var(--color-neon-pink)]",
          rail: "bg-[linear-gradient(180deg,var(--color-neon-pink),color-mix(in_oklab,var(--color-neon-pink)_18%,transparent))]",
          icon: "border-[color:color-mix(in_oklab,var(--color-neon-pink)_24%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_12%,white)] text-[var(--color-neon-pink)] shadow-[0_10px_20px_rgba(159,99,125,0.12)] dark:border-[color:color-mix(in_oklab,var(--color-neon-pink)_38%,var(--border))] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)] dark:shadow-[0_10px_24px_rgba(255,104,220,0.18)]",
        }
      : {
          shell:
            "border-[color:color-mix(in_oklab,var(--color-matrix-green)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_9%,white)] shadow-[0_12px_28px_rgba(29,111,99,0.10)] dark:border-[color:color-mix(in_oklab,var(--color-matrix-green)_34%,var(--border))] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_18%,black)] dark:shadow-[0_16px_34px_rgba(56,240,160,0.13)]",
          text: "text-[var(--color-matrix-green)]",
          rail: "bg-[linear-gradient(180deg,var(--color-matrix-green),color-mix(in_oklab,var(--color-neon-cyan)_28%,transparent))]",
          icon: "border-[color:color-mix(in_oklab,var(--color-matrix-green)_24%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] text-[var(--color-matrix-green)] shadow-[0_10px_20px_rgba(29,111,99,0.10)] dark:border-[color:color-mix(in_oklab,var(--color-matrix-green)_40%,var(--border))] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_16%,black)] dark:shadow-[0_10px_24px_rgba(56,240,160,0.18)]",
        };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans pt-10">
      <Titlebar />
      {/* Sidebar */}
      <aside className="sidebar-shell relative z-10 flex w-72 shrink-0 flex-col items-center overflow-hidden border-r border-border/60 bg-[color:var(--chrome-elevated)]/88 py-8 shadow-[var(--chrome-shadow)] backdrop-blur-2xl">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="sidebar-ambient-orb sidebar-ambient-orb--top" />
          <div className="sidebar-ambient-orb sidebar-ambient-orb--bottom" />
          <div className="sidebar-grid-layer" />
          <div className="sidebar-scanline-layer" />
        </div>

        <div className="relative z-10 mb-12 flex items-center gap-3 rounded-full border border-[color:color-mix(in_oklab,var(--color-matrix-green)_18%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_8%,white)] px-5 py-3 font-bold text-xl tracking-[0.22em] text-[var(--color-matrix-green)] shadow-[var(--panel-shadow)] dark:border-[color:color-mix(in_oklab,var(--color-matrix-green)_34%,var(--border))] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_14%,black)] dark:shadow-[0_16px_34px_rgba(56,240,160,0.12)]">
           <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-matrix-green)] shadow-[0_0_12px_var(--color-matrix-green)]" />
           <Shield size={22} />
           CYBERVPN
        </div>

        <nav className="relative z-10 w-full flex-1 space-y-2.5 px-4">
          {navItems.map((item, index) => {
            const activeChrome = getActiveChrome(item.path);

            return (
              <NavLink
                to={item.path}
                key={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  `cyber-nav-item group relative flex w-full items-center gap-3 overflow-hidden rounded-2xl border px-3 py-3 text-sm font-medium transition-[transform,color,border-color,box-shadow] duration-200 hover:-translate-y-px hover:border-border/75 hover:bg-[color:var(--panel-subtle)]/72 hover:text-foreground hover:shadow-[0_16px_28px_rgba(15,23,42,0.10)] ${
                    isActive
                      ? `border-transparent ${activeChrome.text}`
                      : "border-transparent text-muted-foreground"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <>
                        <motion.span
                          layoutId="sidebar-active-shell"
                          transition={{ duration: durations.accent, ease: desktopMotionEase }}
                          className={`pointer-events-none absolute inset-0 rounded-2xl ${activeChrome.shell}`}
                        />
                        <motion.span
                          layoutId="sidebar-active-rail"
                          transition={{ duration: prefersReducedMotion ? 0.01 : durations.accent + 0.03, ease: desktopMotionEase }}
                          className={`pointer-events-none absolute inset-y-2 left-2 w-1 rounded-full ${activeChrome.rail}`}
                        />
                      </>
                    )}

                    <span
                      className={`relative z-10 inline-flex h-9 w-9 items-center justify-center rounded-2xl border transition-all duration-200 ${
                        isActive
                          ? activeChrome.icon
                          : "border-border/55 bg-[color:var(--panel-surface)]/72 text-muted-foreground group-hover:border-border/80 group-hover:bg-[color:var(--field-surface-hover)] group-hover:text-foreground"
                      }`}
                    >
                      <item.icon size={17} className="drop-shadow-sm transition-transform duration-200 group-hover:translate-x-[1px] group-hover:-translate-y-[1px]" />
                    </span>

                    <span className="relative z-10 flex min-w-0 flex-1 items-center justify-between gap-3">
                      <span className="cyber-glitch-label truncate tracking-[0.04em]" data-text={item.label}>
                        {item.label}
                      </span>
                      <span
                        className={`text-[10px] font-mono uppercase tracking-[0.24em] transition-opacity duration-200 ${
                          isActive ? "opacity-55" : "opacity-0 group-hover:opacity-35"
                        }`}
                      >
                        {(index + 1).toString().padStart(2, "0")}
                      </span>
                    </span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
        
        <div className="relative z-10 mt-auto w-full px-4 py-4 text-center font-mono text-xs text-muted-foreground/60">
            {t('layout.versionSlogan')}
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto min-h-full max-w-5xl p-8">
          <Suspense fallback={<PageSkeleton />}>
            <RouteTransition routeKey={location.pathname}>
              <Outlet />
            </RouteTransition>
          </Suspense>
        </div>
      </main>
      <Toaster position="bottom-right" />
    </div>
  );
}
