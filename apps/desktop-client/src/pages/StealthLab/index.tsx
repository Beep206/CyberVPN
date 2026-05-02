import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  CheckCircle2,
  ChevronRight,
  Network,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  ShieldQuestion,
} from "lucide-react";
import { toast } from "sonner";
import {
  CensorshipReport,
  ProxyNode,
  StealthAutoPilotMode,
  StealthAutoPilotState,
  StealthCompareReport,
  applyStealthFix,
  clearNetworkStealthPolicy,
  compareStealthStrategies,
  getStealthAutoPilotMode,
  getNetworkRules,
  getProfiles,
  listenStealthProbeLog,
  rollbackLastStealthFix,
  runStealthDiagnostics,
  setStealthAutoPilotMode,
} from "../../shared/api/ipc";
import { useTranslation } from "react-i18next";

function formatTimestamp(timestamp?: number | null) {
  if (!timestamp) {
    return "—";
  }

  try {
    return new Date(timestamp).toLocaleString();
  } catch {
    return "—";
  }
}

function formatTierLabel(
  tier: string,
  t: ReturnType<typeof useTranslation>["t"]
) {
  switch (tier) {
    case "fast":
      return t("stealthLab.tier.fast");
    case "balanced":
      return t("stealthLab.tier.balanced");
    case "resistant":
      return t("stealthLab.tier.resistant");
    case "maximum":
      return t("stealthLab.tier.maximum");
    case "last-known-good":
      return t("stealthLab.tier.last-known-good");
    default:
      return tier;
  }
}

function formatAutoPilotMode(
  mode: StealthAutoPilotMode,
  t: ReturnType<typeof useTranslation>["t"]
) {
  switch (mode) {
    case "ask-before-apply":
      return t("stealthLab.autoPilotModes.ask-before-apply");
    case "auto-apply-trusted":
      return t("stealthLab.autoPilotModes.auto-apply-trusted");
    case "auto-apply-with-rollback":
      return t("stealthLab.autoPilotModes.auto-apply-with-rollback");
    default:
      return t("stealthLab.autoPilotModes.recommend-only");
  }
}

function describeAutoPilot(
  autoPilot: StealthAutoPilotState | null | undefined,
  t: ReturnType<typeof useTranslation>["t"]
) {
  if (!autoPilot) {
    return t("stealthLab.autoPilotPending");
  }

  switch (autoPilot.action) {
    case "confirm":
      return t("stealthLab.autoPilotActions.confirm");
    case "auto-applied":
      return t("stealthLab.autoPilotActions.auto-applied");
    case "apply-failed":
      return t("stealthLab.autoPilotActions.apply-failed");
    case "rolled-back":
      return t("stealthLab.autoPilotActions.rolled-back");
    case "idle":
      return t("stealthLab.autoPilotActions.idle");
    default:
      return t("stealthLab.autoPilotActions.recommend");
  }
}

function formatHealthStatus(
  status: string | null | undefined,
  t: ReturnType<typeof useTranslation>["t"]
) {
  switch (status) {
    case "working":
      return t("stealthLab.healthStatuses.working");
    case "degraded":
      return t("stealthLab.healthStatuses.degraded");
    case "failed":
      return t("stealthLab.healthStatuses.failed");
    case "unstable":
      return t("stealthLab.healthStatuses.unstable");
    default:
      return "—";
  }
}

function formatCompareStability(
  status: string | null | undefined,
  t: ReturnType<typeof useTranslation>["t"]
) {
  switch (status) {
    case "working":
      return t("stealthLab.compareStability.working");
    case "degraded":
      return t("stealthLab.compareStability.degraded");
    case "failed":
      return t("stealthLab.compareStability.failed");
    case "unstable":
      return t("stealthLab.compareStability.unstable");
    default:
      return "—";
  }
}

type StealthLabViewMode = "operations" | "research";
type ResearchReadiness = "priority" | "candidate" | "observe" | "blocked";

type ResearchCard = {
  id: "ech-awareness" | "browser-dialer" | "masque-connect-udp";
  title: string;
  readiness: ResearchReadiness;
  summary: string;
  why: string;
  next: string;
  node: string;
  transport: string;
  signals: string[];
  caveats: string[];
};

function formatResearchReadiness(
  readiness: ResearchReadiness,
  t: ReturnType<typeof useTranslation>["t"]
) {
  switch (readiness) {
    case "priority":
      return t("stealthLab.researchStatus.priority");
    case "candidate":
      return t("stealthLab.researchStatus.candidate");
    case "blocked":
      return t("stealthLab.researchStatus.blocked");
    default:
      return t("stealthLab.researchStatus.observe");
  }
}

function looksLikeDomain(host?: string | null) {
  if (!host) {
    return false;
  }

  const candidate = host.trim();
  if (!candidate || candidate.includes(":")) {
    return false;
  }

  if (/^\d{1,3}(?:\.\d{1,3}){3}$/.test(candidate)) {
    return false;
  }

  return /[a-z]/i.test(candidate);
}

function describeResearchTransport(node: ProxyNode | null) {
  if (!node) {
    return "—";
  }

  const transportParts = [
    node.protocol?.toUpperCase(),
    node.network?.toUpperCase(),
    node.tls?.toUpperCase(),
  ].filter(Boolean);

  return transportParts.length > 0 ? transportParts.join(" · ") : node.protocol.toUpperCase();
}

export function StealthLabPage() {
  const { t } = useTranslation();
  const [viewMode, setViewMode] = useState<StealthLabViewMode>("operations");
  const [profiles, setProfiles] = useState<ProxyNode[]>([]);
  const [autoPilotMode, setAutoPilotModeState] =
    useState<StealthAutoPilotMode>("recommend-only");
  const [activeNodeId, setActiveNodeId] = useState<string>("");
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>("");
  const [isProbing, setIsProbing] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [isClearingPolicy, setIsClearingPolicy] = useState(false);
  const [isComparing, setIsComparing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [report, setReport] = useState<CensorshipReport | null>(null);
  const [compareSelection, setCompareSelection] = useState<string[]>([]);
  const [compareReport, setCompareReport] = useState<StealthCompareReport | null>(null);
  const [canRollback, setCanRollback] = useState(false);

  useEffect(() => {
    let unmounted = false;

    void getProfiles().then((result) => {
      if (unmounted) {
        return;
      }

      setProfiles(result);
      if (result.length > 0) {
        setActiveNodeId((current) => current || result[0].id);
      }
    });
    void getStealthAutoPilotMode().then((mode) => {
      if (!unmounted) {
        setAutoPilotModeState(mode);
      }
    });

    const unlisten = listenStealthProbeLog((log: string) => {
      setLogs((prev) => {
        const next = [...prev, log];
        return next.length > 12 ? next.slice(next.length - 12) : next;
      });
    });

    return () => {
      unmounted = true;
      unlisten();
    };
  }, []);

  const activeNode = useMemo(
    () => profiles.find((profile) => profile.id === activeNodeId) ?? null,
    [activeNodeId, profiles]
  );

  const selectedStrategy = useMemo(() => {
    if (!report) {
      return null;
    }

    return report.strategies.find((strategy) => strategy.id === selectedStrategyId) ?? report.strategies[0] ?? null;
  }, [report, selectedStrategyId]);

  const liveHealth = useMemo(
    () => report?.networkPolicy?.last_health ?? report?.networkMemory?.last_health,
    [report]
  );

  const compareCandidates = useMemo(
    () =>
      report?.strategies.filter((strategy) => strategy.readiness !== "manual") ?? [],
    [report]
  );

  const compareWinnerId = useMemo(() => {
    if (!compareReport || compareReport.entries.length === 0) {
      return null;
    }

    const stabilityRank = (status: string) => {
      switch (status) {
        case "working":
          return 4;
        case "degraded":
          return 3;
        case "unstable":
          return 2;
        default:
          return 1;
      }
    };

    return [...compareReport.entries]
      .sort((left, right) => {
        const stabilityDelta =
          stabilityRank(right.stability) - stabilityRank(left.stability);
        if (stabilityDelta !== 0) {
          return stabilityDelta;
        }

        const leftDns = left.dnsSampleCount
          ? left.dnsSuccessCount / left.dnsSampleCount
          : 0;
        const rightDns = right.dnsSampleCount
          ? right.dnsSuccessCount / right.dnsSampleCount
          : 0;
        if (rightDns !== leftDns) {
          return rightDns - leftDns;
        }

        const leftHandshake = left.handshakeSampleCount
          ? left.handshakeSuccessCount / left.handshakeSampleCount
          : 0;
        const rightHandshake = right.handshakeSampleCount
          ? right.handshakeSuccessCount / right.handshakeSampleCount
          : 0;
        if (rightHandshake !== leftHandshake) {
          return rightHandshake - leftHandshake;
        }

        return (left.latencyMs ?? Number.MAX_SAFE_INTEGER) -
          (right.latencyMs ?? Number.MAX_SAFE_INTEGER);
      })[0]?.strategy.id;
  }, [compareReport]);

  const researchNode = useMemo(
    () =>
      (selectedStrategy
        ? profiles.find((profile) => profile.id === selectedStrategy.targetNodeId)
        : null) ?? activeNode,
    [activeNode, profiles, selectedStrategy]
  );

  const researchCards = useMemo<ResearchCard[]>(() => {
    if (!researchNode) {
      return [];
    }

    const findings = report?.findings ?? [];
    const sniFailed = findings.some(
      (finding) => finding.id === "https-sni" && finding.status === "fail"
    );
    const tlsFailed = findings.some(
      (finding) => finding.id === "tls-integrity" && finding.status === "fail"
    );
    const udpFailed = findings.some(
      (finding) => finding.id === "udp-dns" && finding.status === "fail"
    );
    const tcpFailed = findings.some(
      (finding) => finding.id === "node-tcp" && finding.status === "fail"
    );
    const transport = describeResearchTransport(researchNode);
    const browserDialerTransport = (researchNode.network ?? "").toLowerCase();
    const browserDialerSupported =
      browserDialerTransport === "ws" ||
      browserDialerTransport === "websocket" ||
      browserDialerTransport === "xhttp";
    const domainReady = looksLikeDomain(researchNode.server);

    const echReadiness: ResearchReadiness = sniFailed && !tlsFailed
      ? "priority"
      : tlsFailed
        ? "observe"
        : "observe";
    const browserDialerReadiness: ResearchReadiness = browserDialerSupported && domainReady
      ? sniFailed || report?.status === "filtered"
        ? "priority"
        : "candidate"
      : "blocked";
    const masqueReadiness: ResearchReadiness = udpFailed && !sniFailed && !tlsFailed
      ? "priority"
      : udpFailed
        ? "candidate"
        : "observe";

    return [
      {
        id: "ech-awareness",
        title: t("stealthLab.researchCards.ech.title"),
        readiness: echReadiness,
        summary: sniFailed && !tlsFailed
          ? "The current network shows HTTPS/SNI interference without a stronger certificate-interception signal, so ECH is worth tracking as a future privacy and anti-filtering lever."
          : tlsFailed
            ? "TLS interception is the stronger signal on this network, so ECH is not the first research lever to promote."
            : "No strong SNI-only failure pattern is visible right now, so ECH should stay on the watchlist rather than in the active ladder.",
        why: report?.summary ??
          t("stealthLab.researchNoAssessment"),
        next: t("stealthLab.researchCards.ech.next"),
        node: researchNode.name,
        transport,
        signals: [
          `HTTPS/SNI: ${sniFailed ? "fail" : "pass / inconclusive"}`,
          `TLS integrity: ${tlsFailed ? "fail" : "pass / warn"}`,
          `Current assessment: ${report?.status ?? "pending"}`,
        ],
        caveats: [
          "Requires server-side ECH publication and compatible client support before it can become a real desktop route capability.",
          "Research-only: this track does not write policy, memory, or Auto-Pilot decisions.",
        ],
      },
      {
        id: "browser-dialer",
        title: t("stealthLab.researchCards.browserDialer.title"),
        readiness: browserDialerReadiness,
        summary: browserDialerSupported && domainReady
          ? "This route is structurally compatible with browser-dialer-style experiments, so it is a realistic candidate when native client fingerprints keep getting filtered."
          : "The current route is not a good browser-dialer candidate yet because it lacks a browser-friendly transport or uses a non-domain endpoint."
        ,
        why: browserDialerSupported
          ? `Transport ${transport} is close to the WebSocket/XHTTP family that browser dialer experiments require.`
          : "Browser Dialer is only practical with browser-driven HTTP transports such as WebSocket or XHTTP and a direct browser path.",
        next: t("stealthLab.researchCards.browserDialer.next"),
        node: researchNode.name,
        transport,
        signals: [
          `Target address: ${domainReady ? "domain host available" : "IP / unsupported host shape"}`,
          `Transport family: ${browserDialerSupported ? "browser-compatible candidate" : "not browser-compatible"}`,
          `Current assessment: ${report?.status ?? "pending"}`,
        ],
        caveats: [
          "Official Browser Dialer requires a real browser session, direct browser egress, and careful loop avoidance with TUN.",
          "Only WebSocket and XHTTP-style transports are realistic candidates, and there is a real performance overhead.",
        ],
      },
      {
        id: "masque-connect-udp",
        title: t("stealthLab.researchCards.masque.title"),
        readiness: masqueReadiness,
        summary: udpFailed && !sniFailed && !tlsFailed
          ? "UDP is the weakest signal while HTTPS still looks comparatively usable, which makes CONNECT-UDP/MASQUE the most interesting research branch on this network."
          : udpFailed
            ? "UDP is degraded, but the wider filtering picture is mixed. CONNECT-UDP/MASQUE is a candidate, not the lead branch."
            : "Native UDP does not look like the main bottleneck right now, so MASQUE should stay in the background research queue."
        ,
        why: udpFailed
          ? "The baseline UDP/DNS probe failed or degraded, while compare and stealth strategies still lean on HTTP-friendly fallback paths."
          : report?.summary ?? t("stealthLab.researchNoAssessment"),
        next: t("stealthLab.researchCards.masque.next"),
        node: researchNode.name,
        transport,
        signals: [
          `UDP/DNS: ${udpFailed ? "fail" : "pass / warn"}`,
          `HTTPS/SNI: ${sniFailed ? "fail" : "pass / inconclusive"}`,
          `TCP reachability: ${tcpFailed ? "fail" : "pass / inconclusive"}`,
        ],
        caveats: [
          "CONNECT-UDP is useful only when HTTP egress is still viable; it should not be mixed into the main ladder before the engine supports it end-to-end.",
          "Research-only: this track does not auto-apply and does not change stealth posture or route memory.",
        ],
      },
    ];
  }, [activeNode, profiles, report, researchNode, selectedStrategy, t]);

  const statusTone = useMemo(() => {
    if (!report) {
      return {
        label: t("stealthLab.awaitingCommand"),
        badge: "border-white/10 text-muted-foreground bg-black/30",
      };
    }

    switch (report.status) {
      case "intercepted":
        return {
          label: t("stealthLab.statusIntercepted"),
          badge: "border-red-500/40 bg-red-500/10 text-red-300",
        };
      case "filtered":
        return {
          label: t("stealthLab.statusFiltered"),
          badge: "border-[#ff00ff]/40 bg-[#ff00ff]/10 text-[#ff9dff]",
        };
      case "degraded":
        return {
          label: t("stealthLab.statusDegraded"),
          badge: "border-amber-500/40 bg-amber-500/10 text-amber-200",
        };
      default:
        return {
          label: t("stealthLab.statusClear"),
          badge: "border-[var(--color-matrix-green)]/40 bg-[var(--color-matrix-green)]/10 text-[var(--color-matrix-green)]",
        };
    }
  }, [report, t]);

  const handleStartDiagnostics = async () => {
    if (!activeNode) {
      toast.error(t("stealthLab.noNode"));
      return;
    }

    setIsProbing(true);
    setLogs([]);
    setReport(null);
    setCompareReport(null);
    setCompareSelection([]);

    try {
      const result = await runStealthDiagnostics(activeNode.id);
      setReport(result);
      setSelectedStrategyId(
        result.autoPilot?.strategyId ??
          result.recommendedStrategyId ??
          result.strategies[0]?.id ??
          ""
      );
      setCompareSelection(
        result.strategies
          .filter((strategy) => strategy.readiness !== "manual")
          .slice(0, 2)
          .map((strategy) => strategy.id)
      );
      setCanRollback(result.rollbackAvailable);
      if (result.autoPilot?.action === "auto-applied") {
        toast.success(result.autoPilot.message ?? t("stealthLab.autoPilotApplied"));
      } else if (result.autoPilot?.action === "rolled-back") {
        toast.error(result.autoPilot.message ?? t("stealthLab.autoPilotRolledBack"));
      } else if (result.autoPilot?.action === "apply-failed") {
        toast.error(result.autoPilot.message ?? t("stealthLab.autoPilotApplyFailed"));
      }
      toast.success(t("stealthLab.diagnosticComplete"));
    } catch (error: unknown) {
      toast.error(
        t("stealthLab.diagnosticFailed", { error: error instanceof Error ? error.message : String(error) })
      );
    } finally {
      setIsProbing(false);
    }
  };

  const handleAutoPilotModeChange = async (mode: StealthAutoPilotMode) => {
    try {
      const normalizedMode = await setStealthAutoPilotMode(mode);
      setAutoPilotModeState(normalizedMode);
      toast.success(
        t("stealthLab.autoPilotModeSaved", {
          mode: formatAutoPilotMode(normalizedMode, t),
        })
      );
    } catch (error: unknown) {
      toast.error(
        t("stealthLab.autoPilotModeSaveFailed", {
          error: error instanceof Error ? error.message : String(error),
        })
      );
    }
  };

  const toggleCompareStrategy = (strategyId: string) => {
    setCompareSelection((current) => {
      if (current.includes(strategyId)) {
        return current.filter((id) => id !== strategyId);
      }

      if (current.length >= 3) {
        toast.error(t("stealthLab.compareSelectionLimit"));
        return current;
      }

      return [...current, strategyId];
    });
  };

  const handleApplyRecommendation = async () => {
    if (!report || !activeNode || !selectedStrategy || selectedStrategy.readiness !== "ready") {
      return;
    }

    setIsApplying(true);
    try {
      const result = await applyStealthFix(activeNode.id, selectedStrategy.id);
      setCanRollback(result.rollbackAvailable);
      setReport((current) =>
        current && selectedStrategy
          ? {
              ...current,
              networkPolicy: {
                strategy_id: selectedStrategy.id,
                strategy_title: selectedStrategy.title,
                target_node_id: selectedStrategy.targetNodeId,
                target_node_name: selectedStrategy.targetNodeName,
                enable_stealth_mode: selectedStrategy.enableStealthMode,
                saved_at: Date.now(),
                last_health: result.health
                  ? {
                      checked_at: result.health.checkedAt,
                      status: result.health.status,
                      summary: result.health.summary,
                      success_count: result.health.successCount,
                      sample_count: result.health.sampleCount,
                      median_first_byte_latency_ms: result.health.medianFirstByteLatencyMs,
                    }
                  : current.networkPolicy?.last_health,
              },
              networkMemory: current.networkMemory
                ? {
                    ...current.networkMemory,
                    last_applied_recommendation_id: selectedStrategy.id,
                    last_applied_at: Date.now(),
                    last_known_good_node_id:
                      result.health?.status === "working"
                        ? selectedStrategy.targetNodeId
                        : current.networkMemory.last_known_good_node_id,
                    last_known_good_node_name:
                      result.health?.status === "working"
                        ? selectedStrategy.targetNodeName
                        : current.networkMemory.last_known_good_node_name,
                    last_known_good_strategy_id:
                      result.health?.status === "working"
                        ? selectedStrategy.id
                        : current.networkMemory.last_known_good_strategy_id,
                    last_known_good_strategy_title:
                      result.health?.status === "working"
                        ? selectedStrategy.title
                        : current.networkMemory.last_known_good_strategy_title,
                    last_known_good_stealth_mode_enabled:
                      result.health?.status === "working"
                        ? selectedStrategy.enableStealthMode
                        : current.networkMemory.last_known_good_stealth_mode_enabled,
                    last_health: result.health
                      ? {
                          checked_at: result.health.checkedAt,
                          status: result.health.status,
                          summary: result.health.summary,
                          success_count: result.health.successCount,
                          sample_count: result.health.sampleCount,
                          median_first_byte_latency_ms:
                            result.health.medianFirstByteLatencyMs,
                        }
                      : current.networkMemory.last_health,
                  }
                : current.networkMemory,
            }
          : current
      );
      toast.success(result.message);
    } catch (error: unknown) {
      toast.error(t("stealthLab.fixFailed", { error: error instanceof Error ? error.message : String(error) }));
    } finally {
      setIsApplying(false);
    }
  };

  const handleClearPolicy = async () => {
    setIsClearingPolicy(true);
    try {
      const updatedProfile = await clearNetworkStealthPolicy();
      setReport((current) =>
        current
          ? {
              ...current,
              networkPolicy: updatedProfile.stealth_policy,
            }
          : current
      );
      toast.success(t("stealthLab.policyCleared"));
    } catch (error: unknown) {
      toast.error(
        t("stealthLab.policyClearFailed", { error: error instanceof Error ? error.message : String(error) })
      );
    } finally {
      setIsClearingPolicy(false);
    }
  };

  const handleRollback = async () => {
    setIsRollingBack(true);
    try {
      const result = await rollbackLastStealthFix();
      setCanRollback(result.rollbackAvailable);
      if (report?.networkName) {
        const rules = await getNetworkRules();
        const profile = rules[report.networkName];
        setReport((current) =>
          current
            ? {
                ...current,
                networkPolicy: profile?.stealth_policy,
                networkMemory: profile?.stealth_memory ?? current.networkMemory,
              }
            : current
        );
      }
      toast.success(result.message);
    } catch (error: unknown) {
      toast.error(
        t("stealthLab.rollbackFailed", { error: error instanceof Error ? error.message : String(error) })
      );
    } finally {
      setIsRollingBack(false);
    }
  };

  const handleRunCompare = async () => {
    if (!activeNode || compareSelection.length < 2 || compareSelection.length > 3) {
      toast.error(t("stealthLab.compareSelectionHint"));
      return;
    }

    setIsComparing(true);
    setCompareReport(null);
    try {
      const result = await compareStealthStrategies(activeNode.id, compareSelection);
      setCompareReport(result);
      if (result.restoredConnection) {
        toast.success(t("stealthLab.compareComplete"));
      } else {
        toast.error(
          result.restoreMessage ?? t("stealthLab.compareRestoreFailed")
        );
      }
    } catch (error: unknown) {
      toast.error(
        t("stealthLab.compareFailed", {
          error: error instanceof Error ? error.message : String(error),
        })
      );
    } finally {
      setIsComparing(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="p-8 max-w-7xl mx-auto space-y-6 min-h-full pb-24"
    >
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-[#ff00ff]/20 pb-6">
        <div className="space-y-3">
          <h1 className="text-4xl font-black text-white tracking-widest uppercase flex items-center gap-4">
            <ShieldAlert size={34} className="text-[#ff00ff]" />
            {t("stealthLab.title")}
          </h1>
          <p className="text-muted-foreground max-w-3xl text-lg">
            {t("stealthLab.phase4Subtitle")}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className={`rounded-xl border px-4 py-2 text-xs font-mono uppercase tracking-[0.3em] ${statusTone.badge}`}>
            {statusTone.label}
          </div>
          {report && (
            <div className="rounded-xl border border-white/10 bg-black/40 px-4 py-2 text-xs font-mono uppercase tracking-[0.25em] text-muted-foreground">
              {t("stealthLab.confidence")}:{" "}
              <span className="text-white">{report.confidence}%</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => setViewMode("operations")}
          className={`rounded-xl border px-4 py-3 text-sm font-mono uppercase tracking-[0.25em] transition-colors ${
            viewMode === "operations"
              ? "border-[#00ffff]/40 bg-[#00ffff]/10 text-white"
              : "border-white/10 bg-black/25 text-muted-foreground hover:border-white/20"
          }`}
        >
          {t("stealthLab.operationsView")}
        </button>
        <button
          type="button"
          onClick={() => setViewMode("research")}
          className={`rounded-xl border px-4 py-3 text-sm font-mono uppercase tracking-[0.25em] transition-colors ${
            viewMode === "research"
              ? "border-[#ff00ff]/40 bg-[#ff00ff]/10 text-white"
              : "border-white/10 bg-black/25 text-muted-foreground hover:border-white/20"
          }`}
        >
          {t("stealthLab.researchView")}
        </button>
      </div>

      {viewMode === "operations" && (
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <section className="xl:col-span-3 rounded-2xl border border-white/10 bg-black/35 backdrop-blur-md p-6 space-y-5">
          <div className="space-y-2">
            <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-[#00ffff]">
              {t("stealthLab.scope")}
            </div>
            <h2 className="text-xl font-bold text-white">{t("stealthLab.scopeTitle")}</h2>
            <p className="text-sm text-muted-foreground">
              {t("stealthLab.scopeDesc")}
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-mono uppercase tracking-[0.25em] text-muted-foreground">
              {t("stealthLab.nodeSelector")}
            </label>
            <select
              value={activeNodeId}
              onChange={(event) => {
                setActiveNodeId(event.target.value);
                setReport(null);
                setSelectedStrategyId("");
                setCompareSelection([]);
                setCompareReport(null);
              }}
              className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-[#00ffff]"
            >
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name} · {profile.protocol.toUpperCase()} · {profile.server}:{profile.port}
                </option>
              ))}
            </select>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/40 p-4 space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <Network size={16} className="text-[#00ffff]" />
              {t("stealthLab.currentNetwork")}
            </div>
            <p className="text-sm text-muted-foreground">
              {report?.networkName ?? t("stealthLab.networkPending")}
            </p>
            <p className="text-xs text-muted-foreground">
              {report
                ? t("stealthLab.lastAssessmentAt", {
                    timestamp: formatTimestamp(report.assessedAt),
                  })
                : t("stealthLab.networkAssessmentHint")}
            </p>
          </div>

          <button
            onClick={() => void handleStartDiagnostics()}
            disabled={isProbing || !activeNode}
            className="w-full rounded-xl border border-[#ff00ff]/40 bg-[#ff00ff]/10 px-4 py-4 font-mono text-sm font-bold uppercase tracking-[0.25em] text-[#ff9dff] transition-all hover:bg-[#ff00ff]/16 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isProbing ? t("stealthLab.probing") : t("stealthLab.initiateSweep")}
          </button>
        </section>

        <section className="xl:col-span-5 rounded-2xl border border-white/10 bg-black/35 backdrop-blur-md p-6 space-y-5">
          <div className="space-y-2">
            <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-[#00ffff]">
              {t("stealthLab.honestAssessment")}
            </div>
            <h2 className="text-xl font-bold text-white">{t("stealthLab.assessmentTitle")}</h2>
            <p className="text-sm text-muted-foreground">
              {report ? report.summary : t("stealthLab.assessmentPending")}
            </p>
          </div>

          {report ? (
            <div className="space-y-3">
              {report.findings.map((finding) => {
                const findingTone =
                  finding.status === "pass"
                    ? "border-[var(--color-matrix-green)]/30 bg-[var(--color-matrix-green)]/8"
                    : finding.status === "fail"
                      ? "border-red-500/30 bg-red-500/8"
                      : finding.status === "warn"
                        ? "border-amber-500/30 bg-amber-500/8"
                        : "border-white/10 bg-white/5";

                return (
                  <div key={finding.id} className={`rounded-2xl border p-4 ${findingTone}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold text-white">{finding.label}</div>
                        <div className="mt-1 text-sm text-muted-foreground">{finding.summary}</div>
                      </div>
                      <div className="shrink-0 rounded-full border border-white/10 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-white/80">
                        {finding.status}
                      </div>
                    </div>
                    <p className="mt-3 text-xs text-muted-foreground">{finding.detail}</p>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-white/10 bg-black/20 p-8 text-center text-muted-foreground">
              <Activity size={32} className="mx-auto mb-3 opacity-60" />
              <p className="font-mono text-sm uppercase tracking-[0.25em]">
                {t("stealthLab.awaitingCommand")}
              </p>
            </div>
          )}
        </section>

        <section className="xl:col-span-4 rounded-2xl border border-white/10 bg-black/35 backdrop-blur-md p-6 space-y-5">
          <div className="space-y-2">
            <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-[#00ffff]">
              {t("stealthLab.strategyLadder")}
            </div>
            <h2 className="text-xl font-bold text-white">
              {selectedStrategy?.title ?? t("stealthLab.recommendationPending")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {selectedStrategy?.summary ?? t("stealthLab.strategyLadderHint")}
            </p>
          </div>

          {report ? (
            <div className="space-y-3">
              {report.strategies.map((strategy) => {
                const isSelected = selectedStrategy?.id === strategy.id;
                const isRecommended = report.recommendedStrategyId === strategy.id;
                const cardTone =
                  strategy.readiness === "ready"
                    ? "border-[#00ffff]/20 bg-[#00ffff]/5"
                    : strategy.readiness === "noop"
                      ? "border-[var(--color-matrix-green)]/20 bg-[var(--color-matrix-green)]/5"
                      : "border-amber-500/20 bg-amber-500/5";

                return (
                  <button
                    key={strategy.id}
                    type="button"
                    onClick={() => setSelectedStrategyId(strategy.id)}
                    className={`w-full rounded-2xl border p-4 text-left transition-all ${cardTone} ${
                      isSelected ? "ring-1 ring-[#ff00ff]/50 shadow-[0_0_0_1px_rgba(255,0,255,0.2)]" : "hover:border-white/20"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-2 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="text-sm font-semibold text-white">
                            #{strategy.rank} · {strategy.title}
                          </div>
                          {isRecommended && (
                            <span className="rounded-full border border-[#ff00ff]/40 bg-[#ff00ff]/10 px-2 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-[#ff9dff]">
                              {t("stealthLab.recommended")}
                            </span>
                          )}
                          {isSelected && (
                            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-white/80">
                              {t("stealthLab.selected")}
                            </span>
                          )}
                        </div>
                        <div className="text-xs font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                          {formatTierLabel(strategy.tier, t)}
                        </div>
                        <p className="text-sm text-muted-foreground">{strategy.summary}</p>
                      </div>
                      <div className="shrink-0 rounded-full border border-white/10 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-white/80">
                        {strategy.readiness}
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                        <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                          {t("stealthLab.strategyTarget")}
                        </div>
                        <div className="mt-2 text-sm font-semibold text-white">{strategy.targetNodeName}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {strategy.targetProtocol.toUpperCase()} · {strategy.enableStealthMode ? t("stealthLab.camouflageOn") : t("stealthLab.camouflageOff")}
                        </div>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                        <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                          {t("stealthLab.strategyTradeoff")}
                        </div>
                        <div className="mt-2 text-sm text-muted-foreground">{strategy.tradeoff}</div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-white/10 bg-black/20 p-6 text-center text-muted-foreground">
              <p className="font-mono text-sm uppercase tracking-[0.25em]">
                {t("stealthLab.recommendationPending")}
              </p>
            </div>
          )}

          {selectedStrategy && (
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4 space-y-4">
              <div className="space-y-2">
                <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                  {t("stealthLab.previewTitle")}
                </div>
                <div className="text-sm font-semibold text-white">
                  {selectedStrategy.title} · {selectedStrategy.targetNodeName}
                </div>
                <p className="text-sm text-muted-foreground">{selectedStrategy.reason}</p>
              </div>

              {selectedStrategy.previewChanges.length > 0 ? (
                <div className="space-y-2">
                  {selectedStrategy.previewChanges.map((change) => (
                    <div
                      key={`${selectedStrategy.id}-${change.scope}-${change.field}`}
                      className="rounded-xl border border-white/10 bg-black/30 p-3"
                    >
                      <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                        {change.scope}
                      </div>
                      <div className="mt-2 text-sm font-semibold text-white">{change.field}</div>
                      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{change.from}</span>
                        <ChevronRight size={12} />
                        <span className="text-white">{change.to}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-white/10 bg-black/30 p-3 text-sm text-muted-foreground">
                  {t("stealthLab.previewNoDiff")}
                </div>
              )}
            </div>
          )}

          <div className="rounded-2xl border border-white/10 bg-black/30 p-4 space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <Sparkles size={16} className="text-[#00ffff]" />
                {t("stealthLab.autoPilot2")}
              </div>
              <p className="text-sm text-muted-foreground">
                {t("stealthLab.autoPilot2Hint")}
              </p>
            </div>

            <select
              value={autoPilotMode}
              onChange={(event) =>
                void handleAutoPilotModeChange(
                  event.target.value as StealthAutoPilotMode
                )
              }
              className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-[#00ffff]"
            >
              <option value="recommend-only">
                {formatAutoPilotMode("recommend-only", t)}
              </option>
              <option value="ask-before-apply">
                {formatAutoPilotMode("ask-before-apply", t)}
              </option>
              <option value="auto-apply-trusted">
                {formatAutoPilotMode("auto-apply-trusted", t)}
              </option>
              <option value="auto-apply-with-rollback">
                {formatAutoPilotMode("auto-apply-with-rollback", t)}
              </option>
            </select>

            <div className="rounded-xl border border-white/10 bg-black/40 p-4 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-white/80">
                  {formatAutoPilotMode(autoPilotMode, t)}
                </span>
                {report?.autoPilot?.trustedPattern && (
                  <span className="rounded-full border border-[var(--color-matrix-green)]/30 bg-[var(--color-matrix-green)]/8 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-[var(--color-matrix-green)]">
                    {t("stealthLab.autoPilotTrusted")}
                  </span>
                )}
              </div>

              <p className="text-sm text-white">
                {describeAutoPilot(report?.autoPilot, t)}
              </p>

              {report?.autoPilot?.strategyTitle && (
                <div className="text-sm text-muted-foreground">
                  {t("stealthLab.autoPilotStrategy", {
                    strategy: report.autoPilot.strategyTitle,
                    node: report.autoPilot.targetNodeName ?? "—",
                  })}
                </div>
              )}

              {report?.autoPilot?.message && (
                <div className="rounded-xl border border-white/10 bg-black/30 p-3 text-xs text-muted-foreground">
                  {report.autoPilot.message}
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/30 p-4 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-white">
                  {t("stealthLab.networkPolicy")}
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {t("stealthLab.networkPolicyHint")}
                </p>
              </div>
              <button
                onClick={() => void handleClearPolicy()}
                disabled={isClearingPolicy || !report?.networkPolicy?.strategy_id}
                className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-[0.25em] text-white transition-colors hover:border-white/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isClearingPolicy ? t("stealthLab.policyClearing") : t("stealthLab.clearPolicy")}
              </button>
            </div>

            {report?.networkPolicy?.strategy_id ? (
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="text-white font-semibold">
                  {report.networkPolicy.strategy_title ?? t("stealthLab.policyPinned")}
                </div>
                <div>
                  {t("stealthLab.policyNode", {
                    node: report.networkPolicy.target_node_name ?? "—",
                  })}
                </div>
                <div>
                  {report.networkPolicy.enable_stealth_mode
                    ? t("stealthLab.camouflageOn")
                    : t("stealthLab.camouflageOff")}
                </div>
                <div>
                  {t("stealthLab.policySavedAt", {
                    timestamp: formatTimestamp(report.networkPolicy.saved_at),
                  })}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t("stealthLab.networkPolicyEmpty")}</p>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/30 p-4 space-y-3">
            <div className="text-sm font-semibold text-white">
              {t("stealthLab.networkMemory")}
            </div>
            {report?.networkMemory ? (
              <div className="space-y-2 text-sm text-muted-foreground">
                <div>
                  {t("stealthLab.lastAssessmentAt", {
                    timestamp: formatTimestamp(report.networkMemory.last_assessed_at),
                  })}
                </div>
                <div>
                  {t("stealthLab.lastNetworkStatus", {
                    status: report.networkMemory.last_status ?? "—",
                  })}
                </div>
                <div>{report.networkMemory.last_summary ?? "—"}</div>
                {report.networkMemory.last_known_good_node_name && (
                  <div>
                    {t("stealthLab.lastKnownGood", {
                      node: report.networkMemory.last_known_good_node_name,
                    })}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t("stealthLab.networkMemoryEmpty")}</p>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/30 p-4 space-y-3">
            <div className="text-sm font-semibold text-white">
              {t("stealthLab.liveHealth")}
            </div>
            {liveHealth?.status ? (
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="text-white font-semibold">
                  {formatHealthStatus(liveHealth.status, t)}
                </div>
                <div>{liveHealth.summary ?? "—"}</div>
                <div>
                  {t("stealthLab.healthCheckedAt", {
                    timestamp: formatTimestamp(liveHealth.checked_at),
                  })}
                </div>
                <div>
                  {t("stealthLab.healthPassCount", {
                    success: liveHealth.success_count ?? 0,
                    total: liveHealth.sample_count ?? 0,
                  })}
                </div>
                <div>
                  {t("stealthLab.healthMedianFirstByte", {
                    latency:
                      liveHealth.median_first_byte_latency_ms != null
                        ? `${liveHealth.median_first_byte_latency_ms} ms`
                        : "—",
                  })}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                {t("stealthLab.liveHealthEmpty")}
              </p>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/30 p-4 space-y-4">
            <div className="space-y-2">
              <div className="text-sm font-semibold text-white">
                {t("stealthLab.compareMode")}
              </div>
              <p className="text-sm text-muted-foreground">
                {t("stealthLab.compareModeHint")}
              </p>
            </div>

            {compareCandidates.length > 0 ? (
              <>
                <div className="flex flex-wrap gap-2">
                  {compareCandidates.map((strategy) => {
                    const selectedForCompare = compareSelection.includes(strategy.id);

                    return (
                      <button
                        key={`compare-${strategy.id}`}
                        type="button"
                        onClick={() => toggleCompareStrategy(strategy.id)}
                        className={`rounded-xl border px-3 py-2 text-left transition-colors ${
                          selectedForCompare
                            ? "border-[#00ffff]/40 bg-[#00ffff]/10 text-white"
                            : "border-white/10 bg-black/30 text-muted-foreground hover:border-white/20"
                        }`}
                      >
                        <div className="text-xs font-mono uppercase tracking-[0.25em]">
                          {formatTierLabel(strategy.tier, t)}
                        </div>
                        <div className="mt-1 text-sm font-semibold">
                          {strategy.title}
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="rounded-xl border border-white/10 bg-black/40 p-3 text-sm text-muted-foreground">
                  {t("stealthLab.compareSelectedCount", {
                    count: compareSelection.length,
                    max: 3,
                  })}
                </div>

                <button
                  onClick={() => void handleRunCompare()}
                  disabled={
                    isComparing ||
                    compareSelection.length < 2 ||
                    compareSelection.length > 3
                  }
                  className="w-full rounded-xl border border-[#00ffff]/30 bg-[#00ffff]/10 px-4 py-3 font-mono text-xs font-bold uppercase tracking-[0.25em] text-[#a5ffff] transition-colors hover:bg-[#00ffff]/16 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isComparing
                    ? t("stealthLab.comparing")
                    : t("stealthLab.runCompare")}
                </button>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                {t("stealthLab.compareModeEmpty")}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-3">
            <button
              onClick={() => void handleApplyRecommendation()}
              disabled={
                isApplying ||
                !selectedStrategy ||
                selectedStrategy.readiness !== "ready" ||
                !activeNode
              }
              className="w-full rounded-xl bg-white px-4 py-4 font-bold uppercase tracking-[0.25em] text-black transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isApplying
                ? t("stealthLab.applyingFix")
                : selectedStrategy?.actionLabel ?? t("stealthLab.fixItForMe")}
            </button>

            <button
              onClick={() => void handleRollback()}
              disabled={isRollingBack || !canRollback}
              className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 font-mono text-xs font-bold uppercase tracking-[0.25em] text-white transition-colors hover:border-white/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span className="inline-flex items-center gap-2">
                <RotateCcw size={14} />
                {isRollingBack ? t("stealthLab.rollbacking") : t("stealthLab.rollback")}
              </span>
            </button>
          </div>

          {selectedStrategy && selectedStrategy.readiness === "manual" && (
            <div className="rounded-2xl border border-amber-500/30 bg-amber-500/8 p-4 text-sm text-amber-100">
              <div className="flex items-center gap-2 font-semibold">
                <ShieldQuestion size={16} />
                {t("stealthLab.manualReview")}
              </div>
              <p className="mt-2 text-amber-50/80">{selectedStrategy.summary}</p>
            </div>
          )}

          {selectedStrategy && selectedStrategy.readiness === "noop" && (
            <div className="rounded-2xl border border-[var(--color-matrix-green)]/30 bg-[var(--color-matrix-green)]/8 p-4 text-sm text-[var(--color-matrix-green)]">
              <div className="flex items-center gap-2 font-semibold">
                <CheckCircle2 size={16} />
                {t("stealthLab.noopRecommendation")}
              </div>
              <p className="mt-2 text-white/70">{selectedStrategy.summary}</p>
            </div>
          )}
        </section>
      </div>
      )}

      {viewMode === "operations" && compareReport && (
        <section className="rounded-2xl border border-white/10 bg-black/25 p-6 space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-[#00ffff]">
                {t("stealthLab.compareResults")}
              </div>
              <h2 className="text-2xl font-bold text-white">
                {t("stealthLab.compareResultsTitle", {
                  node: compareReport.nodeName,
                })}
              </h2>
              <p className="text-sm text-muted-foreground">
                {compareReport.restoredConnection
                  ? t("stealthLab.compareRestored")
                  : compareReport.restoreMessage ??
                    t("stealthLab.compareRestoreFailed")}
              </p>
            </div>

            <div className="rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-xs font-mono uppercase tracking-[0.25em] text-muted-foreground">
              {t("stealthLab.lastAssessmentAt", {
                timestamp: formatTimestamp(compareReport.assessedAt),
              })}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            {compareReport.entries.map((entry) => {
              const isWinner = compareWinnerId === entry.strategy.id;

              return (
                <div
                  key={`compare-entry-${entry.strategy.id}`}
                  className={`rounded-2xl border p-5 space-y-4 ${
                    isWinner
                      ? "border-[#ff00ff]/35 bg-[#ff00ff]/8"
                      : "border-white/10 bg-black/35"
                  }`}
                >
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="text-sm font-semibold text-white">
                        {entry.strategy.title}
                      </div>
                      {isWinner && (
                        <span className="rounded-full border border-[#ff00ff]/40 bg-[#ff00ff]/10 px-2 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-[#ff9dff]">
                          {t("stealthLab.compareWinner")}
                        </span>
                      )}
                    </div>
                    <div className="text-xs font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                      {formatTierLabel(entry.strategy.tier, t)} ·{" "}
                      {entry.strategy.targetNodeName}
                    </div>
                    <p className="text-sm text-muted-foreground">{entry.summary}</p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                      <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                        {t("stealthLab.compareLatency")}
                      </div>
                      <div className="mt-2 text-sm font-semibold text-white">
                        {entry.latencyMs != null ? `${entry.latencyMs} ms` : "—"}
                      </div>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                      <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                        {t("stealthLab.compareStabilityLabel")}
                      </div>
                      <div className="mt-2 text-sm font-semibold text-white">
                        {formatCompareStability(entry.stability, t)}
                      </div>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                      <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                        {t("stealthLab.compareDns")}
                      </div>
                      <div className="mt-2 text-sm font-semibold text-white">
                        {entry.dnsSuccessCount} / {entry.dnsSampleCount}
                      </div>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                      <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                        {t("stealthLab.compareHandshake")}
                      </div>
                      <div className="mt-2 text-sm font-semibold text-white">
                        {entry.handshakeSuccessCount} / {entry.handshakeSampleCount}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {entry.probes.map((probe) => (
                      <div
                        key={`${entry.strategy.id}-${probe.id}`}
                        className="rounded-xl border border-white/10 bg-black/25 p-3"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold text-white">
                              {probe.label}
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">
                              {probe.summary}
                            </div>
                          </div>
                          <div className="rounded-full border border-white/10 px-2 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-white/80">
                            {probe.category} · {probe.status}
                          </div>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                          {probe.detail}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {viewMode === "research" && (
        <section className="space-y-6">
          <div className="rounded-2xl border border-white/10 bg-black/30 p-6 space-y-3">
            <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-[#ff00ff]">
              {t("stealthLab.researchTrack")}
            </div>
            <h2 className="text-2xl font-bold text-white">
              {t("stealthLab.researchTrack")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("stealthLab.researchTrackHint")}
            </p>
          </div>

          <div className="rounded-2xl border border-[#ff00ff]/20 bg-[#ff00ff]/6 p-5 space-y-3">
            <div className="text-sm font-semibold text-white">
              {t("stealthLab.researchGuardrails")}
            </div>
            <p className="text-sm text-muted-foreground">
              {t("stealthLab.researchGuardrailsHint")}
            </p>
          </div>

          {!report && (
            <div className="rounded-2xl border border-white/10 bg-black/25 p-5 text-sm text-muted-foreground">
              {t("stealthLab.researchNoAssessment")}
            </div>
          )}

          <div className="grid gap-5 xl:grid-cols-3">
            {researchCards.map((card) => (
              <div
                key={card.id}
                className="rounded-2xl border border-white/10 bg-black/30 p-5 space-y-4"
              >
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-lg font-semibold text-white">{card.title}</div>
                    <span className="rounded-full border border-white/10 bg-black/35 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-white/80">
                      {formatResearchReadiness(card.readiness, t)}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{card.summary}</p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-white/10 bg-black/25 p-3">
                    <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                      {t("stealthLab.researchNode")}
                    </div>
                    <div className="mt-2 text-sm font-semibold text-white">
                      {card.node}
                    </div>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/25 p-3">
                    <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                      {t("stealthLab.researchTransport")}
                    </div>
                    <div className="mt-2 text-sm font-semibold text-white">
                      {card.transport}
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-white/10 bg-black/25 p-4 space-y-2">
                  <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                    {t("stealthLab.researchSignals")}
                  </div>
                  <div className="text-sm text-muted-foreground">{card.why}</div>
                  <div className="space-y-1 text-xs text-muted-foreground">
                    {card.signals.map((signal) => (
                      <div key={`${card.id}-${signal}`}>{signal}</div>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-white/10 bg-black/25 p-4 space-y-2">
                  <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                    {t("stealthLab.researchNext")}
                  </div>
                  <div className="text-sm text-muted-foreground">{card.next}</div>
                </div>

                <div className="rounded-xl border border-white/10 bg-black/25 p-4 space-y-2">
                  <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-[#00ffff]">
                    {t("stealthLab.researchCaveats")}
                  </div>
                  <div className="space-y-1 text-sm text-muted-foreground">
                    {card.caveats.map((caveat) => (
                      <div key={`${card.id}-${caveat}`}>{caveat}</div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {viewMode === "operations" && (
      <details className="rounded-2xl border border-white/10 bg-black/25 p-5">
        <summary className="cursor-pointer list-none text-sm font-mono uppercase tracking-[0.25em] text-[#00ffff]">
          {t("stealthLab.rawLogs")}
        </summary>
        <div className="mt-4 space-y-2">
          {logs.length > 0 ? (
            logs.map((log, index) => (
              <div
                key={`${index}-${log}`}
                className="rounded-lg border border-white/5 bg-black/35 px-3 py-2 font-mono text-xs text-muted-foreground"
              >
                {log}
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">{t("stealthLab.logsEmpty")}</p>
          )}
        </div>
      </details>
      )}
    </motion.div>
  );
}
