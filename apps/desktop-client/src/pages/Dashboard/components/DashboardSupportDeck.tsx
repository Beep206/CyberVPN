import { useTranslation } from "react-i18next";

import type { ConnectionStatus } from "../../../shared/api/ipc";
import { TrafficGraph } from "../../../widgets/TrafficGraph";
import { Switch } from "../../../components/ui/switch";
import { Label } from "../../../components/ui/label";
import { Button } from "../../../components/ui/button";
import { StealthWave } from "../../../components/ui/stealth-wave";

type DashboardSupportDeckProps = {
  connectionDebugReport: string;
  isCollectingDebugReport: boolean;
  onCopyConnectionDebugReport: () => void;
  onRefreshConnectionDebugReport: () => void;
  onStealthToggle: (checked: boolean) => void;
  onTunModeChange: (checked: boolean) => void;
  status: ConnectionStatus;
  stealthMode: boolean;
  trafficData: Array<{ time: string; up: number; down: number }>;
  tunMode: boolean;
};

export default function DashboardSupportDeck({
  connectionDebugReport,
  isCollectingDebugReport,
  onCopyConnectionDebugReport,
  onRefreshConnectionDebugReport,
  onStealthToggle,
  onTunModeChange,
  status,
  stealthMode,
  trafficData,
  tunMode,
}: DashboardSupportDeckProps) {
  const { t } = useTranslation();

  return (
    <>
      <div className="grid w-full max-w-[88rem] gap-4 md:grid-cols-2">
        <div className="flex items-center justify-between rounded-[1.75rem] border border-border/60 bg-[color:var(--panel-surface)]/92 px-5 py-5 shadow-[var(--panel-shadow)] backdrop-blur-xl">
          <div className="flex flex-col gap-1 pr-4">
            <Label
              htmlFor="tun-mode"
              className="text-sm font-bold uppercase tracking-wider text-[var(--color-matrix-green)]"
            >
              {t("dashboard.tunModeTitle")}
            </Label>
            <span className="text-xs leading-tight text-muted-foreground">
              {t("dashboard.tunModeDesc")}
            </span>
          </div>
          <Switch
            id="tun-mode"
            checked={tunMode}
            onCheckedChange={(checked) => void onTunModeChange(checked)}
            disabled={status.status !== "disconnected"}
          />
        </div>

        <div
          className={`flex items-center justify-between rounded-[1.75rem] border px-5 py-5 backdrop-blur-xl transition-colors duration-500 ${
            stealthMode
              ? "border-[color:color-mix(in_oklab,var(--color-matrix-green)_34%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_12%,var(--panel-surface))] shadow-[0_0_15px_rgba(20,122,103,0.12)]"
              : "border-border/60 bg-[color:var(--panel-surface)]/92 shadow-[var(--panel-shadow)]"
          }`}
        >
          <div className="flex flex-col gap-1 pr-4">
            <Label
              htmlFor="stealth-mode"
              className={`text-sm font-bold uppercase tracking-wider ${
                stealthMode ? "text-[var(--color-matrix-green)]" : "text-muted-foreground"
              }`}
            >
              {t("dashboard.stealthModeTitle")}
            </Label>
            <span className="text-xs leading-tight text-muted-foreground">
              {t("dashboard.stealthModeDesc")}
            </span>
          </div>
          <Switch
            id="stealth-mode"
            checked={stealthMode}
            onCheckedChange={onStealthToggle}
            disabled={status.status !== "disconnected"}
          />
        </div>
      </div>

      <div className="w-full max-w-[88rem]">
        <TrafficGraph data={trafficData} />
      </div>

      <div className="w-full max-w-[88rem]">
        <StealthWave active={stealthMode} />
      </div>

      {connectionDebugReport ? (
        <div className="w-full max-w-[88rem] rounded-xl border border-red-500/30 bg-red-950/10 p-4 backdrop-blur-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <h2 className="text-sm font-bold uppercase tracking-[0.25em] text-red-300">
                {t("dashboard.debugReportTitle")}
              </h2>
              <p className="text-xs text-red-100/70">{t("dashboard.debugReportDesc")}</p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRefreshConnectionDebugReport}
                disabled={isCollectingDebugReport}
              >
                {isCollectingDebugReport
                  ? t("dashboard.debugReportRefreshing")
                  : t("dashboard.debugReportRefresh")}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={onCopyConnectionDebugReport}
              >
                {t("dashboard.debugReportCopy")}
              </Button>
            </div>
          </div>
          <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-white/10 bg-black/50 p-3 font-mono text-xs leading-5 text-red-50">
            {connectionDebugReport}
          </pre>
        </div>
      ) : null}
    </>
  );
}
