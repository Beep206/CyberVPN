import { useEffect, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { Minus, Moon, Square, SunMedium, X } from "lucide-react";
import { Shield } from "lucide-react";
import { useTranslation } from "react-i18next";
import { LanguageSelector } from "./LanguageSelector";
import { useTheme } from "../app/theme-provider";

export function Titlebar() {
  const [isMaximized, setIsMaximized] = useState(false);
  const { t } = useTranslation();
  const { resolvedTheme, setTheme } = useTheme();

  useEffect(() => {
    const handleResize = async () => {
      try {
        setIsMaximized(await getCurrentWindow().isMaximized());
      } catch (e) {
        // Handle gracefully if not in Tauri
      }
    };
    
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const minimize = () => getCurrentWindow().minimize();
  const toggleMaximize = async () => {
    try {
      const maximized = await getCurrentWindow().isMaximized();
      if (maximized) {
        getCurrentWindow().unmaximize();
        setIsMaximized(false);
      } else {
        getCurrentWindow().maximize();
        setIsMaximized(true);
      }
    } catch (e) {
      // Ignore
    }
  };
  const close = () => getCurrentWindow().close();
  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  };
  const nextThemeLabel =
    resolvedTheme === "dark" ? t("settings.themeLight") : t("settings.themeDark");

  return (
    <div 
      data-tauri-drag-region="true" 
      className="titlebar-shell fixed top-0 left-0 right-0 z-50 flex h-12 select-none items-center justify-between border-b border-border/70 bg-[color:var(--chrome-surface)]/82 px-2 text-muted-foreground shadow-[var(--chrome-shadow)] backdrop-blur-2xl"
    >
        <div className="pointer-events-none relative z-10 px-2">
          <div className="titlebar-brand flex items-center gap-2 rounded-full border border-[color:color-mix(in_oklab,var(--color-matrix-green)_20%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_9%,white)] px-3 py-1.5 text-[var(--color-matrix-green)] shadow-[var(--panel-shadow)] dark:border-[color:color-mix(in_oklab,var(--color-matrix-green)_34%,var(--border))] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_14%,black)] dark:shadow-[0_12px_28px_rgba(56,240,160,0.12)]">
            <span className="relative inline-flex h-2.5 w-2.5 items-center justify-center">
              <span className="absolute inset-0 rounded-full bg-[var(--color-matrix-green)] opacity-35 blur-[1px] animate-ping motion-reduce:animate-none" />
              <span className="relative h-2 w-2 rounded-full bg-[var(--color-matrix-green)] shadow-[0_0_10px_var(--color-matrix-green)]" />
            </span>
            <Shield size={14} className="drop-shadow-[0_0_8px_var(--color-matrix-green)] opacity-80" />
            <span className="text-[10px] font-mono font-semibold tracking-[0.28em] opacity-90">CYBERVPN</span>
          </div>
        </div>
      <div data-tauri-drag-region="false" className="titlebar-controls relative z-10 flex h-full pointer-events-auto items-center gap-1 rounded-full border border-border/65 bg-[color:var(--chrome-elevated)]/82 px-1 shadow-[var(--panel-shadow)]">
        <button
          type="button"
          className="inline-flex h-9 w-10 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-accent/70 hover:text-foreground"
          onClick={toggleTheme}
          title={t("titlebar.toggleTheme", { theme: nextThemeLabel })}
          aria-label={t("titlebar.toggleTheme", { theme: nextThemeLabel })}
        >
          {resolvedTheme === "dark" ? <SunMedium size={15} /> : <Moon size={15} />}
        </button>
        <LanguageSelector />
        <div className="mx-1 h-4 w-px bg-border/80"></div>
        <div 
          className="inline-flex h-9 w-10 cursor-default items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-accent/70 hover:text-foreground"
          onClick={minimize}
          title={t("titlebar.minimize")}
          aria-label={t("titlebar.minimize")}
        >
          <Minus size={14} />
        </div>
        <div 
          className="inline-flex h-9 w-10 cursor-default items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-accent/70 hover:text-foreground"
          onClick={toggleMaximize}
          title={isMaximized ? t("titlebar.restore") : t("titlebar.maximize")}
          aria-label={isMaximized ? t("titlebar.restore") : t("titlebar.maximize")}
        >
          {isMaximized ? <Square size={12} className="opacity-80" /> : <Square size={12} />}
        </div>
        <div 
          className="inline-flex h-9 w-10 cursor-default items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-destructive/15 hover:text-destructive"
          onClick={close}
          title={t("titlebar.hideToTray")}
          aria-label={t("titlebar.hideToTray")}
        >
          <X size={14} />
        </div>
      </div>
    </div>
  );
}
