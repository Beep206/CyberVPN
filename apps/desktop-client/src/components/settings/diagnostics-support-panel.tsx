"use client";

import { useEffect, useState } from "react";
import { openPath, revealItemInDir } from "@tauri-apps/plugin-opener";
import { toast } from "sonner";
import {
  Activity,
  Archive,
  Bug,
  Copy,
  Download,
  FolderOpen,
  Gauge,
  Play,
  RefreshCw,
  Route,
  TerminalSquare,
  Trash2,
} from "lucide-react";

import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  clearDesktopDiagnosticsLogs,
  exportDesktopSupportBundle,
  getDesktopDiagnosticsSnapshot,
  getProfiles,
  runHelixRecoveryBenchmark,
  listenDesktopDiagnostics,
  listenHelixHealth,
  runTransportBenchmark,
  runTransportCoreComparison,
  runTransportTargetMatrixComparison,
  type DesktopDiagnosticsSnapshot,
  type DiagnosticEntry,
  type HelixRecoveryBenchmarkMode,
  type HelixRecoveryBenchmarkReport,
  type HelixContinuitySummary,
  type HelixSidecarHealth,
  type HelixSidecarTelemetry,
  type ProxyNode,
  type SupportBundleExportResult,
  type TransportBenchmarkComparisonReport,
  type TransportBenchmarkMatrixReport,
  type TransportBenchmarkMatrixTarget,
  type TransportBenchmarkReport,
} from "../../shared/api/ipc";

interface EditableMatrixTarget {
  label: string;
  host: string;
  port: string;
  path: string;
}

function formatProfileOptionLabel(profile: ProxyNode): string {
  const endpointLabel =
    profile.server && profile.port > 0 ? `${profile.server}:${profile.port}` : "endpoint";
  return `${profile.name} • ${profile.protocol.toUpperCase()} • ${endpointLabel}`;
}

const DEFAULT_MATRIX_TARGETS: EditableMatrixTarget[] = [
  { label: "Warm HTTP", host: "example.com", port: "80", path: "/" },
  {
    label: "Cloudflare 256K",
    host: "speed.cloudflare.com",
    port: "80",
    path: "/__down?bytes=262144",
  },
  {
    label: "Cloudflare 1M",
    host: "speed.cloudflare.com",
    port: "80",
    path: "/__down?bytes=1048576",
  },
];

const EXTERNAL_MATRIX_TARGETS: EditableMatrixTarget[] = [
  { label: "Warm HTTP", host: "example.com", port: "80", path: "/" },
  {
    label: "Cloudflare 512K",
    host: "speed.cloudflare.com",
    port: "80",
    path: "/__down?bytes=524288",
  },
  {
    label: "Cloudflare 2M",
    host: "speed.cloudflare.com",
    port: "80",
    path: "/__down?bytes=2097152",
  },
];

function cloneMatrixTargets(targets: EditableMatrixTarget[]): EditableMatrixTarget[] {
  return targets.map((target) => ({ ...target }));
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}

function formatCoreLabel(core?: string | null): string {
  switch (core) {
    case "helix":
      return "Helix";
    case "sing-box":
      return "Sing-box";
    case "xray":
      return "Xray";
    default:
      return core ?? "Unknown";
  }
}

function formatBytes(bytes?: number | null): string {
  const safeBytes = bytes ?? 0;
  if (safeBytes < 1024) {
    return `${safeBytes} B`;
  }

  if (safeBytes < 1024 * 1024) {
    return `${(safeBytes / 1024).toFixed(1)} KB`;
  }

  if (safeBytes < 1024 * 1024 * 1024) {
    return `${(safeBytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return `${(safeBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatLatencyMetric(value?: number | null): string {
  return value == null ? "No signal" : `${value} ms`;
}

function formatThroughputMetric(value?: number | null): string {
  return value == null ? "No signal" : `${value.toFixed(1)} kbps`;
}

function formatRatioMetric(value?: number | null): string {
  return value == null ? "No signal" : `${value.toFixed(2)}x`;
}

function percentileMetric(values: number[], percentile: number): number | null {
  if (values.length === 0) {
    return null;
  }

  const sorted = [...values].sort((left, right) => left - right);
  const index = Math.min(
    sorted.length - 1,
    Math.max(0, Math.ceil(sorted.length * percentile) - 1),
  );

  return sorted[index] ?? null;
}

function peakMetric(values: number[]): number | null {
  if (values.length === 0) {
    return null;
  }

  return Math.max(...values);
}

function formatTimestamp(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "No signal";
}

function formatBooleanMetric(value?: boolean | null): string {
  if (value == null) {
    return "No signal";
  }

  return value ? "Yes" : "No";
}

function formatNullableText(value?: string | null, fallback = "No signal"): string {
  return value ?? fallback;
}

function toneForLevel(level: string): string {
  switch (level) {
    case "error":
      return "text-[var(--color-neon-pink)]";
    case "warn":
      return "text-yellow-400";
    case "info":
      return "text-[var(--color-neon-cyan)]";
    default:
      return "text-muted-foreground";
  }
}

function formatContinuitySummary(summary?: HelixContinuitySummary | null): string {
  if (!summary) {
    return "No signal";
  }

  return [
    `grace ${summary.grace_active ? "active" : "inactive"}`,
    `route ${summary.grace_route_endpoint_ref ?? "same-route"}`,
    `remaining ${formatLatencyMetric(summary.grace_remaining_ms)}`,
    `streams ${summary.active_streams} / ${summary.pending_open_streams}`,
    `quarantine ${summary.active_route_quarantined ? formatLatencyMetric(summary.active_route_quarantine_remaining_ms) : "clear"}`,
    `entries ${summary.continuity_grace_entries}`,
    `recovers ${summary.successful_continuity_recovers}`,
    `cross-route ${summary.successful_cross_route_recovers}`,
    `failed ${summary.failed_continuity_recovers}`,
    `last ${formatLatencyMetric(summary.last_continuity_recovery_ms)}`,
    `last cross-route ${formatLatencyMetric(summary.last_cross_route_recovery_ms)}`,
  ].join(" • ");
}

function formatLiveContinuitySummary(health?: HelixSidecarHealth | null): string {
  if (!health) {
    return "No signal";
  }

  return [
    `grace ${health.continuity_grace_active ? "active" : "inactive"}`,
    `route ${health.continuity_grace_route_endpoint_ref ?? "same-route"}`,
    `remaining ${formatLatencyMetric(health.continuity_grace_remaining_ms)}`,
    `quarantine ${health.active_route_quarantined ? formatLatencyMetric(health.active_route_quarantine_remaining_ms) : "clear"}`,
    `entries ${health.active_route_continuity_grace_entries}`,
    `recovers ${health.active_route_successful_continuity_recovers}`,
    `cross-route ${health.active_route_successful_cross_route_recovers}`,
    `failed ${health.active_route_failed_continuity_recovers}`,
    `last ${formatLatencyMetric(health.active_route_last_continuity_recovery_ms)}`,
    `last cross-route ${formatLatencyMetric(health.active_route_last_cross_route_recovery_ms)}`,
  ].join(" • ");
}

function formatPayloadContinuitySummary(payload: Record<string, unknown>): string {
  const graceActive = readBooleanFromPayload(payload, "grace_active");
  return [
    `grace ${graceActive == null ? "No signal" : graceActive ? "active" : "inactive"}`,
    `route ${formatNullableText(readStringFromPayload(payload, "grace_route_endpoint_ref"), "same-route")}`,
    `remaining ${formatLatencyMetric(readNumberFromPayload(payload, "grace_remaining_ms"))}`,
    `streams ${readNumberFromPayload(payload, "active_streams") ?? "n/a"} / ${
      readNumberFromPayload(payload, "pending_open_streams") ?? "n/a"
    }`,
    `quarantine ${
      readBooleanFromPayload(payload, "active_route_quarantined")
        ? formatLatencyMetric(readNumberFromPayload(payload, "active_route_quarantine_remaining_ms"))
        : "clear"
    }`,
    `entries ${readNumberFromPayload(payload, "continuity_grace_entries") ?? "n/a"}`,
    `recovers ${readNumberFromPayload(payload, "successful_continuity_recovers") ?? "n/a"}`,
    `cross-route ${readNumberFromPayload(payload, "successful_cross_route_recovers") ?? "n/a"}`,
    `failed ${readNumberFromPayload(payload, "failed_continuity_recovers") ?? "n/a"}`,
    `last ${formatLatencyMetric(readNumberFromPayload(payload, "last_continuity_recovery_ms"))}`,
    `last cross-route ${formatLatencyMetric(readNumberFromPayload(payload, "last_cross_route_recovery_ms"))}`,
  ].join(" • ");
}

function readNumberFromPayload(payload: Record<string, unknown>, key: string): number | null {
  const value = payload[key];
  return typeof value === "number" ? value : null;
}

function readStringFromPayload(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key];
  return typeof value === "string" ? value : null;
}

function readBooleanFromPayload(payload: Record<string, unknown>, key: string): boolean | null {
  const value = payload[key];
  return typeof value === "boolean" ? value : null;
}

function readObjectFromPayload(
  payload: Record<string, unknown>,
  key: string,
): Record<string, unknown> | null {
  const value = payload[key];
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function readArrayFromPayload(
  payload: Record<string, unknown>,
  key: string,
): Record<string, unknown>[] {
  const value = payload[key];
  return Array.isArray(value)
    ? value.filter(
        (item): item is Record<string, unknown> =>
          Boolean(item) && typeof item === "object" && !Array.isArray(item),
      )
    : [];
}

function summarizeDiagnosticPayload(entry: DiagnosticEntry): string | null {
  const payload = entry.payload;
  if (entry.source !== "helix.benchmark") {
    return null;
  }

  switch (entry.message) {
    case "Transport benchmark completed": {
      const queuePressure = readObjectFromPayload(payload, "helix_queue_pressure");
      const queueDepth = queuePressure
        ? readNumberFromPayload(queuePressure, "frame_queue_depth")
        : null;
      const queuePeak = queuePressure
        ? readNumberFromPayload(queuePressure, "frame_queue_peak")
        : null;
      const rttP95 = queuePressure
        ? readNumberFromPayload(queuePressure, "recent_rtt_p95_ms")
        : null;

      return [
        `core ${formatCoreLabel(readStringFromPayload(payload, "active_core"))}`,
        `gap ${formatLatencyMetric(readNumberFromPayload(payload, "median_open_to_first_byte_gap_ms"))}`,
        `throughput ${formatThroughputMetric(readNumberFromPayload(payload, "average_throughput_kbps"))}`,
        queueDepth != null && queuePeak != null ? `queue ${queueDepth}/${queuePeak}` : null,
        rttP95 != null ? `rtt p95 ${formatLatencyMetric(rttP95)}` : null,
      ]
        .filter(Boolean)
        .join(" • ");
    }
    case "Transport core comparison completed": {
      const helixEntry = readArrayFromPayload(payload, "entries").find((item) => {
        const requestedCore = readStringFromPayload(item, "requested_core");
        const effectiveCore = readStringFromPayload(item, "effective_core");
        return requestedCore === "helix" || effectiveCore === "helix";
      });

      return [
        `baseline ${formatCoreLabel(readStringFromPayload(payload, "baseline_core"))}`,
        `runs ${readArrayFromPayload(payload, "entries").length}`,
        helixEntry
          ? `helix gap ${formatLatencyMetric(readNumberFromPayload(helixEntry, "median_open_to_first_byte_gap_ms"))}`
          : null,
        helixEntry
          ? `helix ratio ${formatRatioMetric(readNumberFromPayload(helixEntry, "relative_open_to_first_byte_gap_ratio"))}`
          : null,
      ]
        .filter(Boolean)
        .join(" • ");
    }
    case "Transport target matrix comparison completed": {
      const helixSummary = readArrayFromPayload(payload, "core_summaries").find(
        (item) => readStringFromPayload(item, "core") === "helix",
      );

      return [
        `targets ${readNumberFromPayload(payload, "target_count") ?? "n/a"}`,
        `baseline ${formatCoreLabel(readStringFromPayload(payload, "baseline_core"))}`,
        helixSummary
          ? `helix gap ${formatLatencyMetric(readNumberFromPayload(helixSummary, "median_open_to_first_byte_gap_ms"))}`
          : null,
        helixSummary
          ? `helix ratio ${formatRatioMetric(readNumberFromPayload(helixSummary, "average_relative_open_to_first_byte_gap_ratio"))}`
          : null,
      ]
        .filter(Boolean)
        .join(" • ");
    }
    case "Helix recovery benchmark completed": {
      const sameRouteRecovered = readBooleanFromPayload(payload, "same_route_recovered");
      const continuityBefore = readObjectFromPayload(payload, "continuity_before");
      const continuityAfter = readObjectFromPayload(payload, "continuity_after");

      return [
        `mode ${readStringFromPayload(payload, "mode") ?? "n/a"}`,
        `recovered ${readBooleanFromPayload(payload, "recovered") ? "yes" : "no"}`,
        `same-route ${sameRouteRecovered == null ? "n/a" : sameRouteRecovered ? "yes" : "no"}`,
        `ready ${formatLatencyMetric(readNumberFromPayload(payload, "ready_recovery_latency_ms"))}`,
        `proxy ${formatLatencyMetric(readNumberFromPayload(payload, "proxy_ready_latency_ms"))}`,
        `gap ${formatLatencyMetric(readNumberFromPayload(payload, "proxy_ready_open_to_first_byte_gap_ms"))}`,
        continuityBefore ? `before ${formatPayloadContinuitySummary(continuityBefore)}` : null,
        continuityAfter ? `after ${formatPayloadContinuitySummary(continuityAfter)}` : null,
        `post-gap ${formatLatencyMetric(readNumberFromPayload(payload, "post_recovery_median_open_to_first_byte_gap_ms"))}`,
      ]
        .filter(Boolean)
        .join(" • ");
    }
    default:
      return null;
  }
}

async function copyText(label: string, value: string) {
  try {
    await navigator.clipboard.writeText(value);
    toast.success(`${label} copied.`);
  } catch (error) {
    toast.error(`Failed to copy ${label.toLowerCase()}: ${formatError(error)}`);
  }
}

function pickProfileId(
  currentId: string,
  profiles: ProxyNode[],
  activeProfileId?: string | null,
): string {
  if (currentId && profiles.some((profile) => profile.id === currentId)) {
    return currentId;
  }

  if (activeProfileId && profiles.some((profile) => profile.id === activeProfileId)) {
    return activeProfileId;
  }

  return profiles[0]?.id ?? "";
}

export function DiagnosticsSupportPanel() {
  const [snapshot, setSnapshot] = useState<DesktopDiagnosticsSnapshot | null>(null);
  const [profiles, setProfiles] = useState<ProxyNode[]>([]);
  const [liveHelixHealth, setLiveHelixHealth] = useState<HelixSidecarHealth | null>(null);
  const [lastExport, setLastExport] = useState<SupportBundleExportResult | null>(null);
  const [lastDrillReport, setLastDrillReport] = useState<TransportBenchmarkReport | null>(null);
  const [lastComparisonReport, setLastComparisonReport] =
    useState<TransportBenchmarkComparisonReport | null>(null);
  const [lastMatrixReport, setLastMatrixReport] =
    useState<TransportBenchmarkMatrixReport | null>(null);
  const [lastRecoveryReport, setLastRecoveryReport] =
    useState<HelixRecoveryBenchmarkReport | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [isRunningDrill, setIsRunningDrill] = useState(false);
  const [isRunningMatrix, setIsRunningMatrix] = useState(false);
  const [isRunningRecovery, setIsRunningRecovery] = useState(false);
  const [isRunningPerfCapture, setIsRunningPerfCapture] = useState(false);
  const [perfCaptureProfileId, setPerfCaptureProfileId] = useState("");
  const [matrixProfileId, setMatrixProfileId] = useState("");
  const [recoveryProfileId, setRecoveryProfileId] = useState("");
  const [recoveryMode, setRecoveryMode] =
    useState<HelixRecoveryBenchmarkMode>("failover");
  const [recoveryTimeoutMs, setRecoveryTimeoutMs] = useState("8000");
  const [matrixTargets, setMatrixTargets] =
    useState<EditableMatrixTarget[]>(() => cloneMatrixTargets(DEFAULT_MATRIX_TARGETS));
  const [drillTargetHost, setDrillTargetHost] = useState("example.com");
  const [drillTargetPort, setDrillTargetPort] = useState("80");
  const [drillTargetPath, setDrillTargetPath] = useState("/");
  const [drillAttempts, setDrillAttempts] = useState("5");
  const [drillDownloadLimit, setDrillDownloadLimit] = useState("262144");
  const [drillConnectTimeout, setDrillConnectTimeout] = useState("6000");

  const refreshSnapshot = async (showToast = false) => {
    setIsRefreshing(true);
    try {
      const [nextSnapshot, profileInventory] = await Promise.all([
        getDesktopDiagnosticsSnapshot(),
        getProfiles(),
      ]);
      setSnapshot(nextSnapshot);
      setProfiles(profileInventory);
      setLiveHelixHealth(nextSnapshot.helix.live_health ?? null);
      setPerfCaptureProfileId((current) =>
        pickProfileId(current, profileInventory, nextSnapshot.active_profile_id),
      );
      setMatrixProfileId((current) =>
        pickProfileId(current, profileInventory, nextSnapshot.active_profile_id),
      );
      setRecoveryProfileId((current) =>
        pickProfileId(current, profileInventory, nextSnapshot.active_profile_id),
      );
      if (showToast) {
        toast.success("Diagnostics snapshot refreshed.");
      }
    } catch (error) {
      toast.error(`Failed to refresh diagnostics: ${formatError(error)}`);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    let unlistenDiagnostics: (() => void) | null = null;
    let unlistenHelixHealth: (() => void) | null = null;

    void refreshSnapshot(false);

    const setupListeners = async () => {
      unlistenDiagnostics = await listenDesktopDiagnostics((entry) => {
        setSnapshot((current) => {
          if (!current) {
            return current;
          }

          const nextEntries = [entry, ...current.recent_entries].slice(0, 120);
          return {
            ...current,
            recent_entries: nextEntries,
          };
        });
      });

      unlistenHelixHealth = await listenHelixHealth((health) => {
        setLiveHelixHealth(health);
        setSnapshot((current) => {
          if (!current) {
            return current;
          }

          return {
            ...current,
            helix: {
              ...current.helix,
              live_health: health,
            },
          };
        });
      });
    };

    void setupListeners();

    return () => {
      if (unlistenDiagnostics) {
        void unlistenDiagnostics();
      }
      if (unlistenHelixHealth) {
        void unlistenHelixHealth();
      }
    };
  }, []);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const result = await exportDesktopSupportBundle();
      setLastExport(result);
      toast.success("Support bundle exported.");
    } catch (error) {
      toast.error(`Support bundle export failed: ${formatError(error)}`);
    } finally {
      setIsExporting(false);
    }
  };

  const handleClearLogs = async () => {
    setIsClearing(true);
    try {
      await clearDesktopDiagnosticsLogs();
      await refreshSnapshot(false);
      toast.success("Desktop diagnostics logs cleared.");
    } catch (error) {
      toast.error(`Failed to clear diagnostics logs: ${formatError(error)}`);
    } finally {
      setIsClearing(false);
    }
  };

  const handleCopySnapshot = async () => {
    if (!snapshot) {
      toast.error("Diagnostics snapshot is not loaded yet.");
      return;
    }

    await copyText("Diagnostics snapshot", JSON.stringify(snapshot, null, 2));
  };

  const handleCopyEntries = async () => {
    if (!snapshot) {
      toast.error("Diagnostics entries are not loaded yet.");
      return;
    }

    const payload = snapshot.recent_entries
      .map((entry) => `[${entry.timestamp}] [${entry.level}] [${entry.source}] ${entry.message}`)
      .join("\n");

    await copyText("Diagnostics timeline", payload);
  };

  const handleCopyCoreTail = async (label: string, lines: string[]) => {
    await copyText(label, lines.join("\n"));
  };

  const handleOpenPath = async (label: string, path: string) => {
    try {
      await openPath(path);
      toast.success(`${label} opened.`);
    } catch (error) {
      toast.error(`Failed to open ${label.toLowerCase()}: ${formatError(error)}`);
    }
  };

  const handleRevealBundle = async (path: string) => {
    try {
      await revealItemInDir(path);
      toast.success("Support bundle revealed in explorer.");
    } catch (error) {
      toast.error(`Failed to reveal support bundle: ${formatError(error)}`);
    }
  };

  const applyDrillPreset = (
    targetHost: string,
    targetPort: string,
    targetPath: string,
    attempts: string,
    downloadLimit: string,
    connectTimeout: string,
  ) => {
    setDrillTargetHost(targetHost);
    setDrillTargetPort(targetPort);
    setDrillTargetPath(targetPath);
    setDrillAttempts(attempts);
    setDrillDownloadLimit(downloadLimit);
    setDrillConnectTimeout(connectTimeout);
  };

  const handleRunHelixDrill = async () => {
    const proxyUrl = snapshot?.helix.proxy_url ?? null;
    if (!proxyUrl) {
      toast.error("Prepare a Helix runtime first so the drill has a local SOCKS5 target.");
      return;
    }

    setIsRunningDrill(true);
    try {
      const benchmarkRequest = buildBenchmarkRequest();
      const report = await runTransportBenchmark({
        proxy_url: proxyUrl,
        ...benchmarkRequest,
      });
      setLastDrillReport(report);
      toast.success("Helix performance drill completed.");
      await refreshSnapshot(false);
    } catch (error) {
      toast.error(`Helix performance drill failed: ${formatError(error)}`);
    } finally {
      setIsRunningDrill(false);
    }
  };

  const handleCopyDrillReport = async () => {
    if (!lastDrillReport) {
      toast.error("No Helix performance drill report is available yet.");
      return;
    }

    await copyText("Helix performance drill report", JSON.stringify(lastDrillReport, null, 2));
  };

  const buildBenchmarkRequest = () => ({
    target_host: drillTargetHost.trim() || "example.com",
    target_port: Number.parseInt(drillTargetPort, 10),
    target_path: drillTargetPath.trim() || "/",
    attempts: Number.parseInt(drillAttempts, 10),
    download_bytes_limit: Number.parseInt(drillDownloadLimit, 10),
    connect_timeout_ms: Number.parseInt(drillConnectTimeout, 10),
  });

  const updateMatrixTarget = (
    index: number,
    field: keyof EditableMatrixTarget,
    value: string,
  ) => {
    setMatrixTargets((current) =>
      current.map((target, currentIndex) =>
        currentIndex === index ? { ...target, [field]: value } : target,
      ),
    );
  };

  const applyMatrixPreset = (targets: EditableMatrixTarget[]) => {
    setMatrixTargets(cloneMatrixTargets(targets));
  };

  const buildMatrixTargets = (): TransportBenchmarkMatrixTarget[] => {
    return matrixTargets.map((target, index) => {
      const host = target.host.trim();
      const port = Number.parseInt(target.port, 10);
      if (!host) {
        throw new Error(`Matrix target ${index + 1} is missing a host.`);
      }
      if (!Number.isFinite(port) || port <= 0 || port > 65535) {
        throw new Error(`Matrix target ${index + 1} must use a valid TCP port.`);
      }

      return {
        label: target.label.trim() || `Target ${index + 1}`,
        host,
        port,
        path: target.path.trim() || "/",
      };
    });
  };

  const handleRunTargetMatrix = async () => {
    if (!matrixProfileId) {
      toast.error("Pick a saved profile before running the target matrix.");
      return;
    }

    setIsRunningMatrix(true);
    try {
      const report = await runTransportTargetMatrixComparison({
        profile_id: matrixProfileId,
        cores: ["helix", "sing-box", "xray"],
        targets: buildMatrixTargets(),
        benchmark: buildBenchmarkRequest(),
      });
      setLastMatrixReport(report);
      toast.success("Helix target matrix comparison completed.");
      await refreshSnapshot(false);
    } catch (error) {
      toast.error(`Helix target matrix failed: ${formatError(error)}`);
    } finally {
      setIsRunningMatrix(false);
    }
  };

  const handleCopyMatrixReport = async () => {
    if (!lastMatrixReport) {
      toast.error("No Helix target matrix report is available yet.");
      return;
    }

    await copyText("Helix target matrix report", JSON.stringify(lastMatrixReport, null, 2));
  };

  const handleRunRecoveryBenchmark = async () => {
    if (!recoveryProfileId) {
      toast.error("Pick a saved profile before running the recovery drill.");
      return;
    }

    const recoveryTimeout = Number.parseInt(recoveryTimeoutMs, 10);
    if (!Number.isFinite(recoveryTimeout) || recoveryTimeout < 1000 || recoveryTimeout > 60000) {
      toast.error("Recovery timeout must be between 1000 and 60000 ms.");
      return;
    }

    setIsRunningRecovery(true);
    try {
      const report = await runHelixRecoveryBenchmark({
        profile_id: recoveryProfileId,
        mode: recoveryMode,
        benchmark: buildBenchmarkRequest(),
        recovery_timeout_ms: recoveryTimeout,
      });
      setLastRecoveryReport(report);
      toast.success(`Helix ${recoveryMode} recovery drill completed.`);
      await refreshSnapshot(false);
    } catch (error) {
      toast.error(`Helix recovery drill failed: ${formatError(error)}`);
    } finally {
      setIsRunningRecovery(false);
    }
  };

  const handleCopyRecoveryReport = async () => {
    if (!lastRecoveryReport) {
      toast.error("No Helix recovery report is available yet.");
      return;
    }

    await copyText("Helix recovery report", JSON.stringify(lastRecoveryReport, null, 2));
  };

  const handleCopyHelixTelemetry = async () => {
    if (!snapshot?.helix.live_telemetry) {
      toast.error("Helix live telemetry is not available yet.");
      return;
    }

    await copyText("Helix telemetry", JSON.stringify(snapshot.helix.live_telemetry, null, 2));
  };

  const handleRunFullPerfCapture = async () => {
    const proxyUrl = snapshot?.helix.proxy_url ?? null;
    if (!proxyUrl) {
      toast.error("Prepare a Helix runtime first so the capture can use the local SOCKS5 path.");
      return;
    }

    if (!perfCaptureProfileId) {
      toast.error("Pick a saved profile before running the full performance capture.");
      return;
    }

    const benchmarkRequest = buildBenchmarkRequest();
    setIsRunningPerfCapture(true);
    try {
      const drillReport = await runTransportBenchmark({
        proxy_url: proxyUrl,
        ...benchmarkRequest,
      });
      setLastDrillReport(drillReport);

      const comparisonReport = await runTransportCoreComparison({
        profile_id: perfCaptureProfileId,
        cores: ["helix", "sing-box", "xray"],
        benchmark: benchmarkRequest,
      });
      setLastComparisonReport(comparisonReport);

      const bundleResult = await exportDesktopSupportBundle();
      setLastExport(bundleResult);
      await refreshSnapshot(false);
      toast.success("Full Helix performance capture completed.");
    } catch (error) {
      toast.error(`Full Helix performance capture failed: ${formatError(error)}`);
    } finally {
      setIsRunningPerfCapture(false);
    }
  };

  const recentEntries = snapshot?.recent_entries ?? [];
  const coreLogTail = snapshot?.core_log_tail ?? [];
  const helixLogTail = snapshot?.helix_log_tail ?? [];
  const helixHealth = liveHelixHealth ?? snapshot?.helix.live_health ?? null;
  const helixTelemetry: HelixSidecarTelemetry | null = snapshot?.helix.live_telemetry ?? null;
  const selectedPerfProfile =
    profiles.find((profile) => profile.id === perfCaptureProfileId) ?? null;
  const selectedMatrixProfile =
    profiles.find((profile) => profile.id === matrixProfileId) ?? null;
  const selectedRecoveryProfile =
    profiles.find((profile) => profile.id === recoveryProfileId) ?? null;
  const helixComparisonEntry =
    lastComparisonReport?.entries.find(
      (entry) => entry.effective_core === "helix" || entry.requested_core === "helix"
    ) ?? null;
  const lastDrillQueuePressure =
    lastDrillReport?.helix_queue_pressure ??
    helixComparisonEntry?.benchmark?.helix_queue_pressure ??
    null;
  const postRecoveryQueuePressure =
    lastRecoveryReport?.post_recovery_benchmark?.helix_queue_pressure ?? null;
  const helixTelemetryRttP50 = percentileMetric(helixTelemetry?.recent_rtt_ms ?? [], 0.5);
  const helixTelemetryRttP95 = percentileMetric(helixTelemetry?.recent_rtt_ms ?? [], 0.95);
  const helixTelemetryPeakFrameQueue = peakMetric(
    helixTelemetry?.recent_streams.map((stream) => stream.peak_frame_queue_depth) ?? [],
  );
  const helixTelemetryPeakInboundQueue = peakMetric(
    helixTelemetry?.recent_streams.map((stream) => stream.peak_inbound_queue_depth) ?? [],
  );

  return (
    <div className="flex flex-col gap-5 rounded-xl border border-border/50 bg-black/40 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-3 text-lg font-semibold text-[var(--color-neon-cyan)]">
            <Bug size={24} />
            <h2>Diagnostics &amp; Support</h2>
          </div>
          <p className="max-w-3xl text-sm text-muted-foreground">
            Persistent desktop diagnostics, live Helix runtime health, raw core log tails, and
            one-click support bundle export for performance tuning and bug hunts.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => void refreshSnapshot(true)}
            disabled={isRefreshing}
          >
            <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
            {isRefreshing ? "Refreshing..." : "Refresh Snapshot"}
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => void handleCopySnapshot()}
            disabled={!snapshot}
          >
            <Copy size={16} />
            Copy Snapshot JSON
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => void handleClearLogs()}
            disabled={isClearing}
          >
            <Trash2 size={16} />
            {isClearing ? "Clearing..." : "Clear Logs"}
          </Button>
          <Button
            onClick={() => void handleExport()}
            disabled={isExporting}
            className="gap-2 bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80"
          >
            <Download size={16} />
            {isExporting ? "Exporting..." : "Export Support Bundle"}
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => {
              if (snapshot) {
                void handleOpenPath("Diagnostics folder", snapshot.diagnostics_dir);
              }
            }}
            disabled={!snapshot}
          >
            <FolderOpen size={16} />
            Open Logs Folder
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => {
              if (snapshot) {
                void handleOpenPath("Support bundles folder", snapshot.support_bundle_dir);
              }
            }}
            disabled={!snapshot}
          >
            <Archive size={16} />
            Open Bundles Folder
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-lg border border-border/40 bg-black/30 p-4">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Desktop Snapshot
          </div>
          <div className="mt-2 text-sm text-foreground">
            {snapshot ? `${snapshot.app_name} ${snapshot.app_version}` : "Loading..."}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {snapshot?.platform ?? "Unknown platform"}
          </div>
        </div>
        <div className="rounded-lg border border-border/40 bg-black/30 p-4">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Active Connection
          </div>
          <div className="mt-2 text-sm text-foreground">
            {snapshot ? snapshot.connection_status.status : "Loading..."}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {snapshot ? formatCoreLabel(snapshot.connection_status.activeCore) : "Waiting..."}
          </div>
        </div>
        <div className="rounded-lg border border-border/40 bg-black/30 p-4">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Inventory
          </div>
          <div className="mt-2 text-sm text-foreground">
            {snapshot
              ? `${snapshot.profile_count} profiles, ${snapshot.subscription_count} subscriptions`
              : "Loading..."}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {snapshot ? `${snapshot.routing_rule_count} routing rules` : "Waiting..."}
          </div>
        </div>
        <div className="rounded-lg border border-border/40 bg-black/30 p-4">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Support Bundle
          </div>
          <div className="mt-2 text-sm text-foreground">
            {lastExport ? "Ready" : "Not exported yet"}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {lastExport ? `${lastExport.event_count} recent events packed` : "ZIP includes logs + snapshot"}
          </div>
        </div>
        <div className="rounded-lg border border-border/40 bg-black/30 p-4">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Startup Recovery
          </div>
          <div className="mt-2 text-sm text-foreground">
            {snapshot
              ? snapshot.lifecycle.previous_unclean_shutdown_detected
                ? "Recovered after unclean exit"
                : "Clean startup"
              : "Loading..."}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {snapshot
              ? snapshot.lifecycle.hidden_launch_requested
                ? "Hidden launch requested"
                : "Visible launch"
              : "Waiting..."}
          </div>
        </div>
      </div>

      {snapshot ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="rounded-xl border border-border/40 bg-black/30 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
              <Activity size={18} />
              Connection Snapshot
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Local IP
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {snapshot.local_ip ?? "Unavailable"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Proxy URL
                </div>
                <div className="mt-1 break-all text-sm text-foreground">
                  {snapshot.connection_status.proxyUrl ?? "Not active"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Active Profile
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {snapshot.active_profile_id ?? "None"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Launch Mode
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {snapshot.lifecycle.hidden_launch_requested ? "Hidden" : "Visible"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Local SOCKS Port
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {snapshot.local_socks_port ?? "Default"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Previous Exit
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {snapshot.lifecycle.previous_exit_kind
                    ? `${snapshot.lifecycle.previous_exit_kind} at ${formatTimestamp(
                        snapshot.lifecycle.previous_exit_at,
                      )}`
                    : "No prior exit signal"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Smart Connect
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {snapshot.smart_connect_enabled ? "Enabled" : "Disabled"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  LAN / Split Tunnel
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {snapshot.allow_lan ? "LAN on" : "LAN off"}, {snapshot.split_tunneling_app_count} apps
                </div>
              </div>
              <div className="md:col-span-2">
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Startup Recovery Detail
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {snapshot.lifecycle.previous_unclean_shutdown_detected
                    ? `Recovered previous run ${snapshot.lifecycle.previous_run_id ?? "unknown"}; proxy cleanup ${
                        snapshot.lifecycle.system_proxy_cleanup_succeeded ? "succeeded" : "attempted"
                      }.`
                    : "No unclean previous desktop shutdown detected."}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-border/40 bg-black/30 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
              <Archive size={18} />
              Support Workflow
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Diagnostics Dir
                </div>
                <div className="mt-1 break-all text-sm text-foreground">
                  {snapshot.diagnostics_dir}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Support Bundles
                </div>
                <div className="mt-1 break-all text-sm text-foreground">
                  {snapshot.support_bundle_dir}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Last Benchmark
                </div>
                <div className="mt-1 break-all text-sm text-foreground">
                  {snapshot.last_benchmark_run_id ?? "No benchmark yet"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Last Comparison
                </div>
                <div className="mt-1 break-all text-sm text-foreground">
                  {snapshot.last_comparison_run_id ?? "No comparison yet"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Last Matrix
                </div>
                <div className="mt-1 break-all text-sm text-foreground">
                  {snapshot.last_matrix_run_id ?? "No matrix yet"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Last Recovery
                </div>
                <div className="mt-1 break-all text-sm text-foreground">
                  {snapshot.last_recovery_run_id ?? "No recovery drill yet"}
                </div>
              </div>
            </div>

            {lastExport ? (
              <div className="mt-4 rounded-lg border border-[var(--color-matrix-green)]/30 bg-[rgba(0,255,136,0.06)] p-4">
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Last Export
                </div>
                <div className="mt-1 break-all font-mono text-sm text-[var(--color-matrix-green)]">
                  {lastExport.archive_path}
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2"
                    onClick={() => void copyText("Support bundle path", lastExport.archive_path)}
                  >
                    <Copy size={14} />
                    Copy Path
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2"
                    onClick={() => void handleRevealBundle(lastExport.archive_path)}
                  >
                    <FolderOpen size={14} />
                    Reveal
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="rounded-xl border border-border/40 bg-black/30 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
              <Gauge size={18} />
              Helix Performance Drill
            </div>
            <p className="max-w-3xl text-sm text-muted-foreground">
              Runs a focused Helix-only benchmark through the prepared local SOCKS5 path so we can
              tune route quality, connect time, first-byte latency, and throughput with real lab
              evidence.
            </p>
          </div>
          <div className="rounded-full border border-border/40 px-3 py-1 text-xs uppercase tracking-[0.15em] text-muted-foreground">
            Proxy {snapshot?.helix.proxy_url ?? "not ready"}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => applyDrillPreset("example.com", "80", "/", "3", "131072", "4000")}
          >
            Quick Warmup
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => applyDrillPreset("example.com", "80", "/", "7", "131072", "5000")}
          >
            Latency Focus
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              applyDrillPreset(
                "speed.cloudflare.com",
                "80",
                "/__down?bytes=1000000",
                "5",
                "524288",
                "7000",
              )
            }
          >
            Throughput Focus
          </Button>
        </div>

        <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="rounded-lg border border-border/40 bg-black/20 p-4 text-sm text-muted-foreground">
            `Full Helix Perf Capture` runs three steps back-to-back:
            Helix-only drill, `Helix vs Sing-box vs Xray` comparison, and support bundle export.
            Use it when you want one package I can use to tune speed, route policy, and runtime stability.
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
              Capture Profile
            </label>
            <select
              value={perfCaptureProfileId}
              onChange={(event) => setPerfCaptureProfileId(event.target.value)}
              className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm text-foreground outline-none transition-colors focus:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              disabled={profiles.length === 0}
            >
              {profiles.length === 0 ? (
                <option value="">No saved profiles</option>
              ) : null}
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {formatProfileOptionLabel(profile)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
              Target Host
            </label>
            <Input
              value={drillTargetHost}
              onChange={(event) => setDrillTargetHost(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
              Target Port
            </label>
            <Input
              value={drillTargetPort}
              onChange={(event) => setDrillTargetPort(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
              Target Path
            </label>
            <Input
              value={drillTargetPath}
              onChange={(event) => setDrillTargetPath(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
              Attempts
            </label>
            <Input
              value={drillAttempts}
              onChange={(event) => setDrillAttempts(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
              Download Limit
            </label>
            <Input
              value={drillDownloadLimit}
              onChange={(event) => setDrillDownloadLimit(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
              Connect Timeout
            </label>
            <Input
              value={drillConnectTimeout}
              onChange={(event) => setDrillConnectTimeout(event.target.value)}
            />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            className="gap-2 bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80"
            onClick={() => void handleRunHelixDrill()}
            disabled={isRunningDrill || !snapshot?.helix.proxy_url}
          >
            <Play size={16} />
            {isRunningDrill ? "Running Drill..." : "Run Helix Drill"}
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => void handleCopyDrillReport()}
            disabled={!lastDrillReport}
          >
            <Copy size={16} />
            Copy Drill JSON
          </Button>
          <Button
            variant="outline"
            className="gap-2 border-[var(--color-matrix-green)]/40 text-[var(--color-matrix-green)] hover:bg-[rgba(0,255,136,0.08)]"
            onClick={() => void handleRunFullPerfCapture()}
            disabled={isRunningPerfCapture || !snapshot?.helix.proxy_url || !perfCaptureProfileId}
          >
            <Gauge size={16} />
            {isRunningPerfCapture ? "Capturing Perf Bundle..." : "Run Full Helix Perf Capture"}
          </Button>
        </div>

        {lastComparisonReport ? (
          <div className="mt-4 rounded-xl border border-[var(--color-matrix-green)]/30 bg-[rgba(0,255,136,0.05)] p-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Comparison Run
                </div>
                <div className="mt-1 break-all font-mono text-sm text-foreground">
                  {lastComparisonReport.run_id}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Baseline Core
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatCoreLabel(lastComparisonReport.baseline_core)}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Profile
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {selectedPerfProfile?.name ?? lastComparisonReport.profile_id}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Compared Cores
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {lastComparisonReport.entries.length}
                </div>
              </div>
            </div>
            <div className="mt-3 text-sm text-muted-foreground">
              This report is also embedded into the exported support bundle, so one capture gives
              me both live Helix drill data and cross-core comparison evidence.
            </div>
            <div className="mt-4 grid gap-3 xl:grid-cols-3">
              {lastComparisonReport.entries.map((entry) => (
                <div
                  key={`comparison-${entry.requested_core}`}
                  className="rounded-lg border border-border/30 bg-black/20 p-4"
                >
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    {formatCoreLabel(entry.effective_core ?? entry.requested_core)}
                  </div>
                  <div className="mt-3 grid gap-2 text-sm text-foreground">
                    <div>
                      Median Gap:{" "}
                      {formatLatencyMetric(entry.benchmark?.median_open_to_first_byte_gap_ms)}
                    </div>
                    <div>
                      Gap vs Baseline:{" "}
                      {formatRatioMetric(entry.relative_open_to_first_byte_gap_ratio)}
                    </div>
                    <div>
                      Queue Peak:{" "}
                      {entry.benchmark?.helix_queue_pressure
                        ? `${entry.benchmark.helix_queue_pressure.frame_queue_depth} / ${entry.benchmark.helix_queue_pressure.frame_queue_peak}`
                        : "No signal"}
                    </div>
                    <div>
                      RTT p50 / p95:{" "}
                      {entry.benchmark?.helix_queue_pressure
                        ? `${formatLatencyMetric(entry.benchmark.helix_queue_pressure.recent_rtt_p50_ms)} / ${formatLatencyMetric(entry.benchmark.helix_queue_pressure.recent_rtt_p95_ms)}`
                        : "No signal"}
                    </div>
                    <div>
                      Continuity:{" "}
                      {entry.benchmark?.helix_continuity
                        ? formatContinuitySummary(entry.benchmark.helix_continuity)
                        : "No signal"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {lastDrillReport ? (
          <div className="mt-4 rounded-xl border border-border/40 bg-black/20 p-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Run Id
                </div>
                <div className="mt-1 break-all font-mono text-sm text-foreground">
                  {lastDrillReport.run_id}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Median Connect
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatLatencyMetric(lastDrillReport.median_connect_latency_ms)}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Median First Byte
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatLatencyMetric(lastDrillReport.median_first_byte_latency_ms)}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Throughput
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatThroughputMetric(lastDrillReport.average_throughput_kbps)}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Median Gap
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatLatencyMetric(lastDrillReport.median_open_to_first_byte_gap_ms)}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  P95 Gap
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatLatencyMetric(lastDrillReport.p95_open_to_first_byte_gap_ms)}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Successes
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {lastDrillReport.successes}/{lastDrillReport.attempts}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Proxy URL
                </div>
                <div className="mt-1 break-all text-sm text-foreground">
                  {lastDrillReport.proxy_url}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Bytes Read
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatBytes(lastDrillReport.bytes_read_total)}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Bytes Written
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatBytes(lastDrillReport.bytes_written_total)}
                </div>
              </div>
            </div>
            {lastDrillQueuePressure ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Queue Depth / Peak
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {lastDrillQueuePressure.frame_queue_depth} / {lastDrillQueuePressure.frame_queue_peak}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    RTT p50 / p95
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatLatencyMetric(lastDrillQueuePressure.recent_rtt_p50_ms)} /{" "}
                    {formatLatencyMetric(lastDrillQueuePressure.recent_rtt_p95_ms)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Continuity
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatContinuitySummary(lastDrillReport.helix_continuity)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Active / Pending
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {lastDrillQueuePressure.active_streams} / {lastDrillQueuePressure.pending_open_streams}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Stream Queue Peaks
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    Frame {lastDrillQueuePressure.recent_stream_peak_frame_queue_depth ?? "n/a"} / Inbound{" "}
                    {lastDrillQueuePressure.recent_stream_peak_inbound_queue_depth ?? "n/a"}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="mt-4 rounded-lg border border-border/40 bg-black/20 p-4 text-sm text-muted-foreground">
            Run a Helix drill to capture a focused performance report you can send back for route
            tuning and session optimization.
          </div>
        )}
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <div className="rounded-xl border border-border/40 bg-black/30 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
                <Route size={18} />
                Helix Recovery Drill
              </div>
              <p className="text-sm text-muted-foreground">
                Forces a controlled route failover or reconnect cycle, then measures how quickly
                Helix becomes ready again on the main desktop path.
              </p>
            </div>
            <div className="rounded-full border border-border/40 px-3 py-1 text-xs uppercase tracking-[0.15em] text-muted-foreground">
              Uses the same benchmark target as the drill above
            </div>
          </div>

          <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_160px_160px]">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Recovery Profile
              </label>
              <select
                value={recoveryProfileId}
                onChange={(event) => setRecoveryProfileId(event.target.value)}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm text-foreground outline-none transition-colors focus:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                disabled={profiles.length === 0}
              >
                {profiles.length === 0 ? <option value="">No saved profiles</option> : null}
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {formatProfileOptionLabel(profile)}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Mode
              </label>
              <select
                value={recoveryMode}
                onChange={(event) =>
                  setRecoveryMode(event.target.value as HelixRecoveryBenchmarkMode)
                }
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm text-foreground outline-none transition-colors focus:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <option value="failover">Failover</option>
                <option value="reconnect">Reconnect</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Timeout (ms)
              </label>
              <Input
                value={recoveryTimeoutMs}
                onChange={(event) => setRecoveryTimeoutMs(event.target.value)}
                inputMode="numeric"
              />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              className="gap-2 bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80"
              onClick={() => void handleRunRecoveryBenchmark()}
              disabled={isRunningRecovery || !recoveryProfileId}
            >
              <Play size={16} />
              {isRunningRecovery ? "Running Recovery Drill..." : "Run Recovery Drill"}
            </Button>
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => void handleCopyRecoveryReport()}
              disabled={!lastRecoveryReport}
            >
              <Copy size={16} />
              Copy Recovery JSON
            </Button>
          </div>

          {lastRecoveryReport ? (
            <div className="mt-4 rounded-xl border border-border/40 bg-black/20 p-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Run Id
                  </div>
                  <div className="mt-1 break-all font-mono text-sm text-foreground">
                    {lastRecoveryReport.run_id}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Mode
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {lastRecoveryReport.mode}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Profile
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {selectedRecoveryProfile?.name ?? lastRecoveryReport.profile_id}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Route Before
                  </div>
                  <div className="mt-1 break-all text-sm text-foreground">
                    {lastRecoveryReport.route_before ?? "No signal"}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Route After
                  </div>
                  <div className="mt-1 break-all text-sm text-foreground">
                    {lastRecoveryReport.route_after ?? "No signal"}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Recovered
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {lastRecoveryReport.recovered ? "Yes" : "No"}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Ready Recovery
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatLatencyMetric(lastRecoveryReport.ready_recovery_latency_ms)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Proxy Ready
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatLatencyMetric(lastRecoveryReport.proxy_ready_latency_ms)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Proxy Gap
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatLatencyMetric(lastRecoveryReport.proxy_ready_open_to_first_byte_gap_ms)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Action Result
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {lastRecoveryReport.action?.success ? "Action succeeded" : "Action degraded"}
                  </div>
                </div>
              </div>

              <div className="mt-4 rounded-lg border border-border/30 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Continuity Snapshot
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Same Route Recovered
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatBooleanMetric(lastRecoveryReport.same_route_recovered)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Continuity Before
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatContinuitySummary(lastRecoveryReport.continuity_before)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Continuity After
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatContinuitySummary(lastRecoveryReport.continuity_after)}
                    </div>
                  </div>
                </div>
              </div>

              {lastRecoveryReport.proxy_ready_measurement || lastRecoveryReport.proxy_ready_probe ? (
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Proxy Probe Mode
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {lastRecoveryReport.proxy_ready_measurement ?? "No signal"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Probe Connect
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatLatencyMetric(
                        lastRecoveryReport.proxy_ready_probe?.connect_latency_ms,
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Probe First Byte
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatLatencyMetric(
                        lastRecoveryReport.proxy_ready_probe?.first_byte_latency_ms,
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Probe Throughput
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatThroughputMetric(
                        lastRecoveryReport.proxy_ready_probe?.throughput_kbps,
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Probe Bytes
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatBytes(lastRecoveryReport.proxy_ready_probe?.bytes_read)}
                    </div>
                  </div>
                </div>
              ) : null}

              {lastRecoveryReport.post_recovery_benchmark ? (
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Post-Recovery Connect
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatLatencyMetric(
                        lastRecoveryReport.post_recovery_benchmark.median_connect_latency_ms,
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Post-Recovery First Byte
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatLatencyMetric(
                        lastRecoveryReport.post_recovery_benchmark.median_first_byte_latency_ms,
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Post-Recovery Gap
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatLatencyMetric(
                        lastRecoveryReport.post_recovery_benchmark.median_open_to_first_byte_gap_ms,
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Post-Recovery Throughput
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatThroughputMetric(
                        lastRecoveryReport.post_recovery_benchmark.average_throughput_kbps,
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Generated
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatTimestamp(lastRecoveryReport.generated_at)}
                    </div>
                  </div>
                </div>
              ) : null}

              {postRecoveryQueuePressure ? (
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Post-Recovery Queue
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {postRecoveryQueuePressure.frame_queue_depth} /{" "}
                      {postRecoveryQueuePressure.frame_queue_peak}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Post-Recovery RTT
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {formatLatencyMetric(postRecoveryQueuePressure.recent_rtt_p50_ms)} /{" "}
                      {formatLatencyMetric(postRecoveryQueuePressure.recent_rtt_p95_ms)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Post-Recovery Streams
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {postRecoveryQueuePressure.active_streams} /{" "}
                      {postRecoveryQueuePressure.pending_open_streams}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Max Concurrent
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {postRecoveryQueuePressure.max_concurrent_streams}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Stream Peaks
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      Frame {postRecoveryQueuePressure.recent_stream_peak_frame_queue_depth ?? "n/a"}{" "}
                      / Inbound{" "}
                      {postRecoveryQueuePressure.recent_stream_peak_inbound_queue_depth ?? "n/a"}
                    </div>
                  </div>
                </div>
              ) : null}

              {lastRecoveryReport.error ? (
                <div className="mt-4 rounded-lg border border-[var(--color-neon-pink)]/40 bg-[rgba(255,0,255,0.08)] p-3 text-sm text-[var(--color-neon-pink)]">
                  {lastRecoveryReport.error}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-border/40 bg-black/20 p-4 text-sm text-muted-foreground">
              Run a recovery drill to capture how fast Helix recovers from forced route
              degradation on the real desktop runtime.
            </div>
          )}
        </div>

        <div className="rounded-xl border border-border/40 bg-black/30 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
                <Gauge size={18} />
                Helix Target Matrix
              </div>
              <p className="text-sm text-muted-foreground">
                Runs `Helix`, `Sing-box`, and `Xray` across the same target set so we can compare
                behaviour on a shared host matrix instead of one lucky endpoint.
              </p>
            </div>
          </div>

          <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_220px]">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Matrix Profile
              </label>
              <select
                value={matrixProfileId}
                onChange={(event) => setMatrixProfileId(event.target.value)}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm text-foreground outline-none transition-colors focus:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                disabled={profiles.length === 0}
              >
                {profiles.length === 0 ? <option value="">No saved profiles</option> : null}
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {formatProfileOptionLabel(profile)}
                  </option>
                ))}
              </select>
            </div>
            <div className="rounded-lg border border-border/40 bg-black/20 p-4 text-sm text-muted-foreground">
              Reuses the same attempts, download limit, and timeout values from the Helix drill
              controls above.
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyMatrixPreset(DEFAULT_MATRIX_TARGETS)}
            >
              Lab Preset
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyMatrixPreset(EXTERNAL_MATRIX_TARGETS)}
            >
              External Preset
            </Button>
          </div>

          <div className="mt-4 space-y-3">
            {matrixTargets.map((target, index) => (
              <div
                key={`${target.label}-${index}`}
                className="rounded-lg border border-border/40 bg-black/20 p-4"
              >
                <div className="grid gap-3 xl:grid-cols-[180px_minmax(0,1fr)_120px_minmax(0,1fr)]">
                  <div className="space-y-2">
                    <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Label
                    </label>
                    <Input
                      value={target.label}
                      onChange={(event) => updateMatrixTarget(index, "label", event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Host
                    </label>
                    <Input
                      value={target.host}
                      onChange={(event) => updateMatrixTarget(index, "host", event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Port
                    </label>
                    <Input
                      value={target.port}
                      onChange={(event) => updateMatrixTarget(index, "port", event.target.value)}
                      inputMode="numeric"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Path
                    </label>
                    <Input
                      value={target.path}
                      onChange={(event) => updateMatrixTarget(index, "path", event.target.value)}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              className="gap-2 bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80"
              onClick={() => void handleRunTargetMatrix()}
              disabled={isRunningMatrix || !matrixProfileId}
            >
              <Play size={16} />
              {isRunningMatrix ? "Running Matrix..." : "Run Target Matrix"}
            </Button>
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => void handleCopyMatrixReport()}
              disabled={!lastMatrixReport}
            >
              <Copy size={16} />
              Copy Matrix JSON
            </Button>
          </div>

          {lastMatrixReport ? (
            <div className="mt-4 space-y-4 rounded-xl border border-border/40 bg-black/20 p-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Run Id
                  </div>
                  <div className="mt-1 break-all font-mono text-sm text-foreground">
                    {lastMatrixReport.run_id}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Baseline Core
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatCoreLabel(lastMatrixReport.baseline_core)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Profile
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {selectedMatrixProfile?.name ?? lastMatrixReport.profile_id}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Targets
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {lastMatrixReport.targets.length}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-3">
                {lastMatrixReport.core_summaries.map((summary) => (
                  <div
                    key={summary.core}
                    className="rounded-xl border border-border/40 bg-black/30 p-4"
                  >
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      {formatCoreLabel(summary.core)}
                    </div>
                    <div className="mt-3 grid gap-2 text-sm text-foreground">
                      <div>
                        Completed / Failed: {summary.completed_targets} / {summary.failed_targets}
                      </div>
                      <div>
                        Median Connect: {formatLatencyMetric(summary.median_connect_latency_ms)}
                      </div>
                      <div>
                        Median First Byte:{" "}
                        {formatLatencyMetric(summary.median_first_byte_latency_ms)}
                      </div>
                      <div>
                        Median Gap:{" "}
                        {formatLatencyMetric(summary.median_open_to_first_byte_gap_ms)}
                      </div>
                      <div>
                        Avg Throughput: {formatThroughputMetric(summary.average_throughput_kbps)}
                      </div>
                      <div>
                        Avg Gap Ratio:{" "}
                        {formatRatioMetric(summary.average_relative_open_to_first_byte_gap_ratio)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="space-y-3">
                {lastMatrixReport.targets.map((target) => (
                  <div
                    key={`${target.label}-${target.host}-${target.port}-${target.path}`}
                    className="rounded-xl border border-border/40 bg-black/30 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                          Target
                        </div>
                        <div className="mt-1 text-sm text-foreground">
                          {target.label} • {target.host}:{target.port}
                          {target.path}
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {target.comparison.entries.length} core runs
                      </div>
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-3">
                      {target.comparison.entries.map((entry) => (
                        <div
                          key={`${target.label}-${entry.requested_core}`}
                          className="rounded-lg border border-border/30 bg-black/20 p-3"
                        >
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            {formatCoreLabel(entry.requested_core)}
                          </div>
                          <div className="mt-2 text-sm text-foreground">
                            Connect: {formatLatencyMetric(entry.benchmark?.median_connect_latency_ms)}
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            First Byte:{" "}
                            {formatLatencyMetric(entry.benchmark?.median_first_byte_latency_ms)}
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            Throughput:{" "}
                            {formatThroughputMetric(entry.benchmark?.average_throughput_kbps)}
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            Gap:{" "}
                            {formatLatencyMetric(entry.benchmark?.median_open_to_first_byte_gap_ms)}
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            Gap vs Baseline:{" "}
                            {formatRatioMetric(entry.relative_open_to_first_byte_gap_ratio)}
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            Queue Peak:{" "}
                            {entry.benchmark?.helix_queue_pressure
                              ? `${entry.benchmark.helix_queue_pressure.frame_queue_depth} / ${entry.benchmark.helix_queue_pressure.frame_queue_peak}`
                              : "No signal"}
                          </div>
                          {entry.error ? (
                            <div className="mt-2 text-sm text-[var(--color-neon-pink)]">
                              {entry.error}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-border/40 bg-black/20 p-4 text-sm text-muted-foreground">
              Run the target matrix to compare Helix against the stable cores on more than one
              destination profile.
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-border/40 bg-black/30 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
              <Route size={18} />
              Helix Live Health Inspector
            </div>
            <p className="text-sm text-muted-foreground">
              Tracks the active route, continuity grace, route score, live stream count, bytes,
              and failover health straight from the embedded Helix sidecar.
            </p>
          </div>
        </div>

        {helixHealth ? (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Status
              </div>
              <div className="mt-1 text-sm text-foreground">
                {helixHealth.status} / {helixHealth.ready ? "ready" : "warming"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Active Route
              </div>
              <div className="mt-1 break-all text-sm text-foreground">
                {helixHealth.active_route_endpoint_ref ?? "Not selected yet"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Route Score / RTT
              </div>
              <div className="mt-1 text-sm text-foreground">
                {helixHealth.active_route_score ?? "n/a"} /{" "}
                {helixHealth.last_ping_rtt_ms == null
                  ? "n/a"
                  : `${helixHealth.last_ping_rtt_ms} ms`}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Warm Standby
              </div>
              <div className="mt-1 break-all text-sm text-foreground">
                {helixHealth.standby_route_endpoint_ref ?? "Not warmed"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Continuity Grace
              </div>
              <div className="mt-1 break-all text-sm text-foreground">
                {helixHealth.continuity_grace_active
                  ? `${helixHealth.continuity_grace_route_endpoint_ref ?? "same-route"} / ${
                      helixHealth.continuity_grace_remaining_ms == null
                        ? "n/a"
                        : `${helixHealth.continuity_grace_remaining_ms} ms`
                    }`
                  : "inactive"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Streams / Routes
              </div>
              <div className="mt-1 text-sm text-foreground">
                {helixHealth.active_streams} active / {helixHealth.route_count} total
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Bytes Sent
              </div>
              <div className="mt-1 text-sm text-foreground">
                {formatBytes(helixHealth.bytes_sent)}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Bytes Received
              </div>
              <div className="mt-1 text-sm text-foreground">
                {formatBytes(helixHealth.bytes_received)}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Failovers / Failures
              </div>
              <div className="mt-1 text-sm text-foreground">
                {helixHealth.active_route_failover_count} / {helixHealth.active_route_failed_activations}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Healthy Observations
              </div>
              <div className="mt-1 text-sm text-foreground">
                {helixHealth.active_route_healthy_observations}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Standby Ready / Score
              </div>
              <div className="mt-1 text-sm text-foreground">
                {helixHealth.standby_ready ? "ready" : "warming"} /{" "}
                {helixHealth.standby_route_score ?? "n/a"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Queue Depth / Peak
              </div>
              <div className="mt-1 text-sm text-foreground">
                {helixHealth.frame_queue_depth} / {helixHealth.frame_queue_peak}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Pending Opens
              </div>
              <div className="mt-1 text-sm text-foreground">
                {helixHealth.pending_open_streams}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Max Concurrent
              </div>
              <div className="mt-1 text-sm text-foreground">
                {helixHealth.max_concurrent_streams}
              </div>
            </div>
          </div>
            <div className="rounded-lg border border-border/30 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Continuity Snapshot
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Continuity Grace
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {helixHealth.continuity_grace_active
                      ? `${formatNullableText(
                          helixHealth.continuity_grace_route_endpoint_ref,
                          "same-route",
                        )} / ${
                          helixHealth.continuity_grace_remaining_ms == null
                            ? "n/a"
                            : `${helixHealth.continuity_grace_remaining_ms} ms`
                        }`
                      : "inactive"}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Continuity Recoveries
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {helixHealth.active_route_successful_continuity_recovers}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Last Continuity Recovery
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatLatencyMetric(helixHealth.active_route_last_continuity_recovery_ms)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Cross-Route Recoveries
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {helixHealth.active_route_successful_cross_route_recovers}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Last Cross-Route Recovery
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatLatencyMetric(helixHealth.active_route_last_cross_route_recovery_ms)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Continuity Grace Entries
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {helixHealth.active_route_continuity_grace_entries}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Continuity Summary
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatLiveContinuitySummary(helixHealth)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-4 rounded-lg border border-border/40 bg-black/20 p-4 text-sm text-muted-foreground">
            Helix live health is unavailable right now. Resolve and prepare a Helix runtime or
            connect through Helix to populate the live inspector.
          </div>
        )}
      </div>

      <div className="rounded-xl border border-border/40 bg-black/30 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
              <Gauge size={18} />
              Helix Live Telemetry
            </div>
            <p className="text-sm text-muted-foreground">
              Recent RTT samples and per-stream queue data captured from the active Helix sidecar.
              These samples also land in the exported support bundle for deeper tuning.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => void handleCopyHelixTelemetry()}
            disabled={!helixTelemetry}
          >
            <Copy size={14} />
            Copy Telemetry JSON
          </Button>
        </div>

        {helixTelemetry ? (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Collected At
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatTimestamp(helixTelemetry.collected_at)}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  RTT Samples
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {helixTelemetry.recent_rtt_ms.length}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  RTT p50 / p95
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {formatLatencyMetric(helixTelemetryRttP50)} /{" "}
                  {formatLatencyMetric(helixTelemetryRttP95)}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Recent Streams
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {helixTelemetry.recent_streams.length}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Queue Depth / Peak
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {helixTelemetry.health.frame_queue_depth} / {helixTelemetry.health.frame_queue_peak}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Pending / Max
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {helixTelemetry.health.pending_open_streams} /{" "}
                  {helixTelemetry.health.max_concurrent_streams}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Stream Queue Peaks
                </div>
                <div className="mt-1 text-sm text-foreground">
                  Frame {helixTelemetryPeakFrameQueue ?? "n/a"} / Inbound{" "}
                  {helixTelemetryPeakInboundQueue ?? "n/a"}
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-border/40 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                Recent RTT Samples
              </div>
              <div className="mt-2 text-sm text-foreground">
                {helixTelemetry.recent_rtt_ms.length > 0
                  ? helixTelemetry.recent_rtt_ms.map((value) => `${value} ms`).join(" • ")
                  : "No RTT samples collected yet"}
              </div>
            </div>

            <div className="space-y-3">
              {helixTelemetry.recent_streams.length > 0 ? (
                helixTelemetry.recent_streams.slice(0, 6).map((stream) => (
                  <div
                    key={`${stream.stream_id}-${stream.opened_at}`}
                    className="rounded-lg border border-border/40 bg-black/20 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                          Stream
                        </div>
                        <div className="mt-1 text-sm text-foreground">
                          #{stream.stream_id} • {stream.target_authority}
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatTimestamp(stream.opened_at)}
                      </div>
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <div>
                        <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                          Duration
                        </div>
                        <div className="mt-1 text-sm text-foreground">
                          {formatLatencyMetric(stream.duration_ms)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                          Bytes Sent
                        </div>
                        <div className="mt-1 text-sm text-foreground">
                          {formatBytes(stream.bytes_sent)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                          Bytes Received
                        </div>
                        <div className="mt-1 text-sm text-foreground">
                          {formatBytes(stream.bytes_received)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                          Queue Peaks
                        </div>
                        <div className="mt-1 text-sm text-foreground">
                          Frame {stream.peak_frame_queue_depth} / Inbound{" "}
                          {stream.peak_inbound_queue_depth}
                        </div>
                      </div>
                    </div>
                    {stream.close_reason ? (
                      <div className="mt-3 text-sm text-muted-foreground">
                        Close reason: {stream.close_reason}
                      </div>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="rounded-lg border border-border/40 bg-black/20 p-4 text-sm text-muted-foreground">
                  No per-stream telemetry is available yet. Start a Helix session or run a drill to
                  populate this view.
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="mt-4 rounded-lg border border-border/40 bg-black/20 p-4 text-sm text-muted-foreground">
            Helix live telemetry is unavailable right now. Refresh the snapshot after a Helix
            session, drill, or recovery benchmark.
          </div>
        )}
      </div>

      <div className="rounded-xl border border-border/40 bg-black/30 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
              <Activity size={18} />
              Recent Diagnostics Timeline
            </div>
            <p className="text-sm text-muted-foreground">
              Structured desktop events for connect/disconnect, Helix runtime changes, benchmark
              completions, process deaths, and diagnostics exports.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => void handleCopyEntries()}
            disabled={recentEntries.length === 0}
          >
            <Copy size={14} />
            Copy Timeline
          </Button>
        </div>

        <div className="mt-4 space-y-3">
          {recentEntries.length > 0 ? (
            recentEntries.slice(0, 14).map((entry: DiagnosticEntry) => (
              <div
                key={entry.id}
                className="rounded-lg border border-border/30 bg-black/20 p-4"
              >
                {(() => {
                  const payloadSummary = summarizeDiagnosticPayload(entry);

                  return (
                    <>
                      <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.15em] text-muted-foreground">
                        <span>{new Date(entry.timestamp).toLocaleString()}</span>
                        <span className={toneForLevel(entry.level)}>{entry.level}</span>
                        <span>{entry.source}</span>
                      </div>
                      <div className="mt-2 text-sm text-foreground">{entry.message}</div>
                      {payloadSummary ? (
                        <div className="mt-2 text-xs text-muted-foreground">
                          {payloadSummary}
                        </div>
                      ) : null}
                    </>
                  );
                })()}
              </div>
            ))
          ) : (
            <div className="rounded-lg border border-border/30 bg-black/20 p-4 text-sm text-muted-foreground">
              No diagnostics events have been recorded yet.
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-xl border border-border/40 bg-black/30 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
                <TerminalSquare size={18} />
                Core Runtime Log Tail
              </div>
              <p className="text-sm text-muted-foreground">
                Recent stdout/stderr tail for `Sing-box` and `Xray`.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => void handleCopyCoreTail("Core runtime log tail", coreLogTail)}
              disabled={coreLogTail.length === 0}
            >
              <Copy size={14} />
              Copy
            </Button>
          </div>

          <pre className="mt-4 max-h-72 overflow-auto rounded-lg border border-border/30 bg-[#0d0d0d] p-4 text-xs text-[var(--color-matrix-green)]">
            {coreLogTail.length > 0
              ? coreLogTail.join("\n")
              : "Core runtime log tail is empty."}
          </pre>
        </div>

        <div className="rounded-xl border border-border/40 bg-black/30 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-neon-cyan)]">
                <TerminalSquare size={18} />
                Helix Runtime Log Tail
              </div>
              <p className="text-sm text-muted-foreground">
                Recent embedded `Helix` sidecar log tail for route selection, fallback, and runtime
                errors.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => void handleCopyCoreTail("Helix runtime log tail", helixLogTail)}
              disabled={helixLogTail.length === 0}
            >
              <Copy size={14} />
              Copy
            </Button>
          </div>

          <pre className="mt-4 max-h-72 overflow-auto rounded-lg border border-border/30 bg-[#0d0d0d] p-4 text-xs text-[var(--color-neon-cyan)]">
            {helixLogTail.length > 0
              ? helixLogTail.join("\n")
              : "Helix runtime log tail is empty."}
          </pre>
        </div>
      </div>
    </div>
  );
}
