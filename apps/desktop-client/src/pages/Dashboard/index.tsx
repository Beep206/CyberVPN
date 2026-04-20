import { Suspense, lazy, startTransition, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, Reorder, useDragControls } from "framer-motion";
import {
  Activity,
  ArrowRight,
  Clock3,
  Fingerprint,
  Gauge,
  Globe2,
  GripVertical,
  Layers3,
  LoaderCircle,
  Map as MapIcon,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  Star,
  Waypoints,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import { ConnectButton } from "../../widgets/ConnectButton";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { CountryFlag } from "../../shared/ui/country-flag";
import {
  DesktopDiagnosticsSnapshot,
  ProfileGroup,
  ProxyNode,
  Subscription,
  getDesktopDiagnosticsSnapshot,
  getGroups,
  getProfiles,
  getStealthMode,
  getSubscriptions,
  listenProfilesUpdated,
  listenTrafficUpdate,
  saveStealthMode,
  testAllLatencies,
} from "../../shared/api/ipc";
import { useConnection } from "../../shared/model/use-connection";
import { desktopMotionEase, useDesktopMotionBudget } from "../../shared/lib/motion";
import { useTranslation } from "react-i18next";
import {
  buildDashboardProfileCollections,
  buildDashboardRegionClusters,
  explainDashboardSmartRoute,
  findBestLatencyProxy,
  findBestSmartRoute,
  getDashboardLatencyTier,
  hasMeasuredLatency,
  inferDashboardRegionCountryCode,
  inferDashboardRegionLabel,
  rankDashboardSmartProxies,
  resolveDashboardSelection,
  sortPinnedFavoriteProxies,
  sortDashboardVisibleProxies,
} from "./lib/profile-catalog";

const DashboardSupportDeck = lazy(() => import("./components/DashboardSupportDeck"));

function redactSensitiveText(value: string) {
  return value
    .replace(/(Bearer\s+)[A-Za-z0-9._~-]+/gi, "$1[REDACTED]")
    .replace(
      /((?:access|refresh|session|api|auth|proxy)?_?token["']?\s*[:=]\s*["']?)[^"',\s}]+/gi,
      "$1[REDACTED]"
    )
    .replace(
      /((?:authorization|cookie|set-cookie|password|secret)["']?\s*[:=]\s*["']?)[^"',\s}]+/gi,
      "$1[REDACTED]"
    )
    .replace(
      /([?&](?:access_token|refresh_token|token|sig|signature)=)[^&\s]+/gi,
      "$1[REDACTED]"
    )
    .replace(/([a-z]+:\/\/[^/\s:@]+:)[^@\s/]+@/gi, "$1[REDACTED]@");
}

function sanitizeDiagnosticPayload(value: unknown): unknown {
  if (typeof value === "string") {
    return redactSensitiveText(value);
  }

  if (Array.isArray(value)) {
    return value.map(sanitizeDiagnosticPayload);
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => {
        if (/token|secret|authorization|cookie|password/i.test(key)) {
          return [key, "[REDACTED]"];
        }

        return [key, sanitizeDiagnosticPayload(nestedValue)];
      })
    );
  }

  return value;
}

function formatUnknownError(error: unknown) {
  if (typeof error === "string") {
    return error;
  }

  if (error instanceof Error) {
    return error.message;
  }

  try {
    return JSON.stringify(error);
  } catch {
    return String(error);
  }
}

function formatTrafficSpeed(bytes: number) {
  if (bytes === 0) return "0 B/s";
  const k = 1024;
  const sizes = ["B/s", "KB/s", "MB/s", "GB/s"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function formatCollectionTimestamp(value?: number | null) {
  if (!value) {
    return null;
  }

  return new Date(value * 1000).toLocaleString();
}

function formatSessionTimestamp(value?: number | null) {
  if (!value) {
    return null;
  }

  return new Date(value).toLocaleTimeString();
}

type LatencyBadge = {
  labelKey:
    | "dashboard.latencyNoProbe"
    | "dashboard.latencyExcellent"
    | "dashboard.latencyFast"
    | "dashboard.latencyStable"
    | "dashboard.latencyLongRoute";
  detail: string;
  tone: string;
};

function getLatencyBadge(ping?: number | null): LatencyBadge {
  if (!hasMeasuredLatency(ping)) {
    return {
      labelKey: "dashboard.latencyNoProbe",
      detail: "—",
      tone:
        "border-border/70 bg-[color:var(--panel-subtle)]/80 text-muted-foreground",
    };
  }

  if (ping <= 60) {
    return {
      labelKey: "dashboard.latencyExcellent",
      detail: `${ping} ms`,
      tone:
        "border-[color:color-mix(in_oklab,var(--color-matrix-green)_24%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_16%,black)]",
    };
  }

  if (ping <= 120) {
    return {
      labelKey: "dashboard.latencyFast",
      detail: `${ping} ms`,
      tone:
        "border-[color:color-mix(in_oklab,var(--color-neon-cyan)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]",
    };
  }

  if (ping <= 220) {
    return {
      labelKey: "dashboard.latencyStable",
      detail: `${ping} ms`,
      tone:
        "border-[color:color-mix(in_oklab,var(--color-neon-pink)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]",
    };
  }

  return {
    labelKey: "dashboard.latencyLongRoute",
    detail: `${ping} ms`,
    tone:
      "border-amber-400/30 bg-amber-500/10 text-amber-200 dark:bg-amber-500/14",
  };
}

function areArraysEqual(a: readonly string[], b: readonly string[]) {
  if (a.length !== b.length) {
    return false;
  }

  return a.every((value, index) => value === b[index]);
}

function haveSameMembers(a: readonly string[], b: readonly string[]) {
  if (a.length !== b.length) {
    return false;
  }

  return b.every((value) => a.includes(value));
}

function getLatencyHeatTone(ping?: number | null) {
  switch (getDashboardLatencyTier(ping)) {
    case "excellent":
      return "border-[color:color-mix(in_oklab,var(--color-matrix-green)_32%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_14%,var(--panel-surface))] text-[var(--color-matrix-green)]";
    case "fast":
      return "border-[color:color-mix(in_oklab,var(--color-neon-cyan)_30%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_14%,var(--panel-surface))] text-[var(--color-neon-cyan)]";
    case "stable":
      return "border-[color:color-mix(in_oklab,var(--color-neon-pink)_28%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_12%,var(--panel-surface))] text-[var(--color-neon-pink)]";
    case "long":
      return "border-amber-400/30 bg-amber-500/12 text-amber-200";
    default:
      return "border-border/70 bg-[color:var(--panel-subtle)]/72 text-muted-foreground";
  }
}

function formatDashboardScore(score: number) {
  return score > 0 ? `+${score}` : `${score}`;
}

function normalizeDashboardToken(value?: string | null) {
  if (!value) {
    return null;
  }

  return value.trim().replace(/[_-]+/g, " ").toUpperCase();
}

function formatRouteTransportSignature(proxy: ProxyNode) {
  const preferred = [
    normalizeDashboardToken(proxy.network),
    proxy.mux ? `MUX ${normalizeDashboardToken(proxy.mux)}` : null,
    proxy.udpRelayMode ? `UDP ${normalizeDashboardToken(proxy.udpRelayMode)}` : null,
    proxy.congestionControl ? `CC ${normalizeDashboardToken(proxy.congestionControl)}` : null,
    normalizeDashboardToken(proxy.obfs),
  ].filter((value): value is string => Boolean(value));

  return preferred[0] ?? null;
}

function formatRouteSecurityEnvelope(proxy: ProxyNode) {
  const parts = [
    normalizeDashboardToken(proxy.tls),
    normalizeDashboardToken(proxy.security),
    proxy.fingerprint ? `FP ${normalizeDashboardToken(proxy.fingerprint)}` : null,
    proxy.flow ? `FLOW ${normalizeDashboardToken(proxy.flow)}` : null,
    proxy.pqcEnabled ? "PQC" : null,
  ].filter((value): value is string => Boolean(value));

  return parts.slice(0, 3).join(" • ") || null;
}

function formatRouteCapacityLabel(proxy: ProxyNode) {
  const hasDown = typeof proxy.downMbps === "number" && proxy.downMbps > 0;
  const hasUp = typeof proxy.upMbps === "number" && proxy.upMbps > 0;

  if (hasDown || hasUp) {
    const down = hasDown ? `${proxy.downMbps}↓` : "—↓";
    const up = hasUp ? `${proxy.upMbps}↑` : "—↑";
    return `${down} / ${up} Mbps`;
  }

  if (typeof proxy.mtu === "number" && proxy.mtu > 0) {
    return `MTU ${proxy.mtu}`;
  }

  if (proxy.congestionControl) {
    return `CC ${normalizeDashboardToken(proxy.congestionControl)}`;
  }

  return null;
}

function formatRouteEndpointLabel(proxy: ProxyNode) {
  if (proxy.sni) {
    return `SNI ${proxy.sni}`;
  }

  if (proxy.alpn?.length) {
    return `ALPN ${proxy.alpn.join("/")}`;
  }

  if (proxy.plugin) {
    return normalizeDashboardToken(proxy.plugin);
  }

  return null;
}

function getRouteRegionMeta(proxy: ProxyNode) {
  const label = inferDashboardRegionLabel(proxy);
  const countryCode = inferDashboardRegionCountryCode(proxy);

  return {
    countryCode,
    label,
  };
}

function formatLatencyLeadLabel(
  selectedPing?: number | null,
  referencePing?: number | null
) {
  if (!hasMeasuredLatency(selectedPing) || !hasMeasuredLatency(referencePing)) {
    return null;
  }

  const delta = selectedPing - referencePing;

  if (Math.abs(delta) < 4) {
    return "0 ms";
  }

  return delta > 0 ? `+${delta} ms` : `${delta} ms`;
}

function clampDashboardMetric(value: number, min = 0, max = 100) {
  return Math.min(max, Math.max(min, value));
}

type DashboardTranslate = (key: string, options?: Record<string, unknown>) => string;

type SmartSignalChipProps = {
  signal: ReturnType<typeof explainDashboardSmartRoute>["signals"][number];
  proxy: ProxyNode;
  latencyBadge: LatencyBadge;
  translate: DashboardTranslate;
};

function SmartSignalChip({
  signal,
  proxy,
  latencyBadge,
  translate,
}: SmartSignalChipProps) {
  const visual = (() => {
    switch (signal.kind) {
      case "latency":
        return {
          label: translate("dashboard.smartSignalLatency"),
          detail: latencyBadge.detail,
          tone: latencyBadge.tone,
        };
      case "favorite":
        return {
          label: translate("dashboard.smartSignalPinned"),
          detail: formatDashboardScore(signal.weight),
          tone:
            "border-[color:color-mix(in_oklab,var(--color-neon-pink)_26%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]",
        };
      case "stable":
        return {
          label: translate("dashboard.smartSignalStable"),
          detail: formatDashboardScore(signal.weight),
          tone:
            "border-[color:color-mix(in_oklab,var(--color-matrix-green)_26%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_16%,black)]",
        };
      case "active":
        return {
          label: translate("dashboard.smartSignalLive"),
          detail: formatDashboardScore(signal.weight),
          tone:
            "border-[color:color-mix(in_oklab,var(--color-neon-cyan)_26%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]",
        };
      case "relay":
        return {
          label: translate("dashboard.smartSignalRelay"),
          detail: formatDashboardScore(signal.weight),
          tone: "border-amber-400/30 bg-amber-500/12 text-amber-200",
        };
      case "fallback":
      default:
        return {
          label: translate("dashboard.smartSignalFallback"),
          detail: proxy.server,
          tone: "border-border/70 bg-[color:var(--panel-subtle)]/72 text-muted-foreground",
        };
    }
  })();

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${visual.tone}`}
    >
      <span>{visual.label}</span>
      <span className="font-mono opacity-80">{visual.detail}</span>
    </span>
  );
}

function DashboardSupportDeckFallback() {
  return (
    <div className="grid w-full max-w-[88rem] gap-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-28 rounded-[1.75rem] border border-border/60 bg-[color:var(--panel-surface)]/72 shadow-[var(--panel-shadow)]" />
        <div className="h-28 rounded-[1.75rem] border border-border/60 bg-[color:var(--panel-surface)]/72 shadow-[var(--panel-shadow)]" />
      </div>
      <div className="h-64 rounded-[1.75rem] border border-border/60 bg-[color:var(--panel-surface)]/72 shadow-[var(--panel-shadow)]" />
      <div className="h-32 rounded-[1.75rem] border border-border/60 bg-[color:var(--panel-surface)]/72 shadow-[var(--panel-shadow)]" />
    </div>
  );
}

type PinnedRouteCardProps = {
  proxy: ProxyNode;
  latencyBadge: LatencyBadge;
  isSelected: boolean;
  isActive: boolean;
  onStage: () => void;
  onToggleFavorite: () => void;
  translate: DashboardTranslate;
};

function PinnedRouteCard({
  proxy,
  latencyBadge,
  isSelected,
  isActive,
  onStage,
  onToggleFavorite,
  translate,
}: PinnedRouteCardProps) {
  const dragControls = useDragControls();
  const regionMeta = getRouteRegionMeta(proxy);
  const transportLabel = formatRouteTransportSignature(proxy);

  return (
    <Reorder.Item
      value={proxy.id}
      dragListener={false}
      dragControls={dragControls}
      layout
      whileDrag={{
        scale: 1.015,
        rotate: 0.35,
      }}
      className={`group relative overflow-hidden rounded-[1.4rem] border shadow-[var(--panel-shadow)] transition-[transform,border-color,background-color,box-shadow] duration-200 ${
        isSelected
          ? "border-[color:color-mix(in_oklab,var(--color-neon-pink)_28%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,var(--panel-surface))]"
          : "border-border/70 bg-[color:var(--panel-surface)]/88 hover:border-border hover:bg-[color:var(--panel-subtle)]/78"
      }`}
    >
      {isSelected ? (
        <motion.span
          layoutId="dashboard-pinned-route-active"
          transition={{ duration: 0.22, ease: desktopMotionEase }}
          className="pointer-events-none absolute inset-0 rounded-[1.4rem] border border-[color:color-mix(in_oklab,var(--color-neon-pink)_22%,transparent)] bg-[linear-gradient(135deg,color-mix(in_oklab,var(--color-neon-pink)_14%,transparent),transparent_72%)]"
        />
      ) : null}

      <div className="relative z-10 flex items-stretch gap-3 px-4 py-3">
        <button
          type="button"
          onClick={onStage}
          className="flex min-w-0 flex-1 items-start justify-between gap-4 text-left"
        >
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="truncate text-sm font-semibold text-foreground">{proxy.name}</span>
              {isActive ? (
                <span className="rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-cyan)_28%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]">
                  LIVE
                </span>
              ) : null}
            </div>
            <div className="mt-1 truncate text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              {proxy.server}:{proxy.port}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${latencyBadge.tone}`}
              >
                {translate(latencyBadge.labelKey)}
              </span>
              <span className="rounded-full border border-border/70 bg-[color:var(--panel-subtle)]/72 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                {proxy.protocol.toUpperCase()}
              </span>
              <span className="inline-flex max-w-full items-center gap-2 rounded-full border border-border/70 bg-[color:var(--panel-subtle)]/72 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                <CountryFlag
                  code={regionMeta.countryCode}
                  className="h-3 w-[1.125rem] rounded-[0.15rem] border border-border/65 shadow-[var(--panel-shadow)]"
                  fallbackClassName="h-3 w-[1.125rem]"
                />
                <span className="truncate">{regionMeta.label}</span>
              </span>
              {transportLabel ? (
                <span className="rounded-full border border-border/70 bg-[color:var(--panel-subtle)]/72 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  {transportLabel}
                </span>
              ) : null}
            </div>
          </div>

          <div className="flex shrink-0 flex-col items-end justify-between gap-3">
            <span className="font-mono text-xs tracking-[0.16em] text-foreground">
              {latencyBadge.detail}
            </span>
            <ArrowRight
              size={16}
              className={`transition-transform duration-200 ${
                isSelected
                  ? "translate-x-0.5 text-[var(--color-neon-pink)]"
                  : "text-muted-foreground group-hover:translate-x-0.5"
              }`}
            />
          </div>
        </button>

        <div className="flex shrink-0 flex-col gap-2">
          <motion.button
            type="button"
            onPointerDown={(event) => dragControls.start(event)}
            aria-label={translate("dashboard.pinnedRoutesDragHint")}
            whileHover={{ scale: 1.04, rotate: 3 }}
            whileTap={{ scale: 0.94 }}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-[color:var(--panel-subtle)]/72 text-muted-foreground transition-colors hover:text-foreground"
          >
            <GripVertical size={16} />
          </motion.button>
          <motion.button
            type="button"
            onClick={onToggleFavorite}
            aria-label={translate("dashboard.favoriteRemoveAria", { route: proxy.name })}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.94 }}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-pink)_28%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] text-[var(--color-neon-pink)] transition-colors dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]"
          >
            <Star size={16} className="fill-current" />
          </motion.button>
        </div>
      </div>
    </Reorder.Item>
  );
}

function buildConnectionDebugReport(
  snapshot: DesktopDiagnosticsSnapshot,
  errorText: string,
  attemptedProfileId: string | null,
  tunMode: boolean,
  systemProxy: boolean
) {
  const recentEntries = snapshot.recent_entries.slice(0, 15);
  const coreTail = snapshot.core_log_tail.slice(-40);
  const helixTail = snapshot.helix_log_tail.slice(-40);

  const eventLines = recentEntries.length
    ? recentEntries
        .map((entry) => {
          const sanitizedMessage = redactSensitiveText(entry.message);
          const sanitizedPayload = sanitizeDiagnosticPayload(entry.payload);
          const payload =
            sanitizedPayload &&
            typeof sanitizedPayload === "object" &&
            Object.keys(sanitizedPayload).length > 0
              ? `\n  payload: ${JSON.stringify(sanitizedPayload)}`
              : "";
          return `[${entry.timestamp}] [${entry.level}] [${entry.source}] ${sanitizedMessage}${payload}`;
        })
        .join("\n")
    : "<no recent diagnostics entries>";

  return [
    "=== CYBERVPN CONNECTION DEBUG REPORT BEGIN ===",
    `captured_at: ${new Date().toISOString()}`,
    `app_version: ${snapshot.app_version}`,
    `platform: ${snapshot.platform}`,
    `attempted_profile_id: ${attemptedProfileId ?? "unknown"}`,
    `tun_mode: ${String(tunMode)}`,
    `system_proxy: ${String(systemProxy)}`,
    `ui_error: ${redactSensitiveText(errorText)}`,
    `connection_status: ${snapshot.connection_status.status}`,
    `connection_message: ${redactSensitiveText(snapshot.connection_status.message ?? "<none>")}`,
    `active_core: ${redactSensitiveText(snapshot.active_core)}`,
    `active_profile_id: ${snapshot.active_profile_id ?? "<none>"}`,
    `diagnostics_dir: ${snapshot.diagnostics_dir}`,
    `profile_count: ${snapshot.profile_count}`,
    `subscription_count: ${snapshot.subscription_count}`,
    "",
    "--- recent_diagnostics ---",
    eventLines,
    "",
    "--- core_log_tail ---",
    coreTail.length ? coreTail.map(redactSensitiveText).join("\n") : "<empty>",
    "",
    "--- helix_log_tail ---",
    helixTail.length ? helixTail.map(redactSensitiveText).join("\n") : "<empty>",
    "=== CYBERVPN CONNECTION DEBUG REPORT END ===",
  ].join("\n");
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { prefersReducedMotion, durations, offsets } = useDesktopMotionBudget();
  const { t } = useTranslation();
  const { connect, disconnect, options, status, updateOptions } = useConnection();

  const [stealthMode, setStealthMode] = useState(false);
  const [trafficData, setTrafficData] = useState<Array<{ time: string; up: number; down: number }>>(
    []
  );
  const [connectionDebugReport, setConnectionDebugReport] = useState("");
  const [isCollectingDebugReport, setIsCollectingDebugReport] = useState(false);
  const [profiles, setProfiles] = useState<ProxyNode[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [groups, setGroups] = useState<ProfileGroup[]>([]);
  const [isCatalogLoading, setIsCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [selectedCollectionKey, setSelectedCollectionKey] = useState<string | null>(null);
  const [selectedProxyId, setSelectedProxyId] = useState<string | null>(null);
  const [proxyQuery, setProxyQuery] = useState("");
  const [isLatencyRefreshing, setIsLatencyRefreshing] = useState(false);
  const [latencyRefreshError, setLatencyRefreshError] = useState<string | null>(null);
  const [lastLatencyRefreshAt, setLastLatencyRefreshAt] = useState<number | null>(null);
  const [favoriteLaunchpadOrder, setFavoriteLaunchpadOrder] = useState<string[]>([]);
  const latencyRefreshInFlightRef = useRef(false);

  const deferredProxyQuery = useDeferredValue(proxyQuery.trim().toLowerCase());

  const loadProfileCatalog = async () => {
    setIsCatalogLoading(true);
    setCatalogError(null);

    try {
      const [profilesData, subscriptionsData, groupsData] = await Promise.all([
        getProfiles(),
        getSubscriptions(),
        getGroups(),
      ]);

      startTransition(() => {
        setProfiles(profilesData);
        setSubscriptions(subscriptionsData);
        setGroups(groupsData);
      });
    } catch (error) {
      console.error("Failed to load dashboard profile catalog", error);
      setCatalogError(formatUnknownError(error));
    } finally {
      setIsCatalogLoading(false);
    }
  };

  const profileCollections = useMemo(
    () => buildDashboardProfileCollections(profiles, subscriptions, groups),
    [profiles, subscriptions, groups]
  );

  const proxyLookup = useMemo(
    () => new Map(profiles.map((profile) => [profile.id, profile])),
    [profiles]
  );

  useEffect(() => {
    const nextSelection = resolveDashboardSelection(profileCollections, {
      selectedCollectionKey,
      selectedProxyId,
      persistedProxyId: options.profileId ?? null,
    });

    if (nextSelection.collectionKey !== selectedCollectionKey) {
      setSelectedCollectionKey(nextSelection.collectionKey);
    }

    if (nextSelection.proxyId !== selectedProxyId) {
      setSelectedProxyId(nextSelection.proxyId);
    }
  }, [options.profileId, profileCollections, selectedCollectionKey, selectedProxyId]);

  const selectedCollection =
    profileCollections.find((collection) => collection.key === selectedCollectionKey) ?? null;
  const selectedProxy = selectedProxyId ? proxyLookup.get(selectedProxyId) ?? null : null;
  const selectedCollectionPosition = selectedCollection?.proxies.findIndex(
    (proxy) => proxy.id === selectedProxy?.id
  );
  const selectedRelayProxy =
    selectedProxy?.nextHopId != null ? proxyLookup.get(selectedProxy.nextHopId) ?? null : null;
  const activeProxy = status.activeId ? proxyLookup.get(status.activeId) ?? null : null;
  const favoriteProfileIds = options.favoriteProfileIds ?? [];
  const favoriteProfileIdSet = useMemo(
    () => new Set(favoriteProfileIds),
    [favoriteProfileIds]
  );
  const favoriteProxies = useMemo(
    () =>
      sortPinnedFavoriteProxies(
        profiles.filter((profile) => favoriteProfileIdSet.has(profile.id)),
        favoriteProfileIds
      ),
    [favoriteProfileIdSet, favoriteProfileIds, profiles]
  );
  const selectedCollectionFavoriteCount = useMemo(
    () =>
      selectedCollection?.proxies.filter((proxy) => favoriteProfileIdSet.has(proxy.id)).length ?? 0,
    [favoriteProfileIdSet, selectedCollection]
  );
  const lastStableProxy = options.lastStableProfileId
    ? proxyLookup.get(options.lastStableProfileId) ?? null
    : null;
  const smartRoutePool = selectedCollection?.proxies.length ? selectedCollection.proxies : profiles;
  const smartRouteOptions = useMemo(
    () => ({
      favoriteProfileIds: favoriteProfileIdSet,
      lastStableProfileId: options.lastStableProfileId ?? null,
      activeProfileId: activeProxy?.id ?? null,
    }),
    [activeProxy?.id, favoriteProfileIdSet, options.lastStableProfileId]
  );
  const rankedSmartRoutes = useMemo(
    () => rankDashboardSmartProxies(smartRoutePool, smartRouteOptions),
    [smartRouteOptions, smartRoutePool]
  );
  const bestAvailableProxy = useMemo(() => {
    return findBestSmartRoute(smartRoutePool, smartRouteOptions) ?? findBestLatencyProxy(profiles);
  }, [profiles, smartRouteOptions, smartRoutePool]);
  const bestAvailableExplanation = useMemo(
    () => (bestAvailableProxy ? explainDashboardSmartRoute(bestAvailableProxy, smartRouteOptions) : null),
    [bestAvailableProxy, smartRouteOptions]
  );
  const bestInCollectionProxy = useMemo(
    () => (selectedCollection ? findBestLatencyProxy(selectedCollection.proxies) : null),
    [selectedCollection]
  );
  const selectedRouteExplanation = useMemo(
    () => (selectedProxy ? explainDashboardSmartRoute(selectedProxy, smartRouteOptions) : null),
    [selectedProxy, smartRouteOptions]
  );
  const regionClusters = useMemo(
    () => buildDashboardRegionClusters(smartRoutePool, favoriteProfileIdSet).slice(0, 4),
    [favoriteProfileIdSet, smartRoutePool]
  );
  const latencyHeatmapRoutes = useMemo(
    () => rankedSmartRoutes.slice(0, 8).map((entry) => entry.proxy),
    [rankedSmartRoutes]
  );
  const measuredLatencyCount = useMemo(
    () => profiles.filter((profile) => hasMeasuredLatency(profile.ping)).length,
    [profiles]
  );
  const canConnectImmediately =
    status.status === "disconnected" || status.status === "error";
  const collectionKeyByProxyId = useMemo(() => {
    const mapping = new Map<string, string>();

    for (const collection of profileCollections) {
      for (const proxy of collection.proxies) {
        mapping.set(proxy.id, collection.key);
      }
    }

    return mapping;
  }, [profileCollections]);
  const favoriteLaunchpadRoutes = useMemo(() => {
    if (!favoriteLaunchpadOrder.length) {
      return favoriteProxies;
    }

    const orderedIds = favoriteLaunchpadOrder.filter((id) => favoriteProfileIdSet.has(id));
    const remainingIds = favoriteProxies
      .map((proxy) => proxy.id)
      .filter((id) => !orderedIds.includes(id));

    return [...orderedIds, ...remainingIds]
      .map((id) => proxyLookup.get(id) ?? null)
      .filter((proxy): proxy is ProxyNode => proxy != null);
  }, [favoriteLaunchpadOrder, favoriteProfileIdSet, favoriteProxies, proxyLookup]);

  const filteredProxies = useMemo(() => {
    if (!selectedCollection) {
      return [];
    }

    const visibleProxies = !deferredProxyQuery
      ? selectedCollection.proxies
      : selectedCollection.proxies.filter((proxy) => {
      const searchableText = [
        proxy.name,
        proxy.server,
        proxy.protocol,
        proxy.sni,
        proxy.fingerprint,
        proxy.method,
        proxy.network,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchableText.includes(deferredProxyQuery);
    });

    return sortDashboardVisibleProxies(visibleProxies, favoriteProfileIdSet);
  }, [deferredProxyQuery, favoriteProfileIdSet, selectedCollection]);

  const currentStatusLabel = t(`dashboard.status_${status.status}`, {
    defaultValue: status.status.toUpperCase(),
  });
  const selectedCollectionSourceLabel = selectedCollection
    ? t(`dashboard.collectionSource_${selectedCollection.source}`)
    : null;
  const selectedCollectionLabel = selectedCollection
    ? selectedCollection.source === "manual"
      ? t("dashboard.manualCollection")
      : selectedCollection.label
    : "—";
  const selectedCollectionTimestamp = formatCollectionTimestamp(selectedCollection?.updatedAt);
  const lastLatencyRefreshLabel = formatSessionTimestamp(lastLatencyRefreshAt);
  const lastStableConnectedLabel = formatSessionTimestamp(options.lastStableConnectedAt);
  const selectionStateLabel =
    status.status === "connected" && activeProxy?.id === selectedProxy?.id
      ? t("dashboard.activeRouteLive")
      : status.status === "connected" && activeProxy && selectedProxy && activeProxy.id !== selectedProxy.id
      ? t("dashboard.activeRouteQueued")
      : t("dashboard.activeRouteIdle");
  const selectedLatencyBadge = getLatencyBadge(selectedProxy?.ping);
  const bestLatencyBadge = getLatencyBadge(bestAvailableProxy?.ping);
  const bestRouteReasonKey = bestAvailableExplanation?.summaryKey ?? "dashboard.smartRouteReasonFallback";
  const selectedRegionLabel = selectedRouteExplanation?.regionLabel ?? null;
  const selectedRegionCountryCode = selectedProxy
    ? inferDashboardRegionCountryCode(selectedProxy)
    : null;
  const selectedTransportSignature =
    (selectedProxy ? formatRouteTransportSignature(selectedProxy) : null) ??
    t("dashboard.transportAdaptive");
  const selectedSecurityEnvelope =
    (selectedProxy ? formatRouteSecurityEnvelope(selectedProxy) : null) ??
    t("dashboard.securityEnvelopeStandard");
  const selectedCapacityLabel =
    (selectedProxy ? formatRouteCapacityLabel(selectedProxy) : null) ??
    t("dashboard.capacityAdaptive");
  const selectedEndpointLabel =
    (selectedProxy ? formatRouteEndpointLabel(selectedProxy) : null) ??
    t("dashboard.endpointPrimary");
  const selectedRouteModeLabel = selectedProxy
    ? selectedRelayProxy
      ? t("dashboard.routeModeRelay")
      : t("dashboard.routeModeDirect")
    : "—";
  const selectedLatencyLead = formatLatencyLeadLabel(selectedProxy?.ping, bestAvailableProxy?.ping);
  const selectedExplainSignals = selectedRouteExplanation?.signals.filter((signal) => signal.active) ?? [];
  const bestExplainSignals =
    bestAvailableExplanation?.signals.filter((signal) => signal.active).slice(0, 3) ?? [];
  const dashboardTelemetry = [
    {
      label: t("dashboard.status"),
      value: currentStatusLabel,
      icon: Activity,
      accent:
        {
          connected:
            "border-[color:color-mix(in_oklab,var(--color-matrix-green)_28%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_18%,black)]",
          connecting:
            "border-[color:color-mix(in_oklab,var(--color-neon-cyan)_28%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]",
          disconnecting:
            "border-[color:color-mix(in_oklab,var(--color-neon-cyan)_20%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_8%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_14%,black)]",
          degraded:
            "border-[color:color-mix(in_oklab,var(--color-neon-pink)_24%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]",
          error: "border-red-400/35 bg-red-500/10 text-red-300 dark:bg-red-500/14",
          disconnected: "border-border/70 bg-[color:var(--panel-subtle)]/72 text-muted-foreground",
        }[status.status] ?? "border-border/70 bg-[color:var(--panel-subtle)]/72 text-muted-foreground",
    },
    {
      label: t("dashboard.selectedProxy"),
      value: selectedProxy?.name ?? t("dashboard.unknownRoute"),
      icon: Fingerprint,
      accent: "border-border/70 bg-[color:var(--panel-surface)]/80 text-foreground",
    },
    {
      label: t("dashboard.download"),
      value: formatTrafficSpeed(status.downBytes ?? 0),
      icon: Gauge,
      accent:
        "border-[color:color-mix(in_oklab,var(--color-matrix-green)_20%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_8%,white)] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_14%,black)]",
    },
    {
      label: t("dashboard.upload"),
      value: formatTrafficSpeed(status.upBytes ?? 0),
      icon: ShieldCheck,
      accent:
        "border-[color:color-mix(in_oklab,var(--color-neon-cyan)_20%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_8%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_14%,black)]",
    },
  ];
  const connectedStateTheme =
    {
      connected: {
        accent: "var(--color-matrix-green)",
        chip:
          "border-[color:color-mix(in_oklab,var(--color-matrix-green)_28%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_16%,black)]",
      },
      connecting: {
        accent: "var(--color-neon-cyan)",
        chip:
          "border-[color:color-mix(in_oklab,var(--color-neon-cyan)_28%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]",
      },
      disconnecting: {
        accent: "var(--color-neon-cyan)",
        chip:
          "border-[color:color-mix(in_oklab,var(--color-neon-cyan)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_8%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_14%,black)]",
      },
      degraded: {
        accent: "var(--color-neon-pink)",
        chip:
          "border-[color:color-mix(in_oklab,var(--color-neon-pink)_26%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]",
      },
      error: {
        accent: "#f87171",
        chip: "border-red-400/35 bg-red-500/10 text-red-300 dark:bg-red-500/14",
      },
      disconnected: {
        accent: "var(--muted-foreground)",
        chip: "border-border/70 bg-[color:var(--panel-subtle)]/72 text-muted-foreground",
      },
    }[status.status] ?? {
      accent: "var(--muted-foreground)",
      chip: "border-border/70 bg-[color:var(--panel-subtle)]/72 text-muted-foreground",
    };
  const connectedStateMeters = [
    {
      label: t("dashboard.status"),
      value: currentStatusLabel,
      progress: clampDashboardMetric(
        {
          connected: 100,
          connecting: 76,
          disconnecting: 34,
          degraded: 68,
          error: 22,
          disconnected: 12,
        }[status.status] ?? 10
      ),
    },
    {
      label: t("dashboard.routeMode"),
      value: selectedRouteModeLabel,
      progress: clampDashboardMetric(selectedProxy ? (selectedRelayProxy ? 58 : 90) : 14),
    },
    {
      label: t("dashboard.routeRegion"),
      value: selectedRegionLabel ?? "—",
      progress: clampDashboardMetric(selectedProxy ? 84 : 16),
    },
    {
      label: t("dashboard.capacityLabel"),
      value: selectedCapacityLabel,
      progress: clampDashboardMetric(
        selectedProxy
          ? hasMeasuredLatency(selectedProxy.ping)
            ? 100 - Math.min(selectedProxy.ping, 320) / 3.2
            : 56
          : 18
      ),
    },
  ];
  const connectedStateSignalText = selectedProxy
    ? `${selectedProxy.protocol.toUpperCase()} • ${selectedEndpointLabel}`
    : t("dashboard.selectedRouteDesc");
  const connectedStateTrafficLabel = `${formatTrafficSpeed(status.downBytes ?? 0)} ↓ • ${formatTrafficSpeed(
    status.upBytes ?? 0
  )} ↑`;
  const connectedStatePulseAnimation =
    status.status === "connected" || status.status === "degraded" || status.status === "connecting";

  useEffect(() => {
    const nextFavoriteOrder = favoriteProxies.map((proxy) => proxy.id);

    if (!haveSameMembers(favoriteLaunchpadOrder, nextFavoriteOrder)) {
      setFavoriteLaunchpadOrder(nextFavoriteOrder);
    }
  }, [favoriteLaunchpadOrder, favoriteProxies]);

  useEffect(() => {
    if (!favoriteLaunchpadOrder.length || favoriteLaunchpadOrder.length !== favoriteProfileIds.length) {
      return;
    }

    if (areArraysEqual(favoriteLaunchpadOrder, favoriteProfileIds)) {
      return;
    }

    const persistTimer = window.setTimeout(() => {
      void updateOptions((current) => ({
        ...current,
        favoriteProfileIds: favoriteLaunchpadOrder,
        sourceSurface: "dashboard",
      })).catch((error) => {
        console.error("Failed to persist favorite launchpad order", error);
        toast.error(t("dashboard.favoritePersistError", { error: formatUnknownError(error) }));
      });
    }, 180);

    return () => {
      window.clearTimeout(persistTimer);
    };
  }, [favoriteLaunchpadOrder, favoriteProfileIds, t, updateOptions]);

  const refreshLatencyTelemetry = async ({ silent = true }: { silent?: boolean } = {}) => {
    if (latencyRefreshInFlightRef.current) {
      return;
    }

    latencyRefreshInFlightRef.current = true;
    setIsLatencyRefreshing(true);
    setLatencyRefreshError(null);

    try {
      await testAllLatencies();
      setLastLatencyRefreshAt(Date.now());

      if (!silent) {
        toast.success(t("dashboard.latencyRefreshSuccess"));
      }
    } catch (error) {
      const message = formatUnknownError(error);
      console.error("Failed to refresh dashboard latencies", error);
      setLatencyRefreshError(message);

      if (!silent) {
        toast.error(t("dashboard.latencyRefreshError", { error: message }));
      }
    } finally {
      latencyRefreshInFlightRef.current = false;
      setIsLatencyRefreshing(false);
    }
  };

  useEffect(() => {
    let unlistenProfilesUpdated: (() => void) | undefined;
    let latencyIntervalId: number | undefined;

    void loadProfileCatalog();
    void refreshLatencyTelemetry();

    listenProfilesUpdated(() => {
      setLastLatencyRefreshAt(Date.now());
      void loadProfileCatalog();
    })
      .then((cleanup) => {
        unlistenProfilesUpdated = cleanup;
      })
      .catch(console.error);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void refreshLatencyTelemetry();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    latencyIntervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void refreshLatencyTelemetry();
      }
    }, 90_000);

    return () => {
      unlistenProfilesUpdated?.();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (latencyIntervalId) {
        window.clearInterval(latencyIntervalId);
      }
    };
  }, []);

  useEffect(() => {
    getStealthMode().then(setStealthMode).catch(console.error);

    let unlistenTraffic: (() => void) | undefined;

    listenTrafficUpdate((data) => {
      setTrafficData((prev) => {
        const now = new Date().toLocaleTimeString();
        const newData = [...prev, { time: now, up: data.up, down: data.down }];
        return newData.length > 30 ? newData.slice(newData.length - 30) : newData;
      });
    })
      .then((cleanup) => {
        unlistenTraffic = cleanup;
      })
      .catch(console.error);

    return () => {
      unlistenTraffic?.();
    };
  }, []);

  useEffect(() => {
    if (status.status === "connected") {
      setConnectionDebugReport("");
      return;
    }

    if (status.status === "disconnected") {
      setTrafficData([]);
    }
  }, [status.status]);

  const persistSelectedProxy = async (proxyId: string) => {
    if (proxyId === options.profileId) {
      return;
    }

    try {
      await updateOptions((current) => ({
        ...current,
        profileId: proxyId,
        sourceSurface: "dashboard",
      }));
    } catch (error) {
      console.error("Failed to persist selected proxy", error);
      toast.error(t("dashboard.selectionPersistError", { error: formatUnknownError(error) }));
    }
  };

  const stageProxySelection = async (
    proxyId: string,
    { resetQuery = false }: { resetQuery?: boolean } = {}
  ) => {
    const nextCollectionKey = collectionKeyByProxyId.get(proxyId) ?? null;

    if (nextCollectionKey && nextCollectionKey !== selectedCollectionKey) {
      setSelectedCollectionKey(nextCollectionKey);
    }

    setSelectedProxyId(proxyId);

    if (resetQuery) {
      setProxyQuery("");
    }

    await persistSelectedProxy(proxyId);
  };

  const connectToProxy = async (proxy: ProxyNode, sourceSurface = "dashboard") => {
    let attemptedProfileId: string | null = null;

    try {
      setConnectionDebugReport("");
      attemptedProfileId = proxy.id;

      await connect(proxy.id, {
        tunMode: options.tunMode,
        systemProxy: options.systemProxy,
        sourceSurface,
      });
    } catch (error) {
      const errorText = formatUnknownError(error);
      console.error("Failed to connect", error);

      if (errorText.includes("Elevation Required") || errorText.includes("Administrator")) {
        toast.error(t("dashboard.tunErrorAdmin"), { duration: 8000 });
      } else {
        toast.error(t("dashboard.connectionFailed", { error: errorText }));
      }

      await captureConnectionDebugReport(errorText, attemptedProfileId);
    }
  };

  const toggleFavoriteProxy = async (proxyId: string) => {
    const nextFavoriteIds = favoriteProfileIdSet.has(proxyId)
      ? favoriteProfileIds.filter((favoriteId) => favoriteId !== proxyId)
      : [proxyId, ...favoriteProfileIds.filter((favoriteId) => favoriteId !== proxyId)].slice(
          0,
          24
        );

    try {
      await updateOptions((current) => ({
        ...current,
        favoriteProfileIds: nextFavoriteIds,
        sourceSurface: "dashboard",
      }));

      toast.success(
        favoriteProfileIdSet.has(proxyId)
          ? t("dashboard.favoriteRemoved")
          : t("dashboard.favoriteAdded")
      );
    } catch (error) {
      console.error("Failed to update favorite proxies", error);
      toast.error(t("dashboard.favoritePersistError", { error: formatUnknownError(error) }));
    }
  };

  const handleFavoriteReorder = (nextOrder: string[]) => {
    startTransition(() => {
      setFavoriteLaunchpadOrder(nextOrder.filter((id) => favoriteProfileIdSet.has(id)));
    });
  };

  const handleQuickAction = async (
    proxy: ProxyNode | null,
    mode: "best" | "stable"
  ) => {
    if (!proxy) {
      toast.error(
        mode === "best"
          ? t("dashboard.bestRouteUnavailable")
          : t("dashboard.lastStableUnavailable")
      );
      return;
    }

    await stageProxySelection(proxy.id, { resetQuery: true });

    if (!canConnectImmediately) {
      toast.info(t("dashboard.quickRouteQueued", { route: proxy.name }));
      return;
    }

    await connectToProxy(
      proxy,
      mode === "best" ? "dashboard-best-route" : "dashboard-last-stable"
    );
  };

  const handleCollectionSelect = async (nextCollectionKey: string) => {
    const nextCollection = profileCollections.find((collection) => collection.key === nextCollectionKey);
    const nextProxy = nextCollection?.proxies[0] ?? null;

    setSelectedCollectionKey(nextCollectionKey);
    setSelectedProxyId(nextProxy?.id ?? null);
    setProxyQuery("");

    if (nextProxy) {
      await persistSelectedProxy(nextProxy.id);
    }
  };

  const handleProxySelect = async (proxyId: string) => {
    await stageProxySelection(proxyId);
  };

  const captureConnectionDebugReport = async (
    errorText: string,
    attemptedProfileId: string | null
  ) => {
    setIsCollectingDebugReport(true);
    try {
      const snapshot = await getDesktopDiagnosticsSnapshot();
      setConnectionDebugReport(
        buildConnectionDebugReport(
          snapshot,
          errorText,
          attemptedProfileId,
          options.tunMode,
          options.systemProxy
        )
      );
    } catch (reportError) {
      setConnectionDebugReport([
        "=== CYBERVPN CONNECTION DEBUG REPORT BEGIN ===",
        `captured_at: ${new Date().toISOString()}`,
        `attempted_profile_id: ${attemptedProfileId ?? "unknown"}`,
        `tun_mode: ${String(options.tunMode)}`,
        `system_proxy: ${String(options.systemProxy)}`,
        `ui_error: ${redactSensitiveText(errorText)}`,
        `snapshot_error: ${redactSensitiveText(formatUnknownError(reportError))}`,
        "=== CYBERVPN CONNECTION DEBUG REPORT END ===",
      ].join("\n"));
    } finally {
      setIsCollectingDebugReport(false);
    }
  };

  const handleCopyConnectionDebugReport = async () => {
    if (!connectionDebugReport) {
      return;
    }

    try {
      await navigator.clipboard.writeText(connectionDebugReport);
      toast.success(t("dashboard.debugReportCopied"));
    } catch (error) {
      toast.error(t("dashboard.debugReportCopyFailed", { error: formatUnknownError(error) }));
    }
  };

  const handleConnect = async () => {
    if (!selectedProxy) {
      toast.error(t("dashboard.noProfilesError"));
      return;
    }

    await connectToProxy(selectedProxy);
  };

  const handleDisconnect = async () => {
    try {
      await disconnect("dashboard");
    } catch (error) {
      console.error("Failed to disconnect", error);
      toast.error(t("dashboard.disconnectFailed", { error: formatUnknownError(error) }));
    }
  };

  const handleTunModeChange = async (checked: boolean) => {
    try {
      await updateOptions((current) => ({
        ...current,
        tunMode: checked,
        sourceSurface: "dashboard",
      }));
    } catch (error) {
      console.error("Failed to persist TUN mode", error);
      toast.error(t("dashboard.connectionFailed", { error: formatUnknownError(error) }));
    }
  };

  const handleStealthToggle = async (checked: boolean) => {
    try {
      await saveStealthMode(checked);
      setStealthMode(checked);
      if (checked) {
        toast.success(t("dashboard.stealthActive"));
      } else {
        toast.info(t("dashboard.stealthDisabled"));
      }
    } catch (error) {
      console.error(error);
      toast.error(t("dashboard.stealthError"));
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: offsets.page }}
      animate={{
        opacity: 1,
        y: 0,
        backgroundColor: stealthMode ? "rgba(0, 30, 20, 0.4)" : "transparent",
      }}
      exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -4 }}
      transition={{
        default: { duration: durations.page, ease: desktopMotionEase },
        backgroundColor: { duration: durations.page, ease: "easeOut" },
      }}
      className="relative flex h-full flex-col gap-12 rounded-2xl p-4 transition-colors"
    >
      <header className="relative overflow-hidden rounded-[2rem] border border-border/60 bg-[color:var(--panel-surface)]/78 px-6 py-6 shadow-[var(--panel-shadow)] backdrop-blur-xl">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute -left-8 top-0 h-28 w-28 rounded-full bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_24%,transparent)] blur-3xl" />
          <div className="absolute bottom-0 right-8 h-24 w-24 rounded-full bg-[color:color-mix(in_oklab,var(--color-neon-pink)_20%,transparent)] blur-3xl" />
          <div className="absolute inset-x-8 top-0 h-px bg-[linear-gradient(90deg,transparent,color-mix(in_oklab,var(--color-neon-cyan)_28%,transparent),transparent)]" />
        </div>
        <div className="relative z-10 flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-cyan)_24%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_9%,white)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]">
              Secure Control Surface
            </div>
            <h1 className="text-4xl font-semibold tracking-[-0.04em] text-[var(--color-matrix-green)]">
              {t("dashboard.title")}
            </h1>
            <p className="mt-1 font-mono text-sm tracking-[0.14em] text-muted-foreground">
              {t("dashboard.status")}: {currentStatusLabel}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:w-[30rem]">
            {dashboardTelemetry.map((item, index) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: prefersReducedMotion ? 0 : offsets.list }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: durations.list,
                  delay: prefersReducedMotion ? 0 : index * 0.03,
                  ease: desktopMotionEase,
                }}
                className={`rounded-[1.5rem] border px-4 py-3 shadow-[var(--panel-shadow)] backdrop-blur-xl ${item.accent}`}
              >
                <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] opacity-75">
                  <item.icon size={14} />
                  {item.label}
                </div>
                <div className="font-mono text-sm tracking-[0.12em]">{item.value}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center gap-12">
        <section className="relative w-full max-w-[112rem] overflow-hidden rounded-[2rem] border border-border/60 bg-[color:var(--panel-surface)]/82 px-5 py-6 shadow-[var(--panel-shadow-strong)] backdrop-blur-2xl 2xl:px-7">
          <div aria-hidden className="pointer-events-none absolute inset-0">
            <div className="absolute inset-x-10 top-0 h-px bg-[linear-gradient(90deg,transparent,color-mix(in_oklab,var(--color-neon-cyan)_24%,transparent),transparent)]" />
            <div className="absolute inset-y-8 left-0 w-px bg-[linear-gradient(180deg,transparent,color-mix(in_oklab,var(--color-matrix-green)_18%,transparent),transparent)]" />
            <div className="absolute -left-10 top-10 h-40 w-40 rounded-full bg-[color:color-mix(in_oklab,var(--color-matrix-green)_16%,transparent)] blur-3xl" />
            <div className="absolute -right-12 bottom-8 h-44 w-44 rounded-full bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,transparent)] blur-3xl" />
          </div>

          <div className="relative z-10 flex flex-col gap-6">
            <div className="grid w-full gap-3 md:grid-cols-3">
              <div className="rounded-[1.4rem] border border-border/65 bg-[color:var(--field-surface)]/88 px-4 py-3 shadow-[var(--panel-shadow)]">
                <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                  {t("dashboard.tunModeTitle")}
                </div>
                <div className="mt-2 font-mono text-sm tracking-[0.12em] text-[var(--color-matrix-green)]">
                  {options.tunMode ? "TUN ACTIVE" : "PROXY PATH"}
                </div>
              </div>
              <div className="rounded-[1.4rem] border border-border/65 bg-[color:var(--field-surface)]/88 px-4 py-3 shadow-[var(--panel-shadow)]">
                <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                  {t("dashboard.stealthModeTitle")}
                </div>
                <div className="mt-2 font-mono text-sm tracking-[0.12em] text-[var(--color-neon-cyan)]">
                  {stealthMode ? "MASKED PROFILE" : "STANDARD PROFILE"}
                </div>
              </div>
              <div className="rounded-[1.4rem] border border-border/65 bg-[color:var(--field-surface)]/88 px-4 py-3 shadow-[var(--panel-shadow)]">
                <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                  {t("dashboard.networkTraffic")}
                </div>
                <div className="mt-2 font-mono text-sm tracking-[0.12em] text-foreground">
                  {formatTrafficSpeed((status.upBytes ?? 0) + (status.downBytes ?? 0))}
                </div>
              </div>
            </div>

            {catalogError ? (
              <div className="flex flex-col gap-4 rounded-[1.8rem] border border-red-400/30 bg-red-500/10 px-5 py-5 shadow-[var(--panel-shadow)]">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-red-200">
                    {t("dashboard.catalogLoadError", { error: catalogError })}
                  </div>
                </div>
                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => void loadProfileCatalog()}>
                    {t("dashboard.debugReportRefresh")}
                  </Button>
                </div>
              </div>
            ) : isCatalogLoading ? (
                <div className="grid gap-5 2xl:grid-cols-[minmax(28rem,0.88fr)_minmax(40rem,1.12fr)]">
                {[0, 1].map((index) => (
                  <div
                    key={index}
                    className="min-w-0 animate-pulse rounded-[1.8rem] border border-border/60 bg-[color:var(--chrome-elevated)]/78 p-5 shadow-[var(--panel-shadow)]"
                  >
                    <div className="h-4 w-24 rounded-full bg-[color:var(--panel-subtle)]" />
                    <div className="mt-4 h-12 rounded-[1.2rem] bg-[color:var(--panel-subtle)]" />
                    <div className="mt-4 space-y-3">
                      <div className="h-16 rounded-[1.2rem] bg-[color:var(--panel-subtle)]" />
                      <div className="h-16 rounded-[1.2rem] bg-[color:var(--panel-subtle)]" />
                    </div>
                  </div>
                ))}
              </div>
            ) : profileCollections.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-4 rounded-[1.9rem] border border-border/60 bg-[color:var(--chrome-elevated)]/78 px-6 py-10 text-center shadow-[var(--panel-shadow)]">
                <div className="inline-flex h-14 w-14 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-cyan)_30%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_12%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]">
                  <Sparkles size={22} />
                </div>
                <div>
                  <h2 className="text-xl font-semibold tracking-[-0.03em] text-foreground">
                    {t("dashboard.catalogEmptyTitle")}
                  </h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                    {t("dashboard.catalogEmptyDesc")}
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-center gap-3">
                  <Button variant="outline" onClick={() => navigate("/subscriptions")}>
                    {t("dashboard.openSubscriptions")}
                  </Button>
                  <Button onClick={() => navigate("/profiles")}>{t("dashboard.openProfiles")}</Button>
                </div>
              </div>
            ) : (
              <>
                <div className="grid gap-5 2xl:grid-cols-[minmax(28rem,0.84fr)_minmax(42rem,1.16fr)]">
                  <div className="min-w-0 rounded-[1.8rem] border border-border/60 bg-[color:var(--chrome-elevated)]/82 p-5 shadow-[var(--panel-shadow)]">
                    <div className="mb-4 flex items-start justify-between gap-4">
                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--color-neon-pink)]">
                          {t("dashboard.pinnedRoutesEyebrow")}
                        </div>
                        <h2 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-foreground">
                          {t("dashboard.pinnedRoutesTitle")}
                        </h2>
                        <p className="mt-1 text-sm leading-6 text-muted-foreground">
                          {t("dashboard.pinnedRoutesDesc")}
                        </p>
                      </div>
                      <div className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-pink)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]">
                        <Star size={18} />
                      </div>
                    </div>

                    {favoriteLaunchpadRoutes.length ? (
                      <>
                        <div className="mb-4 flex flex-wrap items-center gap-3 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                          <span className="rounded-full border border-border/70 bg-[color:var(--panel-subtle)] px-3 py-1">
                            {t("dashboard.pinnedRoutesDragHint")}
                          </span>
                          <span className="rounded-full border border-border/70 bg-[color:var(--panel-subtle)] px-3 py-1">
                            {t("dashboard.pinnedRoutesInScope", {
                              count: selectedCollectionFavoriteCount,
                            })}
                          </span>
                        </div>

                        <Reorder.Group
                          as="div"
                          axis="y"
                          values={favoriteLaunchpadRoutes.map((proxy) => proxy.id)}
                          onReorder={handleFavoriteReorder}
                          className="max-h-[24rem] space-y-3 overflow-y-auto pr-1"
                        >
                          {favoriteLaunchpadRoutes.map((proxy) => (
                            <PinnedRouteCard
                              key={proxy.id}
                              proxy={proxy}
                              latencyBadge={getLatencyBadge(proxy.ping)}
                              isSelected={proxy.id === selectedProxy?.id}
                              isActive={proxy.id === activeProxy?.id}
                              onStage={() => {
                                void stageProxySelection(proxy.id, { resetQuery: true });
                              }}
                              onToggleFavorite={() => {
                                void toggleFavoriteProxy(proxy.id);
                              }}
                              translate={(key, options) =>
                                String(t(key as never, options as never))
                              }
                            />
                          ))}
                        </Reorder.Group>
                      </>
                    ) : (
                      <div className="rounded-[1.35rem] border border-dashed border-border/70 bg-[color:var(--panel-subtle)]/64 px-4 py-5">
                        <div className="text-sm font-semibold text-foreground">
                          {t("dashboard.pinnedRoutesEmptyTitle")}
                        </div>
                        <p className="mt-2 text-sm leading-6 text-muted-foreground">
                          {t("dashboard.pinnedRoutesEmptyDesc")}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="min-w-0 rounded-[1.8rem] border border-border/60 bg-[color:var(--chrome-elevated)]/82 p-5 shadow-[var(--panel-shadow)]">
                    <div className="mb-4 flex items-start justify-between gap-4">
                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--color-neon-cyan)]">
                          {t("dashboard.latencyOpsEyebrow")}
                        </div>
                        <h2 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-foreground">
                          {t("dashboard.latencyOpsTitle")}
                        </h2>
                        <p className="mt-1 text-sm leading-6 text-muted-foreground">
                          {t("dashboard.latencyOpsDesc")}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        onClick={() => void refreshLatencyTelemetry({ silent: false })}
                        disabled={isLatencyRefreshing}
                        className="h-11 rounded-[1rem] border-border/70 bg-[color:var(--field-surface)]/88 px-4 shadow-[var(--panel-shadow)]"
                      >
                        {isLatencyRefreshing ? (
                          <LoaderCircle size={15} className="animate-spin" />
                        ) : (
                          <RefreshCw size={15} />
                        )}
                        <span>{t("dashboard.refreshLatency")}</span>
                      </Button>
                    </div>

                    <div className="grid gap-3 lg:grid-cols-2 min-[1680px]:grid-cols-[minmax(0,0.78fr)_minmax(0,1.22fr)_minmax(0,0.94fr)]">
                      <div className="min-w-0 rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                          {t("dashboard.latencyCoverage")}
                        </div>
                        <div className="mt-2 text-sm font-semibold text-foreground">
                          {t("dashboard.latencyCoverageValue", {
                            measured: measuredLatencyCount,
                            total: profiles.length,
                          })}
                        </div>
                      </div>
                      <div className="min-w-0 rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                          {t("dashboard.bestAvailable")}
                        </div>
                        <div className="mt-2 break-words text-sm font-semibold text-foreground">
                          {bestAvailableProxy?.name ?? t("dashboard.bestRouteUnavailable")}
                        </div>
                        <div className="mt-1 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                          {bestAvailableProxy ? bestLatencyBadge.detail : t("dashboard.latencyNoProbe")}
                        </div>
                        <div className="mt-2 text-xs leading-5 text-muted-foreground">
                          {t(bestRouteReasonKey)}
                        </div>
                        {bestAvailableProxy && bestExplainSignals.length ? (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {bestExplainSignals.map((signal) => (
                              <SmartSignalChip
                                key={`best-${signal.kind}`}
                                signal={signal}
                                proxy={bestAvailableProxy}
                                latencyBadge={bestLatencyBadge}
                                translate={(key, options) =>
                                  String(t(key as never, options as never))
                                }
                              />
                            ))}
                          </div>
                        ) : null}
                      </div>
                      <div className="min-w-0 rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                          {t("dashboard.lastStable")}
                        </div>
                        <div className="mt-2 break-words text-sm font-semibold text-foreground">
                          {lastStableProxy?.name ?? t("dashboard.lastStableUnavailable")}
                        </div>
                        <div className="mt-1 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                          {lastStableConnectedLabel
                            ? t("dashboard.lastStableSeen", { time: lastStableConnectedLabel })
                            : t("dashboard.lastStableNever")}
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <Button
                        onClick={() => void handleQuickAction(bestAvailableProxy, "best")}
                        className="h-12 rounded-[1.1rem] shadow-[var(--panel-shadow)]"
                      >
                        <Zap size={16} />
                        <span>{t("dashboard.connectBest")}</span>
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => void handleQuickAction(lastStableProxy, "stable")}
                        className="h-12 rounded-[1.1rem] border-border/70 bg-[color:var(--field-surface)]/88 shadow-[var(--panel-shadow)]"
                      >
                        <Clock3 size={16} />
                        <span>{t("dashboard.connectLastStable")}</span>
                      </Button>
                    </div>

                    <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)] 2xl:grid-cols-[minmax(0,1.04fr)_minmax(0,0.96fr)]">
                      <div className="rounded-[1.35rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 p-4">
                        <div className="mb-3 flex items-start justify-between gap-4">
                          <div>
                            <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                              {t("dashboard.latencyHeatmapTitle")}
                            </div>
                            <p className="mt-1 text-sm leading-6 text-muted-foreground">
                              {t("dashboard.latencyHeatmapDesc")}
                            </p>
                          </div>
                          <div className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-cyan)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]">
                            <Globe2 size={16} />
                          </div>
                        </div>

                        {latencyHeatmapRoutes.length ? (
                          <div className="grid gap-2 sm:grid-cols-2">
                            {latencyHeatmapRoutes.map((proxy) => {
                              const latencyBadge = getLatencyBadge(proxy.ping);
                              const regionMeta = getRouteRegionMeta(proxy);
                              const isHeatmapBest = proxy.id === bestAvailableProxy?.id;
                              const isHeatmapActive = proxy.id === activeProxy?.id;
                              const isHeatmapFavorite = favoriteProfileIdSet.has(proxy.id);

                              return (
                                <button
                                  key={proxy.id}
                                  type="button"
                                  onClick={() => void stageProxySelection(proxy.id)}
                                  className={`rounded-[1.2rem] border p-3 text-left shadow-[var(--panel-shadow)] transition-[transform,border-color,background-color] duration-200 hover:-translate-y-0.5 ${getLatencyHeatTone(proxy.ping)}`}
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                      <div className="truncate text-sm font-semibold text-foreground">
                                        {proxy.name}
                                      </div>
                                      <div className="mt-1 inline-flex max-w-full items-center gap-2 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                                        <CountryFlag
                                          code={regionMeta.countryCode}
                                          className="h-3.5 w-[1.3125rem] rounded-[0.15rem] border border-border/65 shadow-[var(--panel-shadow)]"
                                          fallbackClassName="h-3.5 w-[1.3125rem]"
                                        />
                                        <span className="truncate">{regionMeta.label}</span>
                                      </div>
                                    </div>
                                    <span className="font-mono text-[11px] tracking-[0.16em] text-foreground">
                                      {latencyBadge.detail}
                                    </span>
                                  </div>
                                  <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em]">
                                    {isHeatmapBest ? (
                                      <span className="rounded-full border border-[color:color-mix(in_oklab,var(--color-matrix-green)_26%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] px-2 py-1 text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_14%,black)]">
                                        {t("dashboard.latencyHeatmapBest")}
                                      </span>
                                    ) : null}
                                    {isHeatmapActive ? (
                                      <span className="rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-cyan)_26%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] px-2 py-1 text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]">
                                        {t("dashboard.latencyHeatmapLive")}
                                      </span>
                                    ) : null}
                                    {isHeatmapFavorite ? (
                                      <span className="rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-pink)_24%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] px-2 py-1 text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]">
                                        {t("dashboard.latencyHeatmapPinned")}
                                      </span>
                                    ) : null}
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="rounded-[1.2rem] border border-dashed border-border/70 bg-[color:var(--panel-surface)]/76 px-4 py-5 text-sm text-muted-foreground">
                            {t("dashboard.latencyHeatmapEmpty")}
                          </div>
                        )}
                      </div>

                      <div className="rounded-[1.35rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 p-4">
                        <div className="mb-3 flex items-start justify-between gap-4">
                          <div>
                            <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                              {t("dashboard.regionClustersTitle")}
                            </div>
                            <p className="mt-1 text-sm leading-6 text-muted-foreground">
                              {t("dashboard.regionClustersDesc")}
                            </p>
                          </div>
                          <div className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-pink)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]">
                            <MapIcon size={16} />
                          </div>
                        </div>

                        {regionClusters.length ? (
                          <div className="space-y-2">
                            {regionClusters.map((cluster) => (
                              <div
                                key={cluster.key}
                                className="rounded-[1.15rem] border border-border/70 bg-[color:var(--panel-surface)]/82 px-4 py-3 shadow-[var(--panel-shadow)]"
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <div className="text-sm font-semibold text-foreground">
                                      {cluster.label}
                                    </div>
                                    <div className="mt-1 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                                      {cluster.dominantProtocol ?? "—"}
                                    </div>
                                  </div>
                                  <span className="rounded-full border border-border/70 bg-[color:var(--panel-subtle)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                    {t("dashboard.regionClustersInferred")}
                                  </span>
                                </div>
                                <div className="mt-3 grid gap-2 sm:grid-cols-3">
                                  <div>
                                    <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                      {t("dashboard.regionClusterInventory")}
                                    </div>
                                    <div className="mt-1 text-sm font-semibold text-foreground">
                                      {cluster.proxyCount}
                                    </div>
                                  </div>
                                  <div>
                                    <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                      {t("dashboard.regionClusterFavorites")}
                                    </div>
                                    <div className="mt-1 text-sm font-semibold text-foreground">
                                      {cluster.favoriteCount}
                                    </div>
                                  </div>
                                  <div>
                                    <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                      {t("dashboard.regionClusterBest")}
                                    </div>
                                    <div className="mt-1 text-sm font-semibold text-foreground">
                                      {cluster.bestLatency != null
                                        ? `${cluster.bestLatency} ms`
                                        : t("dashboard.latencyNoProbe")}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="rounded-[1.2rem] border border-dashed border-border/70 bg-[color:var(--panel-surface)]/76 px-4 py-5 text-sm text-muted-foreground">
                            {t("dashboard.regionClustersEmpty")}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-3 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                      <span className="rounded-full border border-border/70 bg-[color:var(--panel-subtle)] px-3 py-1">
                        {lastLatencyRefreshLabel
                          ? t("dashboard.latencyLastRefresh", { time: lastLatencyRefreshLabel })
                          : t("dashboard.latencyAwaiting")}
                      </span>
                      {latencyRefreshError ? (
                        <span className="rounded-full border border-red-400/30 bg-red-500/10 px-3 py-1 text-red-200">
                          {t("dashboard.latencyRefreshInlineError")}
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="grid gap-5">
                  <div className="rounded-[1.8rem] border border-border/60 bg-[color:var(--chrome-elevated)]/82 p-5 shadow-[var(--panel-shadow)]">
                    <div className="mb-4 flex items-start justify-between gap-4">
                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--color-neon-cyan)]">
                          {t("dashboard.selectionStepProfile")}
                        </div>
                        <h2 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-foreground">
                          {t("dashboard.accessProfile")}
                        </h2>
                        <p className="mt-1 text-sm leading-6 text-muted-foreground">
                          {t("dashboard.accessProfileDesc")}
                        </p>
                      </div>
                      <div className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-cyan)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_14%,black)]">
                        <Layers3 size={18} />
                      </div>
                    </div>

                    <Select
                      value={selectedCollectionKey ?? undefined}
                      onValueChange={(value) => {
                        if (value != null) {
                          void handleCollectionSelect(String(value));
                        }
                      }}
                    >
                      <SelectTrigger className="h-14 w-full rounded-[1.3rem] border-border/70 bg-[color:var(--field-surface)]/92 px-4 text-left shadow-[var(--panel-shadow)]">
                        <SelectValue placeholder={t("dashboard.accessProfile")}>
                          {(value) => {
                            const collection = profileCollections.find((entry) => entry.key === value);
                            if (!collection) {
                              return t("dashboard.accessProfile");
                            }

                            return (
                              <div className="flex min-w-0 flex-1 items-center gap-3">
                                <div className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-matrix-green)_20%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_14%,black)]">
                                  <Layers3 size={15} />
                                </div>
                                <div className="min-w-0">
                                  <div className="truncate text-sm font-semibold text-foreground">
                                    {collection.source === "manual"
                                      ? t("dashboard.manualCollection")
                                      : collection.label}
                                  </div>
                                  <div className="truncate text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                                    {t("dashboard.collectionProxyCount", {
                                      count: collection.proxyCount,
                                    })}{" "}
                                    • {t(`dashboard.collectionSource_${collection.source}`)}
                                  </div>
                                </div>
                              </div>
                            );
                          }}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent
                        align="start"
                        sideOffset={10}
                        alignItemWithTrigger={false}
                        className="max-h-88 w-[min(42rem,calc(var(--anchor-width)+7rem))] rounded-[1.5rem] p-2"
                      >
                        {profileCollections.map((collection) => (
                          <SelectItem
                            key={collection.key}
                            value={collection.key}
                            className="rounded-[1rem] px-3 py-3"
                          >
                            <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
                              <div className="min-w-0">
                                <div className="truncate text-sm font-semibold text-foreground">
                                  {collection.source === "manual"
                                    ? t("dashboard.manualCollection")
                                    : collection.label}
                                </div>
                                <div className="mt-1 flex flex-wrap gap-2 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                                  <span>{t(`dashboard.collectionSource_${collection.source}`)}</span>
                                  <span>{t("dashboard.collectionProxyCount", { count: collection.proxyCount })}</span>
                                  {collection.updatedAt ? (
                                    <span>
                                      {t("dashboard.collectionUpdated", {
                                        time: formatCollectionTimestamp(collection.updatedAt),
                                      })}
                                    </span>
                                  ) : null}
                                </div>
                              </div>
                              <div className="flex flex-wrap justify-end gap-1">
                                {collection.protocols.slice(0, 3).map((protocol) => (
                                  <span
                                    key={protocol}
                                    className="rounded-full border border-border/70 bg-[color:var(--panel-subtle)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground"
                                  >
                                    {protocol}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <div className="mt-4 grid gap-3 sm:grid-cols-3">
                      <div className="rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                          {t("dashboard.profileCollection")}
                        </div>
                        <div className="mt-2 text-sm font-semibold text-foreground">
                          {selectedCollectionSourceLabel ?? "—"}
                        </div>
                      </div>
                      <div className="rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                          {t("dashboard.proxyInventory")}
                        </div>
                        <div className="mt-2 text-sm font-semibold text-foreground">
                          {t("dashboard.collectionProxyCount", {
                            count: selectedCollection?.proxyCount ?? 0,
                          })}
                        </div>
                      </div>
                      <div className="rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                          {t("dashboard.lastSynced")}
                        </div>
                        <div className="mt-2 text-sm font-semibold text-foreground">
                          {selectedCollectionTimestamp ?? t(`dashboard.collectionHint_${selectedCollection?.source ?? "manual"}`)}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-[1.8rem] border border-border/60 bg-[color:var(--chrome-elevated)]/82 p-5 shadow-[var(--panel-shadow)]">
                    <div className="mb-4 flex items-start justify-between gap-4">
                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--color-matrix-green)]">
                          {t("dashboard.selectionStepProxy")}
                        </div>
                        <h2 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-foreground">
                          {t("dashboard.proxyNode")}
                        </h2>
                        <p className="mt-1 text-sm leading-6 text-muted-foreground">
                          {t("dashboard.proxyNodeDesc")}
                        </p>
                      </div>
                      <div className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-matrix-green)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_12%,white)] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_16%,black)]">
                        <Server size={18} />
                      </div>
                    </div>

                    <div className="relative">
                      <Search
                        size={16}
                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                      />
                      <Input
                        value={proxyQuery}
                        onChange={(event) => setProxyQuery(event.target.value)}
                        placeholder={t("dashboard.searchProxyPlaceholder")}
                        className="h-11 rounded-[1.2rem] border-border/70 bg-[color:var(--field-surface)]/92 pl-10 pr-4 shadow-[var(--panel-shadow)]"
                        disabled={!selectedCollection}
                      />
                    </div>

                    <div className="mt-4 flex items-center justify-between text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                      <span>
                        {selectedCollection
                          ? selectedCollection.source === "manual"
                            ? t("dashboard.manualCollection")
                            : selectedCollection.label
                          : t("dashboard.accessProfile")}
                      </span>
                      <span>{t("dashboard.searchResults", { count: filteredProxies.length })}</span>
                    </div>

                    <div className="mt-3 max-h-[28rem] space-y-2 overflow-y-auto pr-1">
                      {!filteredProxies.length ? (
                        <div className="rounded-[1.35rem] border border-dashed border-border/70 bg-[color:var(--panel-subtle)]/64 px-4 py-5 text-center">
                          <div className="text-sm font-semibold text-foreground">
                            {deferredProxyQuery
                              ? t("dashboard.collectionNoMatches", { query: proxyQuery.trim() })
                              : t("dashboard.collectionEmptyTitle")}
                          </div>
                          <p className="mt-2 text-sm leading-6 text-muted-foreground">
                            {deferredProxyQuery
                              ? t("dashboard.collectionNoMatchesHint")
                              : t("dashboard.collectionEmptyDesc")}
                          </p>
                        </div>
                      ) : (
                        filteredProxies.map((proxy) => {
                          const isSelected = proxy.id === selectedProxy?.id;
                          const isActive = proxy.id === activeProxy?.id;
                          const isFavorite = favoriteProfileIdSet.has(proxy.id);
                          const latencyBadge = getLatencyBadge(proxy.ping);
                          const regionMeta = getRouteRegionMeta(proxy);
                          const transportLabel = formatRouteTransportSignature(proxy);
                          const endpointLabel = formatRouteEndpointLabel(proxy);

                          return (
                            <motion.div
                              key={proxy.id}
                              layout
                              className={`group relative w-full overflow-hidden rounded-[1.35rem] border px-4 py-3 text-left shadow-[var(--panel-shadow)] transition-[transform,border-color,background-color,box-shadow] duration-200 hover:-translate-y-0.5 ${
                                isSelected
                                  ? "border-[color:color-mix(in_oklab,var(--color-matrix-green)_30%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_12%,var(--panel-surface))]"
                                  : "border-border/70 bg-[color:var(--panel-surface)]/88 hover:border-border hover:bg-[color:var(--panel-subtle)]/80"
                              }`}
                            >
                              {isSelected ? (
                                <motion.span
                                  layoutId="dashboard-proxy-active"
                                  transition={{ duration: durations.accent, ease: desktopMotionEase }}
                                  className="pointer-events-none absolute inset-0 rounded-[1.35rem] border border-[color:color-mix(in_oklab,var(--color-matrix-green)_24%,transparent)] bg-[linear-gradient(135deg,color-mix(in_oklab,var(--color-matrix-green)_14%,transparent),transparent_68%)]"
                                />
                              ) : null}
                              <div className="relative z-10 flex items-start gap-3">
                                <button
                                  type="button"
                                  onClick={() => void handleProxySelect(proxy.id)}
                                  className="flex min-w-0 flex-1 items-start justify-between gap-3 text-left"
                                >
                                  <div className="min-w-0">
                                    <div className="flex flex-wrap items-center gap-2">
                                      <span className="truncate text-sm font-semibold text-foreground">
                                        {proxy.name}
                                      </span>
                                      {isActive ? (
                                        <span className="rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-cyan)_32%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]">
                                          LIVE
                                        </span>
                                      ) : null}
                                      {bestInCollectionProxy?.id === proxy.id ? (
                                        <span className="rounded-full border border-[color:color-mix(in_oklab,var(--color-matrix-green)_26%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_14%,black)]">
                                          {t("dashboard.bestAvailableBadge")}
                                        </span>
                                      ) : null}
                                      {isFavorite ? (
                                        <span className="rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-pink)_26%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]">
                                          {t("dashboard.favoritePinned")}
                                        </span>
                                      ) : null}
                                    </div>
                                    <div className="mt-1 flex flex-wrap gap-2 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                                      <span className="inline-flex min-w-0 items-center gap-1.5">
                                        <CountryFlag
                                          code={regionMeta.countryCode}
                                          className="h-3 w-[1.125rem] rounded-[0.15rem] border border-border/65 shadow-[var(--panel-shadow)]"
                                          fallbackClassName="h-3 w-[1.125rem]"
                                        />
                                        <span className="truncate">{regionMeta.label}</span>
                                      </span>
                                      <span>{proxy.protocol.toUpperCase()}</span>
                                      {transportLabel ? <span>{transportLabel}</span> : null}
                                      <span>
                                        {proxy.server}:{proxy.port}
                                      </span>
                                      {endpointLabel ? <span>{endpointLabel}</span> : null}
                                    </div>
                                  </div>
                                  <div className="flex shrink-0 flex-col items-end gap-2">
                                    <span
                                      className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${latencyBadge.tone}`}
                                    >
                                      {t(latencyBadge.labelKey)}
                                    </span>
                                    <div className="flex items-center gap-2 font-mono text-[11px] tracking-[0.16em] text-foreground">
                                      <span>{latencyBadge.detail}</span>
                                      <ArrowRight
                                        size={15}
                                        className={`transition-transform duration-200 ${
                                          isSelected
                                            ? "translate-x-0.5 text-[var(--color-matrix-green)]"
                                            : "text-muted-foreground group-hover:translate-x-0.5"
                                        }`}
                                      />
                                    </div>
                                  </div>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => void toggleFavoriteProxy(proxy.id)}
                                  aria-label={
                                    isFavorite
                                      ? t("dashboard.favoriteRemoveAria", { route: proxy.name })
                                      : t("dashboard.favoriteAddAria", { route: proxy.name })
                                  }
                                  className={`mt-0.5 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border transition-colors ${
                                    isFavorite
                                      ? "border-[color:color-mix(in_oklab,var(--color-neon-pink)_28%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]"
                                      : "border-border/70 bg-[color:var(--panel-subtle)]/72 text-muted-foreground hover:text-[var(--color-neon-pink)]"
                                  }`}
                                >
                                  <Star size={16} className={isFavorite ? "fill-current" : ""} />
                                </button>
                              </div>
                              {proxy.nextHopId ? (
                                <div className="relative z-10 mt-3 flex items-center gap-2 text-xs text-[var(--color-neon-pink)]">
                                  <Waypoints size={13} />
                                  {t("dashboard.relayPath")}:{" "}
                                  {proxyLookup.get(proxy.nextHopId)?.name ?? t("profiles.unknown")}
                                </div>
                              ) : null}
                            </motion.div>
                          );
                        })
                      )}
                    </div>
                  </div>
                </div>

                <div className="grid gap-5 xl:grid-cols-[minmax(0,1.18fr)_21rem] 2xl:grid-cols-[minmax(0,1.2fr)_22rem] xl:items-stretch">
                  <div className="relative overflow-hidden rounded-[2rem] border border-border/60 bg-[color:var(--chrome-elevated)]/84 p-5 shadow-[var(--panel-shadow-strong)]">
                    <div aria-hidden className="pointer-events-none absolute inset-0">
                      <div className="absolute inset-x-10 top-0 h-px bg-[linear-gradient(90deg,transparent,color-mix(in_oklab,var(--color-neon-cyan)_28%,transparent),transparent)]" />
                      <div className="absolute -left-12 top-12 h-44 w-44 rounded-full bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_14%,transparent)] blur-3xl" />
                      <div className="absolute right-0 top-8 h-36 w-36 rounded-full bg-[color:color-mix(in_oklab,var(--color-neon-pink)_14%,transparent)] blur-3xl" />
                      <div className="absolute bottom-0 left-12 h-32 w-32 rounded-full bg-[color:color-mix(in_oklab,var(--color-matrix-green)_16%,transparent)] blur-3xl" />
                    </div>

                    <div className="relative z-10">
                      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                        <div className="min-w-0">
                          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[color:color-mix(in_oklab,var(--color-matrix-green)_24%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_14%,black)]">
                            {t("dashboard.selectedRoute")}
                          </div>
                          <h2 className="truncate text-2xl font-semibold tracking-[-0.04em] text-foreground">
                            {selectedProxy?.name ?? t("dashboard.unknownRoute")}
                          </h2>
                          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                            {selectedProxy
                              ? t(selectedRouteExplanation?.summaryKey ?? "dashboard.smartRouteReasonFallback")
                              : t("dashboard.selectedRouteDesc")}
                          </p>

                          <div className="mt-4 flex flex-wrap items-center gap-2">
                            <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-[color:var(--panel-subtle)]/72 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                              <Sparkles size={14} className="text-[var(--color-neon-cyan)]" />
                              {selectionStateLabel}
                            </span>
                            {selectedProxy ? (
                              <span
                                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] ${selectedLatencyBadge.tone}`}
                              >
                                <Gauge size={13} />
                                {selectedLatencyBadge.detail}
                              </span>
                            ) : null}
                            {selectedRegionLabel ? (
                              <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-[color:var(--panel-subtle)]/72 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                <CountryFlag
                                  code={selectedRegionCountryCode}
                                  className="h-3.5 w-[1.3125rem] rounded-[0.15rem] border border-border/65 shadow-[var(--panel-shadow)]"
                                  fallbackClassName="h-3.5 w-[1.3125rem]"
                                />
                                <span>{selectedRegionLabel}</span>
                              </span>
                            ) : null}
                            {selectedProxy ? (
                              <span className="rounded-full border border-border/70 bg-[color:var(--panel-subtle)]/72 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                {selectedRouteModeLabel}
                              </span>
                            ) : null}
                          </div>
                        </div>

                        <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[18rem]">
                          <div className="rounded-[1.35rem] border border-[color:color-mix(in_oklab,var(--color-neon-cyan)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] px-4 py-3 text-[var(--color-neon-cyan)] shadow-[var(--panel-shadow)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]">
                            <div className="text-[10px] font-semibold uppercase tracking-[0.22em] opacity-75">
                              {t("dashboard.smartScore")}
                            </div>
                            <div className="mt-2 font-mono text-2xl font-semibold tracking-[0.08em] text-foreground">
                              {selectedRouteExplanation
                                ? formatDashboardScore(selectedRouteExplanation.score)
                                : "—"}
                            </div>
                            <div className="mt-1 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                              {t("dashboard.smartScoreHint")}
                            </div>
                          </div>
                          <div className="rounded-[1.35rem] border border-[color:color-mix(in_oklab,var(--color-neon-pink)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] px-4 py-3 text-[var(--color-neon-pink)] shadow-[var(--panel-shadow)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]">
                            <div className="text-[10px] font-semibold uppercase tracking-[0.22em] opacity-75">
                              {t("dashboard.bestRouteDelta")}
                            </div>
                            <div className="mt-2 font-mono text-2xl font-semibold tracking-[0.08em] text-foreground">
                              {selectedProxy?.id === bestAvailableProxy?.id
                                ? t("dashboard.bestRouteLeading")
                                : selectedLatencyLead ?? "—"}
                            </div>
                            <div className="mt-1 truncate text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                              {selectedProxy?.id === bestAvailableProxy?.id
                                ? t("dashboard.bestRouteLeadingHint")
                                : bestAvailableProxy?.name ?? t("dashboard.bestRouteUnavailable")}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3">
                        <div className="rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                            {t("dashboard.proxyNode")}
                          </div>
                          <div className="mt-2 text-sm font-semibold text-foreground">
                            {selectedProxy?.server ? `${selectedProxy.server}:${selectedProxy.port}` : "—"}
                          </div>
                        </div>
                        <div className="rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                            {t("profiles.protocol")}
                          </div>
                          <div className="mt-2 text-sm font-semibold text-foreground">
                            {selectedProxy?.protocol?.toUpperCase() ?? "—"}
                          </div>
                        </div>
                        <div className="rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                            {t("dashboard.routeRegion")}
                          </div>
                          {selectedRegionLabel ? (
                            <div className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                              <CountryFlag
                                code={selectedRegionCountryCode}
                                className="h-4 w-6 rounded-[0.2rem] border border-border/65 shadow-[var(--panel-shadow)]"
                                fallbackClassName="h-4 w-6"
                              />
                              <span>{selectedRegionLabel}</span>
                            </div>
                          ) : (
                            <div className="mt-2 text-sm font-semibold text-foreground">—</div>
                          )}
                        </div>
                        <div className="rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                            {t("dashboard.transportProfile")}
                          </div>
                          <div className="mt-2 text-sm font-semibold text-foreground">
                            {selectedProxy ? selectedTransportSignature : "—"}
                          </div>
                        </div>
                        <div className="rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                            {t("dashboard.securityEnvelope")}
                          </div>
                          <div className="mt-2 text-sm font-semibold text-foreground">
                            {selectedProxy ? selectedSecurityEnvelope : "—"}
                          </div>
                        </div>
                        <div className="rounded-[1.25rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3">
                          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                            {t("dashboard.profileCollection")}
                          </div>
                          <div className="mt-2 text-sm font-semibold text-foreground">
                            {selectedCollectionLabel}
                          </div>
                        </div>
                      </div>

                      <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.06fr)_minmax(0,0.94fr)] 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                        <div className="rounded-[1.45rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 p-4 shadow-[var(--panel-shadow)]">
                          <div className="mb-3 flex items-start justify-between gap-4">
                            <div>
                              <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                                {t("dashboard.smartExplainTitle")}
                              </div>
                              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                                {selectedProxy
                                  ? t(selectedRouteExplanation?.summaryKey ?? "dashboard.smartRouteReasonFallback")
                                  : t("dashboard.selectedRouteDesc")}
                              </p>
                            </div>
                            <div className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-cyan)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_10%,white)] text-[var(--color-neon-cyan)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_16%,black)]">
                              <Sparkles size={16} />
                            </div>
                          </div>

                          {selectedProxy && selectedExplainSignals.length ? (
                            <div className="flex flex-wrap gap-2">
                              {selectedExplainSignals.map((signal) => (
                                <SmartSignalChip
                                  key={`selected-${signal.kind}`}
                                  signal={signal}
                                  proxy={selectedProxy}
                                  latencyBadge={selectedLatencyBadge}
                                  translate={(key, options) =>
                                    String(t(key as never, options as never))
                                  }
                                />
                              ))}
                            </div>
                          ) : (
                            <div className="rounded-[1.15rem] border border-dashed border-border/70 bg-[color:var(--panel-surface)]/78 px-4 py-4 text-sm text-muted-foreground">
                              {t("dashboard.smartExplainEmpty")}
                            </div>
                          )}
                        </div>

                        <div className="rounded-[1.45rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 p-4 shadow-[var(--panel-shadow)]">
                          <div className="mb-3 flex items-start justify-between gap-4">
                            <div>
                              <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                                {t("dashboard.routeSignatureTitle")}
                              </div>
                              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                                {t("dashboard.routeSignatureDesc")}
                              </p>
                            </div>
                            <div className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-neon-pink)_22%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_10%,white)] text-[var(--color-neon-pink)] dark:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_16%,black)]">
                              <Fingerprint size={16} />
                            </div>
                          </div>

                          <div className="grid gap-3 sm:grid-cols-2">
                            <div>
                              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                {t("dashboard.endpointPrimary")}
                              </div>
                              <div className="mt-1 text-sm font-semibold text-foreground">
                                {selectedProxy ? selectedEndpointLabel : "—"}
                              </div>
                            </div>
                            <div>
                              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                {t("dashboard.capacityLabel")}
                              </div>
                              <div className="mt-1 text-sm font-semibold text-foreground">
                                {selectedProxy ? selectedCapacityLabel : "—"}
                              </div>
                            </div>
                            <div>
                              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                {selectedRelayProxy ? t("dashboard.relayPath") : t("dashboard.routeMode")}
                              </div>
                              <div className="mt-1 text-sm font-semibold text-foreground">
                                {selectedRelayProxy ? selectedRelayProxy.name : selectedRouteModeLabel}
                              </div>
                            </div>
                            <div>
                              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                {t("dashboard.positionInProfile")}
                              </div>
                              <div className="mt-1 text-sm font-semibold text-foreground">
                                {selectedCollectionPosition != null &&
                                selectedCollectionPosition >= 0 &&
                                selectedCollection
                                  ? `${selectedCollectionPosition + 1} / ${selectedCollection.proxyCount}`
                                  : "—"}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-4">
                    <div className="rounded-[1.8rem] border border-border/60 bg-[color:var(--chrome-elevated)]/84 p-4 shadow-[var(--panel-shadow)]">
                      <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                        {t("dashboard.bestAvailable")}
                      </div>
                      <div className="mt-2 text-lg font-semibold text-foreground">
                        {bestAvailableProxy?.name ?? t("dashboard.bestRouteUnavailable")}
                      </div>
                      <div className="mt-2 text-sm leading-6 text-muted-foreground">
                        {t(bestRouteReasonKey)}
                      </div>
                      {bestAvailableProxy && bestExplainSignals.length ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {bestExplainSignals.map((signal) => (
                            <SmartSignalChip
                              key={`capsule-${signal.kind}`}
                              signal={signal}
                              proxy={bestAvailableProxy}
                              latencyBadge={bestLatencyBadge}
                              translate={(key, options) =>
                                String(t(key as never, options as never))
                              }
                            />
                          ))}
                        </div>
                      ) : null}
                    </div>

                    <div className="relative flex flex-1 flex-col overflow-hidden rounded-[1.8rem] border border-border/60 bg-[color:var(--chrome-elevated)]/84 p-4 shadow-[var(--panel-shadow)]">
                      <div aria-hidden className="pointer-events-none absolute inset-0">
                        <motion.div
                          className="absolute -right-12 top-6 h-36 w-36 rounded-full blur-3xl"
                          style={{ backgroundColor: connectedStateTheme.accent }}
                          animate={
                            connectedStatePulseAnimation
                              ? { opacity: [0.08, 0.22, 0.12], scale: [0.94, 1.08, 0.98] }
                              : { opacity: 0.08, scale: 1 }
                          }
                          transition={{
                            repeat: connectedStatePulseAnimation ? Infinity : 0,
                            duration: 3.4,
                            ease: desktopMotionEase,
                          }}
                        />
                        <motion.div
                          className="absolute -left-10 bottom-10 h-28 w-28 rounded-full blur-3xl"
                          style={{ backgroundColor: connectedStateTheme.accent }}
                          animate={
                            connectedStatePulseAnimation
                              ? { opacity: [0.04, 0.14, 0.06], scale: [1, 0.9, 1.04] }
                              : { opacity: 0.05, scale: 1 }
                          }
                          transition={{
                            repeat: connectedStatePulseAnimation ? Infinity : 0,
                            duration: 4.2,
                            ease: desktopMotionEase,
                          }}
                        />
                        <div className="absolute inset-x-8 top-0 h-px bg-[linear-gradient(90deg,transparent,color-mix(in_oklab,var(--color-neon-cyan)_24%,transparent),transparent)]" />
                      </div>

                      <div className="relative z-10 mb-4 flex items-start justify-between gap-3">
                        <div>
                          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                            {t("dashboard.selectedRoute")}
                          </div>
                          <div className="mt-2 text-sm leading-6 text-muted-foreground">
                            {selectionStateLabel}
                          </div>
                        </div>
                        <span
                          className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${connectedStateTheme.chip}`}
                        >
                          <motion.span
                            className="h-2 w-2 rounded-full"
                            style={{ backgroundColor: connectedStateTheme.accent, boxShadow: `0 0 12px ${connectedStateTheme.accent}` }}
                            animate={
                              connectedStatePulseAnimation
                                ? { opacity: [0.4, 1, 0.56], scale: [0.9, 1.14, 0.96] }
                                : { opacity: 0.72, scale: 1 }
                            }
                            transition={{
                              repeat: connectedStatePulseAnimation ? Infinity : 0,
                              duration: 1.8,
                              ease: desktopMotionEase,
                            }}
                          />
                          {currentStatusLabel}
                        </span>
                      </div>

                      <div className="relative z-10 rounded-[1.45rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-4 py-3 shadow-[var(--panel-shadow)]">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                          {t("dashboard.routeSignatureTitle")}
                        </div>
                        <div className="mt-2 text-sm font-semibold text-foreground">
                          {connectedStateSignalText}
                        </div>
                        <div className="mt-1 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                          {connectedStateTrafficLabel}
                        </div>
                      </div>

                      <div className="relative z-10 flex justify-center py-5">
                        <ConnectButton
                          status={status}
                          onConnect={handleConnect}
                          onDisconnect={handleDisconnect}
                        />
                      </div>

                      <div className="relative z-10 mt-auto grid gap-2">
                        {connectedStateMeters.map((meter, index) => (
                          <div
                            key={meter.label}
                            className="rounded-[1.2rem] border border-border/65 bg-[color:var(--panel-subtle)]/72 px-3.5 py-3 shadow-[var(--panel-shadow)]"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                {meter.label}
                              </div>
                              <div className="truncate text-[11px] font-semibold uppercase tracking-[0.14em] text-foreground">
                                {meter.value}
                              </div>
                            </div>
                            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[color:var(--field-surface)]/90">
                              <motion.div
                                className="h-full rounded-full"
                                style={{
                                  background: `linear-gradient(90deg, ${connectedStateTheme.accent}, color-mix(in oklab, ${connectedStateTheme.accent} 55%, white))`,
                                }}
                                animate={
                                  connectedStatePulseAnimation
                                    ? {
                                        width: [
                                          `${Math.max(12, meter.progress - 8)}%`,
                                          `${meter.progress}%`,
                                          `${Math.max(12, meter.progress - 4)}%`,
                                        ],
                                        opacity: [0.72, 1, 0.82],
                                      }
                                    : {
                                        width: `${meter.progress}%`,
                                        opacity: 0.88,
                                      }
                                }
                                transition={{
                                  delay: index * 0.08,
                                  repeat: connectedStatePulseAnimation ? Infinity : 0,
                                  duration: 2.4,
                                  ease: desktopMotionEase,
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

              </>
            )}
          </div>
        </section>
        <Suspense fallback={<DashboardSupportDeckFallback />}>
          <DashboardSupportDeck
            connectionDebugReport={connectionDebugReport}
            isCollectingDebugReport={isCollectingDebugReport}
            onCopyConnectionDebugReport={() => {
              void handleCopyConnectionDebugReport();
            }}
            onRefreshConnectionDebugReport={() => {
              void captureConnectionDebugReport(
                status.message ?? "Connection failed",
                status.activeId ?? null
              );
            }}
            onStealthToggle={handleStealthToggle}
            onTunModeChange={(checked) => {
              void handleTunModeChange(checked);
            }}
            status={status}
            stealthMode={stealthMode}
            trafficData={trafficData}
            tunMode={options.tunMode}
          />
        </Suspense>
      </div>
    </motion.div>
  );
}
