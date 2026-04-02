import { motion, AnimatePresence } from "framer-motion";
import { lazy, Suspense, useEffect, useState } from "react";
import {
  getActiveCore,
  getCustomConfig,
  getHelixCapabilities,
  getHelixRuntimeState,
  getProfiles,
  prepareHelixRuntime,
  resolveHelixManifest,
  runTransportCoreComparison,
  saveActiveCore,
  saveCustomConfig,
  type EngineCore,
  type HelixCapabilityDefaults,
  type HelixPreparedRuntime,
  type HelixResolvedManifest,
  type ProxyNode,
  type StableCore,
  type TransportBenchmarkComparisonReport,
} from "../../shared/api/ipc";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { toast } from "sonner";
import {
  Activity,
  Cpu,
  FileJson,
  Globe,
  KeyRound,
  Monitor,
  Moon,
  RefreshCw,
  Save,
  Shield,
  Sun,
} from "lucide-react";
import { useTheme } from "../../app/theme-provider";

const DiagnosticsSupportPanel = lazy(() =>
  import("../../components/settings/diagnostics-support-panel").then((module) => ({
    default: module.DiagnosticsSupportPanel,
  })),
);

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}

function formatManifestSummary(manifest: HelixResolvedManifest): string {
  const profile = manifest.manifest.transport_profile;
  return `${profile.profile_family} v${profile.profile_version} policy ${profile.policy_version}`;
}

function resolveStableFallbackCore(activeCore: EngineCore): StableCore {
  return activeCore === "xray" ? "xray" : "sing-box";
}

function formatLatencyMetric(value?: number | null): string {
  return value == null ? "No signal" : `${value} ms`;
}

function formatThroughputMetric(value?: number | null): string {
  return value == null ? "No signal" : `${value.toFixed(1)} kbps`;
}

function formatRatioMetric(value?: number | null): string {
  return value == null ? "Baseline" : `${value.toFixed(2)}x`;
}

function ratioToneClass(
  value: number | null | undefined,
  lowerIsBetter: boolean,
): string {
  if (value == null || value === 1) {
    return "text-muted-foreground";
  }

  const isBetter = lowerIsBetter ? value < 1 : value > 1;
  return isBetter
    ? "text-[var(--color-matrix-green)]"
    : "text-[var(--color-neon-pink)]";
}

function formatCoreLabel(core?: string | null): string {
  switch (core) {
    case "helix":
      return "Helix";
    case "sing-box":
      return "Sing-box";
    case "xray":
      return "Xray";
    case "private-transport":
      return "Helix (Legacy Alias)";
    default:
      return core ?? "Unknown";
  }
}

function formatProfileLabel(profile: ProxyNode): string {
  return `${profile.name} • ${profile.protocol.toUpperCase()} • ${profile.server}:${profile.port}`;
}

export function SettingsPage() {
  const [useCustomConfig, setUseCustomConfig] = useState(false);
  const [jsonConfig, setJsonConfig] = useState("");
  const [activeCore, setActiveCore] = useState<EngineCore>("sing-box");
  const [isSaving, setIsSaving] = useState(false);
  const [helixCapabilities, setHelixCapabilities] =
    useState<HelixCapabilityDefaults | null>(null);
  const [helixManifest, setHelixManifest] =
    useState<HelixResolvedManifest | null>(null);
  const [helixPreparedRuntime, setHelixPreparedRuntime] =
    useState<HelixPreparedRuntime | null>(null);
  const [helixFallbackReason, setHelixFallbackReason] =
    useState<string | null>(null);
  const [helixBackendUrl, setHelixBackendUrl] = useState("");
  const [helixAccessToken, setHelixAccessToken] = useState("");
  const [helixDesktopClientId, setHelixDesktopClientId] = useState("");
  const [profiles, setProfiles] = useState<ProxyNode[]>([]);
  const [comparisonProfileId, setComparisonProfileId] = useState("");
  const [comparisonTargetHost, setComparisonTargetHost] = useState("example.com");
  const [comparisonTargetPort, setComparisonTargetPort] = useState("80");
  const [comparisonTargetPath, setComparisonTargetPath] = useState("/");
  const [comparisonAttempts, setComparisonAttempts] = useState("5");
  const [comparisonReport, setComparisonReport] =
    useState<TransportBenchmarkComparisonReport | null>(null);
  const [isRefreshingTransport, setIsRefreshingTransport] = useState(false);
  const [isResolvingTransport, setIsResolvingTransport] = useState(false);
  const [isPreparingTransport, setIsPreparingTransport] = useState(false);
  const [isRunningComparison, setIsRunningComparison] = useState(false);
  const { theme, setTheme } = useTheme();
  const selectedComparisonProfile =
    profiles.find((profile) => profile.id === comparisonProfileId) ?? null;
  const diagnosticsPanelReady =
    Boolean(helixPreparedRuntime) ||
    Boolean(helixManifest) ||
    Boolean(comparisonReport);

  const refreshHelixState = async (showToast = false) => {
    setIsRefreshingTransport(true);

    try {
      const [capabilities, runtimeState, profileInventory] = await Promise.all([
        getHelixCapabilities(),
        getHelixRuntimeState(),
        getProfiles(),
      ]);

      setHelixCapabilities(capabilities);
      setHelixManifest(runtimeState.last_manifest);
      setHelixPreparedRuntime(runtimeState.last_prepared_runtime);
      setHelixFallbackReason(runtimeState.last_fallback_reason);
      setHelixDesktopClientId(runtimeState.desktop_client_id);
      setHelixBackendUrl(runtimeState.backend_url ?? "");
      setProfiles(profileInventory);
      setComparisonProfileId((currentId) => {
        if (currentId && profileInventory.some((profile) => profile.id === currentId)) {
          return currentId;
        }

        return profileInventory[0]?.id ?? "";
      });

      if (profileInventory.length === 0) {
        setComparisonReport(null);
      }

      if (showToast) {
        toast.success("Helix state refreshed.");
      }
    } catch (error) {
      toast.error(`Failed to refresh Helix state: ${formatError(error)}`);
    } finally {
      setIsRefreshingTransport(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const loadSettings = async () => {
      try {
        const [customConfig, core] = await Promise.all([
          getCustomConfig(),
          getActiveCore(),
        ]);

        if (cancelled) {
          return;
        }

        if (customConfig) {
          setUseCustomConfig(true);
          setJsonConfig(customConfig);
        }
        setActiveCore(core);
      } catch (error) {
        toast.error(`Failed to load core settings: ${formatError(error)}`);
      }

      if (!cancelled) {
        await refreshHelixState(false);
      }
    };

    void loadSettings();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (useCustomConfig) {
        JSON.parse(jsonConfig);
        await saveCustomConfig(jsonConfig);
      } else {
        await saveCustomConfig(null);
      }

      await saveActiveCore(activeCore);
      toast.success("Settings saved successfully.");
    } catch (error) {
      toast.error(`Invalid JSON or save failed: ${formatError(error)}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCoreChange = async (core: EngineCore) => {
    setActiveCore(core);
    try {
      await saveActiveCore(core);
      toast.success(`Active core switched to ${core}.`);
    } catch (error) {
      toast.error(`Failed to change core: ${formatError(error)}`);
    }
  };

  const handleResolveHelix = async () => {
    setIsResolvingTransport(true);

    try {
      const manifest = await resolveHelixManifest(
        helixBackendUrl,
        helixAccessToken,
        resolveStableFallbackCore(activeCore),
      );

      setHelixManifest(manifest);
      setHelixPreparedRuntime(null);
      setHelixFallbackReason(null);
      setHelixBackendUrl(helixBackendUrl.trim());
      toast.success(
        `Helix manifest resolved: ${formatManifestSummary(manifest)}.`,
      );
    } catch (error) {
      toast.error(`Helix resolve failed: ${formatError(error)}`);
    } finally {
      setIsResolvingTransport(false);
    }
  };

  const handlePrepareHelix = async () => {
    setIsPreparingTransport(true);

    try {
      const preparedRuntime = await prepareHelixRuntime();
      setHelixPreparedRuntime(preparedRuntime);
      setHelixFallbackReason(null);

      if (preparedRuntime.binary_available) {
        toast.success(
          `Helix runtime prepared with ${preparedRuntime.route_count} route(s).`,
        );
      } else {
        toast.error(
          `Helix sidecar entrypoint is unavailable at ${preparedRuntime.sidecar_path}. Stable fallback remains ${preparedRuntime.fallback_core}.`,
        );
      }
    } catch (error) {
      toast.error(`Helix runtime prepare failed: ${formatError(error)}`);
    } finally {
      setIsPreparingTransport(false);
    }
  };

  const handleRunComparison = async () => {
    if (!comparisonProfileId) {
      toast.error("Pick a saved desktop profile before running the comparison.");
      return;
    }

    const targetPort = Number.parseInt(comparisonTargetPort, 10);
    if (!Number.isFinite(targetPort) || targetPort <= 0 || targetPort > 65535) {
      toast.error("Benchmark target port must be a valid TCP port.");
      return;
    }

    const attempts = Number.parseInt(comparisonAttempts, 10);
    if (!Number.isFinite(attempts) || attempts <= 0 || attempts > 20) {
      toast.error("Benchmark attempts must be between 1 and 20.");
      return;
    }

    setIsRunningComparison(true);

    try {
      const report = await runTransportCoreComparison({
        profile_id: comparisonProfileId,
        benchmark: {
          target_host: comparisonTargetHost.trim() || "example.com",
          target_port: targetPort,
          target_path: comparisonTargetPath.trim() || "/",
          attempts,
        },
      });

      setComparisonReport(report);
      await refreshHelixState(false);
      toast.success(
        `Comparison finished. Baseline: ${formatCoreLabel(report.baseline_core)}.`,
      );
    } catch (error) {
      toast.error(`Comparison failed: ${formatError(error)}`);
    } finally {
      setIsRunningComparison(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      transition={{ duration: 0.2 }}
      className="flex h-full flex-col gap-6 pb-6"
    >
      <header className="mb-2">
        <h1 className="text-3xl font-bold tracking-tight text-[var(--color-neon-cyan)] drop-shadow-[0_0_8px_rgba(0,255,255,0.4)]">
          Settings
        </h1>
        <p className="mt-2 text-muted-foreground">
          Configure core app preferences, experimental transport handshakes, and routing.
        </p>
      </header>

      <div className="flex flex-1 flex-col gap-6">
        <div className="flex flex-col gap-4 rounded-xl border border-border/50 bg-black/40 p-6">
          <div className="mb-2 flex items-center justify-between">
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

        <div className="flex flex-col gap-4 rounded-xl border border-border/50 bg-black/40 p-6">
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-3 text-lg font-semibold text-[var(--color-matrix-green)]">
              <Cpu size={24} />
              <h2>Proxy Engine Core</h2>
            </div>
          </div>
          <p className="mb-2 text-sm text-muted-foreground">
            Sing-box is recommended for modern protocols, while Xray-core stays available as the
            stable fallback core for Helix recovery.
          </p>
          <div className="grid grid-cols-3 gap-4">
            <Button
              variant={activeCore === "sing-box" ? "default" : "outline"}
              className={
                activeCore === "sing-box"
                  ? "bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80"
                  : ""
              }
              onClick={() => handleCoreChange("sing-box")}
            >
              Sing-box (Modern)
            </Button>
            <Button
              variant={activeCore === "xray" ? "default" : "outline"}
              className={
                activeCore === "xray"
                  ? "bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80"
                  : ""
              }
              onClick={() => handleCoreChange("xray")}
            >
              Xray (Legacy)
            </Button>
            <Button
              variant={activeCore === "helix" ? "default" : "outline"}
              className={
                activeCore === "helix"
                  ? "bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80"
                  : ""
              }
              onClick={() => handleCoreChange("helix")}
            >
              Helix (Experimental)
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-5 rounded-xl border border-border/50 bg-black/40 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-3 text-lg font-semibold text-[var(--color-neon-cyan)]">
                <Shield size={24} />
                <h2>Helix Lab Runtime</h2>
              </div>
              <p className="max-w-3xl text-sm text-muted-foreground">
                Desktop negotiates a compatible transport profile window with the backend facade,
                resolves a signed manifest, and keeps the current stable core as a hard fallback.
              </p>
            </div>

            <Button
              variant="outline"
              className="gap-2"
              onClick={() => void refreshHelixState(true)}
              disabled={isRefreshingTransport}
            >
              <RefreshCw size={16} className={isRefreshingTransport ? "animate-spin" : ""} />
              {isRefreshingTransport ? "Refreshing..." : "Refresh"}
            </Button>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-border/40 bg-black/30 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Desktop Client Id
              </div>
              <div className="mt-2 break-all font-mono text-sm text-[var(--color-matrix-green)]">
                {helixDesktopClientId || "Allocating..."}
              </div>
            </div>
            <div className="rounded-lg border border-border/40 bg-black/30 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Local Supported Profiles
              </div>
              <div className="mt-2 text-sm text-foreground">
                {helixCapabilities?.supported_transport_profiles.length ?? 0} windows
              </div>
            </div>
            <div className="rounded-lg border border-border/40 bg-black/30 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Stable Fallback Core
              </div>
              <div className="mt-2 text-sm text-foreground">
                {resolveStableFallbackCore(activeCore)}
              </div>
            </div>
            <div className="rounded-lg border border-border/40 bg-black/30 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Prepared Runtime
              </div>
              <div className="mt-2 text-sm text-foreground">
                {helixPreparedRuntime
                  ? helixPreparedRuntime.binary_available
                    ? "Ready to launch"
                    : "Awaiting sidecar"
                  : "Not prepared"}
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Globe size={16} className="text-[var(--color-neon-cyan)]" />
                Backend URL
              </label>
              <Input
                value={helixBackendUrl}
                onChange={(event) => setHelixBackendUrl(event.target.value)}
                placeholder="https://api.cybervpn.example"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <KeyRound size={16} className="text-[var(--color-neon-pink)]" />
                Access Token
              </label>
              <Input
                type="password"
                value={helixAccessToken}
                onChange={(event) => setHelixAccessToken(event.target.value)}
                placeholder="Bearer token for backend facade"
                autoComplete="off"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={() => void handleResolveHelix()}
              disabled={isResolvingTransport}
              className="gap-2 bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80"
            >
              <Activity size={16} />
              {isResolvingTransport ? "Resolving..." : "Resolve Compatible Manifest"}
            </Button>
            <p className="text-sm text-muted-foreground">
              Uses the current stable core as the requested fallback if the Helix
              runtime becomes unhealthy.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="outline"
              onClick={() => void handlePrepareHelix()}
              disabled={isPreparingTransport}
              className="gap-2"
            >
              <Activity size={16} />
              {isPreparingTransport ? "Preparing..." : "Prepare Local Runtime"}
            </Button>
            <p className="text-sm text-muted-foreground">
              Writes a local sidecar config bundle, reserves a localhost health endpoint, and
              prepares the embedded desktop sidecar entrypoint for launch.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {helixCapabilities?.supported_transport_profiles.map((profile) => (
              <div
                key={`${profile.profile_family}-${profile.min_transport_profile_version}-${profile.max_transport_profile_version}`}
                className="rounded-lg border border-border/40 bg-black/30 p-4"
              >
                <div className="text-sm font-semibold text-[var(--color-neon-cyan)]">
                  {profile.profile_family}
                </div>
                <div className="mt-2 text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Compatible Window
                </div>
                <div className="mt-1 text-sm text-foreground">
                  v{profile.min_transport_profile_version} to v
                  {profile.max_transport_profile_version}
                </div>
                <div className="mt-2 text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Policy Versions
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {profile.supported_policy_versions.join(", ")}
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-border/40 bg-black/30 p-5">
            <div className="mb-3 text-sm font-semibold text-[var(--color-matrix-green)]">
              Last Resolved Manifest
            </div>

            {helixManifest ? (
              <>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Transport Profile
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {formatManifestSummary(helixManifest)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Rollout Channel
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {helixManifest.manifest.subject.channel}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Compatibility Window
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    v{helixManifest.manifest.compatibility_window.min_transport_profile_version}
                    {" - "}v
                    {helixManifest.manifest.compatibility_window.max_transport_profile_version}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Fallback Core
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {helixManifest.manifest.capability_profile.fallback_core}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Manifest Version
                  </div>
                  <div className="mt-1 break-all font-mono text-sm text-foreground">
                    {helixManifest.manifest_version_id}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Expires At
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {new Date(helixManifest.manifest.expires_at).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Endpoint Count
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {helixManifest.manifest.routes.length}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Required Capabilities
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {helixManifest.manifest.capability_profile.required_capabilities.join(", ")}
                  </div>
                </div>
              </div>

                {helixManifest.selected_profile_policy ? (
                  <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Policy Score
                    </div>
                    <div className="mt-1 text-sm text-[var(--color-neon-cyan)]">
                      {helixManifest.selected_profile_policy.policy_score}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Observed Events
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {helixManifest.selected_profile_policy.observed_events}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Continuity Success
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {(helixManifest.selected_profile_policy.continuity_success_rate * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Cross-Route Recovery
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {(helixManifest.selected_profile_policy.cross_route_recovery_rate * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Connect Success
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {(helixManifest.selected_profile_policy.connect_success_rate * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Fallback Rate
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {(helixManifest.selected_profile_policy.fallback_rate * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4 md:col-span-2 xl:col-span-2">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Policy State
                    </div>
                    <div
                      className={`mt-1 text-sm ${
                        helixManifest.selected_profile_policy.degraded
                          ? "text-[var(--color-neon-pink)]"
                          : "text-[var(--color-matrix-green)]"
                      }`}
                    >
                      {helixManifest.selected_profile_policy.degraded
                        ? "Degraded: adapter selected the best available compatible profile under current evidence."
                        : "Healthy: adapter selected a non-degraded compatible profile."}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Advisory State
                    </div>
                    <div className="mt-1 text-sm text-foreground">
                      {helixManifest.selected_profile_policy.advisory_state}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      New-Session Posture
                    </div>
                    <div
                      className={`mt-1 text-sm ${
                        helixManifest.selected_profile_policy.new_session_posture === "blocked"
                          ? "text-[var(--color-neon-pink)]"
                          : helixManifest.selected_profile_policy.new_session_posture === "guarded"
                            ? "text-[var(--color-neon-cyan)]"
                            : helixManifest.selected_profile_policy.new_session_posture === "watch"
                              ? "text-[var(--color-neon-pink)]"
                              : "text-[var(--color-matrix-green)]"
                      }`}
                    >
                      {helixManifest.selected_profile_policy.new_session_posture}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      New Session Issuance
                    </div>
                    <div
                      className={`mt-1 text-sm ${
                        helixManifest.selected_profile_policy.new_session_issuable
                          ? "text-[var(--color-matrix-green)]"
                          : "text-[var(--color-neon-pink)]"
                      }`}
                    >
                      {helixManifest.selected_profile_policy.new_session_issuable
                        ? "Issuable for new Helix desktop sessions"
                        : "Blocked by new-session continuity guardrails"}
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      Selection flag:{" "}
                      {helixManifest.selected_profile_policy.selection_eligible
                        ? "profile remains rollout-eligible"
                        : "profile is marked avoid-new-sessions"}
                    </div>
                    {helixManifest.selected_profile_policy.suppression_window_active ? (
                      <div className="mt-1 text-xs text-[var(--color-neon-pink)]">
                        Adapter cooloff window active
                        {helixManifest.selected_profile_policy.suppressed_until
                          ? ` until ${new Date(
                              helixManifest.selected_profile_policy.suppressed_until,
                            ).toLocaleString()}`
                          : ""}
                        .
                      </div>
                    ) : null}
                  </div>
                  <div className="rounded-lg border border-border/40 bg-black/30 p-4">
                    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                      Suppression Window
                    </div>
                    <div
                      className={`mt-1 text-sm ${
                        helixManifest.selected_profile_policy.suppression_window_active
                          ? "text-[var(--color-neon-pink)]"
                          : "text-[var(--color-matrix-green)]"
                      }`}
                    >
                      {helixManifest.selected_profile_policy.suppression_window_active
                        ? "Active"
                        : "Inactive"}
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      Observations:{" "}
                      {helixManifest.selected_profile_policy.suppression_observation_count}
                    </div>
                    {helixManifest.selected_profile_policy.suppression_reason ? (
                      <div className="mt-1 text-xs text-muted-foreground">
                        Reason: {helixManifest.selected_profile_policy.suppression_reason}
                      </div>
                    ) : null}
                  </div>
                  {helixManifest.selected_profile_policy.recommended_action ? (
                    <div className="rounded-lg border border-border/40 bg-black/30 p-4 md:col-span-2 xl:col-span-4">
                      <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                        Recommended Action
                      </div>
                      <div className="mt-1 text-sm text-foreground">
                        {helixManifest.selected_profile_policy.recommended_action}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                No Helix manifest has been resolved on this desktop yet.
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-4 rounded-xl border border-border/50 bg-black/40 p-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3 text-lg font-semibold text-[var(--color-neon-pink)]">
              <Activity size={24} />
              <h2>Helix Runtime</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              The desktop prepares a local sidecar config from the signed manifest and reverts to
              a stable core if the embedded Helix runtime cannot become healthy.
            </p>
          </div>

          {helixPreparedRuntime ? (
            <div className="grid gap-3 rounded-xl border border-border/40 bg-black/30 p-5 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Sidecar Status
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {helixPreparedRuntime.binary_available ? "Embedded Ready" : "Unavailable"}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Fallback Core
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {helixPreparedRuntime.fallback_core}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Route Count
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {helixPreparedRuntime.route_count}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Startup Timeout
                </div>
                <div className="mt-1 text-sm text-foreground">
                  {helixPreparedRuntime.startup_timeout_seconds}s
                </div>
              </div>
              <div className="md:col-span-2 xl:col-span-2">
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Sidecar Entry
                </div>
                <div className="mt-1 break-all font-mono text-sm text-foreground">
                  {helixPreparedRuntime.sidecar_path}
                </div>
              </div>
              <div className="md:col-span-2 xl:col-span-2">
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Config Path
                </div>
                <div className="mt-1 break-all font-mono text-sm text-foreground">
                  {helixPreparedRuntime.config_path}
                </div>
              </div>
              <div className="md:col-span-2 xl:col-span-4">
                <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                  Local Health Endpoint
                </div>
                <div className="mt-1 break-all font-mono text-sm text-foreground">
                  {helixPreparedRuntime.health_url}
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-border/40 bg-black/30 p-5 text-sm text-muted-foreground">
              The desktop has not prepared a Helix runtime bundle yet.
            </div>
          )}

          {helixFallbackReason ? (
            <div className="rounded-xl border border-[var(--color-neon-pink)]/40 bg-[rgba(255,0,255,0.08)] p-4 text-sm text-[var(--color-neon-pink)]">
              Last automatic fallback: {helixFallbackReason}
            </div>
          ) : null}
        </div>

        <div className="flex flex-col gap-5 rounded-xl border border-border/50 bg-black/40 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-3 text-lg font-semibold text-[var(--color-neon-cyan)]">
                <Activity size={24} />
                <h2>Helix Core Comparison</h2>
              </div>
              <p className="max-w-3xl text-sm text-muted-foreground">
                Runs the same saved desktop profile through Helix, Sing-box, and Xray, then
                measures median connect time, first-byte latency, and throughput on a shared
                SOCKS5 benchmark path. The comparison temporarily cycles the active connection.
              </p>
            </div>

            <Button
              onClick={() => void handleRunComparison()}
              disabled={isRunningComparison || !comparisonProfileId}
              className="gap-2 bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80"
            >
              <Activity size={16} />
              {isRunningComparison ? "Running Comparison..." : "Run Helix vs Stable Cores"}
            </Button>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <div className="space-y-2 xl:col-span-2">
              <label className="text-sm font-medium text-foreground">
                Desktop Profile For Comparison
              </label>
              <select
                value={comparisonProfileId}
                onChange={(event) => {
                  setComparisonProfileId(event.target.value);
                  setComparisonReport(null);
                }}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm text-foreground outline-none transition-colors focus:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                disabled={profiles.length === 0}
              >
                {profiles.length === 0 ? (
                  <option value="">No saved profiles available</option>
                ) : null}
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {formatProfileLabel(profile)}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                {selectedComparisonProfile
                  ? `Using node ${selectedComparisonProfile.id} as the shared benchmark target.`
                  : "Add or import at least one desktop profile before running the benchmark."}
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Target Host</label>
              <Input
                value={comparisonTargetHost}
                onChange={(event) => setComparisonTargetHost(event.target.value)}
                placeholder="example.com"
                autoComplete="off"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Target Port</label>
              <Input
                value={comparisonTargetPort}
                onChange={(event) => setComparisonTargetPort(event.target.value)}
                placeholder="80"
                inputMode="numeric"
                autoComplete="off"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Attempts</label>
              <Input
                value={comparisonAttempts}
                onChange={(event) => setComparisonAttempts(event.target.value)}
                placeholder="5"
                inputMode="numeric"
                autoComplete="off"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Target Path</label>
              <Input
                value={comparisonTargetPath}
                onChange={(event) => setComparisonTargetPath(event.target.value)}
                placeholder="/"
                autoComplete="off"
              />
            </div>
            <div className="rounded-lg border border-border/40 bg-black/30 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Benchmark Scope
              </div>
              <div className="mt-2 text-sm text-foreground">
                Helix, Sing-box, and Xray all run the same request path.
              </div>
            </div>
            <div className="rounded-lg border border-border/40 bg-black/30 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Session Impact
              </div>
              <div className="mt-2 text-sm text-foreground">
                The runner disconnects the live session while it cycles through cores.
              </div>
            </div>
          </div>

          {comparisonReport ? (
            <div className="space-y-4 rounded-xl border border-border/40 bg-black/30 p-5">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Baseline Core
                  </div>
                  <div className="mt-1 text-sm text-[var(--color-matrix-green)]">
                    {formatCoreLabel(comparisonReport.baseline_core)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Profile Id
                  </div>
                  <div className="mt-1 break-all font-mono text-sm text-foreground">
                    {comparisonReport.profile_id}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Report Time
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {new Date(comparisonReport.generated_at).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    Compared Cores
                  </div>
                  <div className="mt-1 text-sm text-foreground">
                    {comparisonReport.entries.length}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-3">
                {comparisonReport.entries.map((entry) => {
                  const benchmark = entry.benchmark;
                  const isBaseline =
                    entry.effective_core === comparisonReport.baseline_core ||
                    entry.requested_core === comparisonReport.baseline_core;

                  return (
                    <div
                      key={`${entry.requested_core}-${entry.effective_core ?? "failed"}`}
                      className={`rounded-xl border p-5 ${
                        isBaseline
                          ? "border-[var(--color-matrix-green)]/50 bg-[rgba(0,255,136,0.06)]"
                          : "border-border/40 bg-black/40"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                            Requested Core
                          </div>
                          <div className="mt-1 text-lg font-semibold text-[var(--color-neon-cyan)]">
                            {formatCoreLabel(entry.requested_core)}
                          </div>
                        </div>
                        {isBaseline ? (
                          <div className="rounded-full border border-[var(--color-matrix-green)]/40 px-3 py-1 text-xs uppercase tracking-[0.2em] text-[var(--color-matrix-green)]">
                            Baseline
                          </div>
                        ) : null}
                      </div>

                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <div>
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            Effective Core
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            {formatCoreLabel(entry.effective_core)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            Outcome
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            {entry.error ? "Failed" : "Completed"}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            Median Connect
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            {formatLatencyMetric(benchmark?.median_connect_latency_ms)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            Median First Byte
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            {formatLatencyMetric(benchmark?.median_first_byte_latency_ms)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            Throughput
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            {formatThroughputMetric(benchmark?.average_throughput_kbps)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            Success Rate
                          </div>
                          <div className="mt-1 text-sm text-foreground">
                            {benchmark
                              ? `${benchmark.successes}/${benchmark.attempts}`
                              : "No samples"}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 grid gap-3 md:grid-cols-3">
                        <div>
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            Connect Ratio
                          </div>
                          <div
                            className={`mt-1 text-sm ${ratioToneClass(
                              entry.relative_connect_latency_ratio,
                              true,
                            )}`}
                          >
                            {formatRatioMetric(entry.relative_connect_latency_ratio)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            First Byte Ratio
                          </div>
                          <div
                            className={`mt-1 text-sm ${ratioToneClass(
                              entry.relative_first_byte_latency_ratio,
                              true,
                            )}`}
                          >
                            {formatRatioMetric(entry.relative_first_byte_latency_ratio)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                            Throughput Ratio
                          </div>
                          <div
                            className={`mt-1 text-sm ${ratioToneClass(
                              entry.relative_throughput_ratio,
                              false,
                            )}`}
                          >
                            {formatRatioMetric(entry.relative_throughput_ratio)}
                          </div>
                        </div>
                      </div>

                      {entry.error ? (
                        <div className="mt-4 rounded-lg border border-[var(--color-neon-pink)]/40 bg-[rgba(255,0,255,0.08)] p-3 text-sm text-[var(--color-neon-pink)]">
                          {entry.error}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-border/40 bg-black/30 p-5 text-sm text-muted-foreground">
              Run the comparison to see Helix against the stable desktop cores on the same
              benchmark path.
            </div>
          )}
        </div>

        <Suspense
          fallback={
            <div className="rounded-xl border border-border/50 bg-black/40 p-6 text-sm text-muted-foreground">
              Loading Helix diagnostics lab...
            </div>
          }
        >
          {diagnosticsPanelReady ? (
            <DiagnosticsSupportPanel />
          ) : (
            <div className="rounded-xl border border-border/50 bg-black/40 p-6 text-sm text-muted-foreground">
              Helix diagnostics lab will load after you resolve a manifest, prepare a runtime, or
              run a comparison.
            </div>
          )}
        </Suspense>

        <div className="flex flex-col gap-4 rounded-xl border border-border/50 bg-black/40 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 text-lg font-semibold text-[var(--color-neon-pink)]">
              <FileJson size={24} />
              <h2>Raw "Power-User" Configuration</h2>
            </div>
            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                value=""
                className="peer sr-only"
                checked={useCustomConfig}
                onChange={(event) => setUseCustomConfig(event.target.checked)}
              />
              <div className="h-6 w-11 rounded-full bg-muted outline-none peer-checked:bg-[var(--color-neon-pink)] peer-checked:after:translate-x-full peer-checked:after:border-white after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-['']" />
            </label>
          </div>

          <p className="text-sm text-muted-foreground">
            Override the generated sing-box configuration entirely. When enabled, this exact JSON
            payload will be written to `run.json` and executed. The normal connection profiles and
            routing settings will be ignored.
          </p>

          <AnimatePresence>
            {useCustomConfig && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-2 flex flex-col gap-4"
              >
                <textarea
                  value={jsonConfig}
                  onChange={(event) => setJsonConfig(event.target.value)}
                  className="h-80 w-full resize-none rounded-md border border-border/60 bg-[#0d0d0d] p-4 font-mono text-sm text-[#a0a0a0] outline-none focus:border-[var(--color-neon-cyan)] focus:text-[var(--color-neon-cyan)]"
                  placeholder={'{\n  "log": { "level": "info" },\n  "inbounds": [...],\n  "outbounds": [...]\n}'}
                  spellCheck={false}
                />
              </motion.div>
            )}
          </AnimatePresence>

          <div className="mt-2 flex justify-end border-t border-border/30 pt-4">
            <Button
              onClick={handleSave}
              disabled={isSaving}
              className="gap-2 bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80"
            >
              <Save size={16} />
              {isSaving ? "Saving..." : "Save Settings"}
            </Button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
