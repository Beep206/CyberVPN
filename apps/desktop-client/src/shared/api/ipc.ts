import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

// TypeScript matches Rust `ProxyNode`
export interface ProxyNode {
  id: string;
  name: string;
  server: string;
  port: number;
  protocol: string;
  uuid?: string;
  password?: string;
  flow?: string;
  network?: string;
  tls?: string;
  sni?: string;
  fingerprint?: string;
  publicKey?: string;
  shortId?: string;
  ping?: number;
  nextHopId?: string;
  alterId?: number;
  security?: string;
  method?: string;
  obfs?: string;
  obfsPassword?: string;
  upMbps?: number;
  downMbps?: number;
  alpn?: string[];
  subscriptionId?: string;
  congestionControl?: string;
  udpRelayMode?: string;
  localAddress?: string[];
  privateKey?: string;
  peerPublicKey?: string;
  mtu?: number;
  preSharedKey?: string;
  reserved?: number[];
  allowedIps?: string[];
  persistentKeepaliveInterval?: number;
  listenPort?: number;
  tailscaleAuthKey?: string;
  tailscaleControlUrl?: string;
  tailscaleStateDirectory?: string;
  tailscaleHostname?: string;
  tailscaleEphemeral?: boolean;
  tailscaleAcceptRoutes?: boolean;
  tailscaleExitNode?: string;
  tailscaleExitNodeAllowLanAccess?: boolean;
  tailscaleAdvertiseRoutes?: string[];
  tailscaleAdvertiseExitNode?: boolean;
  tailscaleSystemInterface?: boolean;
  tailscaleSystemInterfaceName?: string;
  tailscaleSystemInterfaceMtu?: number;
  tailscaleUdpTimeout?: string;
  tailscaleRelayServerPort?: number;
  tailscaleRelayServerStaticEndpoints?: string[];
  mux?: string;
  groupId?: string;
  plugin?: string;
  pluginOpts?: string;
  tlsFragment?: boolean;
  tlsRecordFragment?: boolean;
  pqcEnabled?: boolean;
}

export interface RoutingRule {
  id: string;
  enabled: boolean;
  domains: string[];
  ips: string[];
  outbound: string;
}

export interface ConnectionStatus {
  status:
    | "disconnected"
    | "connecting"
    | "connected"
    | "disconnecting"
    | "degraded"
    | "error";
  activeId?: string | null;
  activeCore?: string | null;
  proxyUrl?: string | null;
  message?: string | null;
  upBytes: number;
  downBytes: number;
}

export interface LastConnectionOptions {
  profileId?: string | null;
  tunMode: boolean;
  systemProxy: boolean;
  activeCore: string;
  sourceSurface: string;
  favoriteProfileIds?: string[];
  lastStableProfileId?: string | null;
  lastStableConnectedAt?: number | null;
  lastAction?: string | null;
  lastRequestedAt?: number | null;
  lastConnectedAt?: number | null;
  lastDisconnectedAt?: number | null;
}

/** Get all saved proxy profiles */
export const getProfiles = async (): Promise<ProxyNode[]> => {
  return await invoke<ProxyNode[]>("get_profiles");
};

/** Add a new proxy profile */
export const addProfile = async (profile: ProxyNode): Promise<void> => {
  return await invoke("add_profile", { profile });
};

/** Connect to a proxy profile */
export const connectProfile = async (
  id: string,
  tunMode: boolean,
  systemProxy = false,
  sourceSurface = "dashboard"
): Promise<void> => {
  return await invoke("connect_profile", { id, tunMode, systemProxy, sourceSurface });
};

/** Disconnect the active proxy */
export const disconnectProxy = async (sourceSurface = "dashboard"): Promise<void> => {
  return await invoke("disconnect", { sourceSurface });
};

/** Get the current engine connection status */
export const getConnectionStatus = async (): Promise<ConnectionStatus> => {
  return await invoke<ConnectionStatus>("get_connection_status");
};

/** Listen for real-time connection status updates securely from Rust */
export const listenConnectionStatus = async (
  callback: (status: ConnectionStatus) => void
) => {
  return await listen<ConnectionStatus>("connection-status", (event) => {
    callback(event.payload);
  });
};

export const getLastConnectionOptions = async (): Promise<LastConnectionOptions> => {
  return await invoke<LastConnectionOptions>("get_last_connection_options");
};

export const saveLastConnectionOptions = async (
  options: LastConnectionOptions
): Promise<LastConnectionOptions> => {
  return await invoke<LastConnectionOptions>("save_last_connection_options", { options });
};

export const listenConnectionOptions = async (
  callback: (options: LastConnectionOptions) => void
) => {
  return await listen<LastConnectionOptions>("connection-options", (event) => {
    callback(event.payload);
  });
};

export const testAllLatencies = async (): Promise<void> => {
  return await invoke("test_all_latencies");
};

export const listenProfilesUpdated = async (callback: () => void) => {
  return await listen("profiles-updated", () => {
    callback();
  });
};

/** Parse a base64 encoded VLESS/Hysteria share link */
export const parseClipboardLink = async (link: string): Promise<ProxyNode> => {
  return await invoke<ProxyNode>("parse_clipboard_link", { link });
};

/** Listen for real-time traffic statistics */
export const listenTrafficUpdate = async (
  callback: (data: { up: number; down: number }) => void
) => {
  return await listen<{ up: number; down: number }>("traffic_update", (event) => {
    callback(event.payload);
  });
};

/** Get all routing rules */
export const getRoutingRules = async (): Promise<RoutingRule[]> => {
  return await invoke<RoutingRule[]>("get_routing_rules");
};

/** Add a new routing rule */
export const addRoutingRule = async (rule: RoutingRule): Promise<void> => {
  return await invoke("add_routing_rule", { rule });
};

/** Update an existing routing rule */
export const updateRoutingRule = async (rule: RoutingRule): Promise<void> => {
  return await invoke("update_routing_rule", { rule });
};

/** Delete a routing rule */
export const deleteRoutingRule = async (id: string): Promise<void> => {
  return await invoke("delete_routing_rule", { id });
};

export interface Subscription {
  id: string;
  name: string;
  url: string;
  autoUpdate: boolean;
  lastUpdated?: number;
}

export interface ProfileGroup {
  id: string;
  name: string;
}

/** Get all subscriptions */
export const getSubscriptions = async (): Promise<Subscription[]> => {
  return await invoke<Subscription[]>("get_subscriptions");
};

/** Add a new subscription */
export const addSubscription = async (sub: Subscription): Promise<void> => {
  return await invoke("add_subscription", { sub });
};

/** Update/Sync an existing subscription by ID */
export const updateSubscription = async (subId: string): Promise<void> => {
  return await invoke("update_subscription", { subId });
};

/** Get all user-defined profile groups */
export const getGroups = async (): Promise<ProfileGroup[]> => {
  return await invoke<ProfileGroup[]>("get_groups");
};

/** Scan active screens for a QR code and return a ProxyNode */
export const scanScreenForQr = async (): Promise<ProxyNode> => {
  return await invoke<ProxyNode>("scan_screen_for_qr");
};

/** Generate a shareable link from a ProxyNode */
export const generateLink = async (node: ProxyNode): Promise<string> => {
  return await invoke<string>("generate_link", { node });
};

/** Get the currently set custom config override */
export const getCustomConfig = async (): Promise<string | null> => {
  return await invoke<string | null>("get_custom_config");
};

/** Save a custom config override */
export const saveCustomConfig = async (config: string | null): Promise<void> => {
  return await invoke("save_custom_config", { config });
};

export type StableCore = "sing-box" | "xray";
export type EngineCore = StableCore | "helix";

/** Get the currently selected proxy engine core */
export const getActiveCore = async (): Promise<EngineCore> => {
  return await invoke<EngineCore>("get_active_core");
};

/** Save the proxy engine core */
export const saveActiveCore = async (core: EngineCore): Promise<void> => {
  return await invoke("save_active_core", { core });
};

export interface SupportedTransportProfile {
  profile_family: string;
  min_transport_profile_version: number;
  max_transport_profile_version: number;
  supported_policy_versions: number[];
}

export interface HelixCapabilityDefaults {
  schema_version: string;
  client_family: string;
  default_channel: string;
  supported_protocol_versions: number[];
  supported_transport_profiles: SupportedTransportProfile[];
  required_capabilities: string[];
  fallback_cores: string[];
  rollout_channels: string[];
}

export interface HelixManifest {
  schema_version: string;
  manifest_id: string;
  rollout_id: string;
  issued_at: string;
  expires_at: string;
  subject: {
    user_id: string;
    desktop_client_id: string;
    entitlement_id: string;
    channel: string;
  };
  transport: {
    transport_family: string;
    protocol_version: number;
    session_mode: string;
  };
  transport_profile: {
    transport_profile_id: string;
    profile_family: string;
    profile_version: number;
    policy_version: number;
    deprecation_state: string;
  };
  compatibility_window: {
    profile_family: string;
    min_transport_profile_version: number;
    max_transport_profile_version: number;
  };
  capability_profile: {
    required_capabilities: string[];
    fallback_core: string;
    health_policy: {
      startup_timeout_seconds: number;
      runtime_unhealthy_threshold: number;
    };
  };
  routes: Array<{
    endpoint_ref: string;
    dial_host: string;
    dial_port: number;
    server_name?: string | null;
    preference: number;
    policy_tag: string;
  }>;
  credentials: {
    key_id: string;
    token: string;
  };
  integrity: {
    manifest_hash: string;
    signature: {
      alg: string;
      key_id: string;
      sig: string;
    };
  };
  observability: {
    trace_id: string;
    metrics_namespace: string;
  };
}

export interface HelixResolvedManifest {
  manifest_version_id: string;
  manifest: HelixManifest;
  selected_profile_policy?: {
    observed_events: number;
    connect_success_rate: number;
    fallback_rate: number;
    continuity_success_rate: number;
    cross_route_recovery_rate: number;
    policy_score: number;
    degraded: boolean;
    advisory_state: string;
    recommended_action?: string | null;
    selection_eligible: boolean;
    new_session_issuable: boolean;
    new_session_posture: string;
    suppression_window_active: boolean;
    suppression_reason?: string | null;
    suppression_observation_count: number;
    suppressed_until?: string | null;
  } | null;
}

export interface HelixPreparedRuntime {
  manifest_id: string;
  manifest_version_id: string;
  rollout_id: string;
  transport_profile_id: string;
  config_path: string;
  sidecar_path: string;
  binary_available: boolean;
  health_url: string;
  proxy_url: string;
  fallback_core: StableCore;
  route_count: number;
  startup_timeout_seconds: number;
}

export interface HelixSidecarHealth {
  schema_version: string;
  status: string;
  ready: boolean;
  connected: boolean;
  manifest_id: string;
  rollout_id: string;
  transport_profile_id: string;
  route_count: number;
  proxy_url: string;
  session_id?: string | null;
  remote_addr?: string | null;
  active_route_endpoint_ref?: string | null;
  active_route_probe_latency_ms?: number | null;
  active_route_score?: number | null;
  standby_route_endpoint_ref?: string | null;
  standby_route_probe_latency_ms?: number | null;
  standby_route_score?: number | null;
  standby_ready: boolean;
  continuity_grace_active: boolean;
  continuity_grace_route_endpoint_ref?: string | null;
  continuity_grace_remaining_ms?: number | null;
  active_route_continuity_grace_entries: number;
  active_route_successful_continuity_recovers: number;
  active_route_failed_continuity_recovers: number;
  active_route_last_continuity_recovery_ms?: number | null;
  active_route_successful_cross_route_recovers: number;
  active_route_last_cross_route_recovery_ms?: number | null;
  active_route_quarantined: boolean;
  active_route_quarantine_remaining_ms?: number | null;
  active_route_successful_activations: number;
  active_route_failed_activations: number;
  active_route_failover_count: number;
  active_route_healthy_observations: number;
  last_ping_rtt_ms?: number | null;
  active_streams: number;
  pending_open_streams: number;
  max_concurrent_streams: number;
  frame_queue_depth: number;
  frame_queue_peak: number;
  bytes_sent: number;
  bytes_received: number;
}

export interface HelixStreamTelemetrySample {
  stream_id: number;
  target_authority: string;
  opened_at: string;
  closed_at?: string | null;
  duration_ms?: number | null;
  bytes_sent: number;
  bytes_received: number;
  peak_frame_queue_depth: number;
  peak_inbound_queue_depth: number;
  close_reason?: string | null;
}

export interface HelixSidecarTelemetry {
  schema_version: string;
  collected_at: string;
  health: HelixSidecarHealth;
  recent_rtt_ms: number[];
  recent_streams: HelixStreamTelemetrySample[];
}

export interface HelixRuntimeState {
  backend_url: string | null;
  desktop_client_id: string;
  last_manifest: HelixResolvedManifest | null;
  last_prepared_runtime: HelixPreparedRuntime | null;
  last_fallback_reason: string | null;
}

export interface CanonicalCustomerProfile {
  id: string;
  email: string;
  username?: string | null;
  status: string;
  telegram_id?: number | null;
  telegram_username?: string | null;
  created_at?: string | null;
  subscription?: {
    status: string;
    plan_name?: string | null;
    expires_at?: string | null;
    traffic_limit_bytes?: number | null;
    used_traffic_bytes?: number | null;
    auto_renew?: boolean;
  } | null;
}

export interface CanonicalEntitlementState {
  status: string;
  plan_uuid?: string | null;
  plan_code?: string | null;
  display_name?: string | null;
  period_days?: number | null;
  expires_at?: string | null;
  effective_entitlements: Record<string, unknown>;
  invite_bundle: Record<string, number>;
  is_trial: boolean;
  addons: Array<Record<string, unknown>>;
}

export interface CanonicalServiceIdentity {
  id: string;
  service_key: string;
  customer_account_id: string;
  auth_realm_id: string;
  source_order_id?: string | null;
  origin_storefront_id?: string | null;
  provider_name: string;
  provider_subject_ref?: string | null;
  identity_status: string;
  service_context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CanonicalProvisioningProfile {
  id: string;
  service_identity_id: string;
  profile_key: string;
  target_channel: string;
  delivery_method: string;
  profile_status: string;
  provider_name: string;
  provider_profile_ref?: string | null;
  provisioning_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CanonicalDeviceCredential {
  id: string;
  credential_key: string;
  service_identity_id: string;
  auth_realm_id: string;
  origin_storefront_id?: string | null;
  provisioning_profile_id?: string | null;
  credential_type: string;
  credential_status: string;
  subject_key: string;
  provider_name: string;
  provider_credential_ref?: string | null;
  credential_context: Record<string, unknown>;
  issued_at: string;
  last_used_at?: string | null;
  revoked_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CanonicalAccessDeliveryChannel {
  id: string;
  delivery_key: string;
  service_identity_id: string;
  auth_realm_id: string;
  origin_storefront_id?: string | null;
  provisioning_profile_id?: string | null;
  device_credential_id?: string | null;
  channel_type: string;
  channel_status: string;
  channel_subject_ref: string;
  provider_name: string;
  delivery_context: Record<string, unknown>;
  delivery_payload: Record<string, unknown>;
  last_delivered_at?: string | null;
  last_accessed_at?: string | null;
  archived_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CanonicalCurrentServiceState {
  customer_account_id: string;
  auth_realm_id: string;
  provider_name: string;
  entitlement_snapshot: CanonicalEntitlementState;
  service_identity?: CanonicalServiceIdentity | null;
  provisioning_profile?: CanonicalProvisioningProfile | null;
  device_credential?: CanonicalDeviceCredential | null;
  access_delivery_channel?: CanonicalAccessDeliveryChannel | null;
  purchase_context: {
    active_entitlement_grant_id?: string | null;
    source_type?: string | null;
    source_order_id?: string | null;
    source_growth_reward_allocation_id?: string | null;
    source_renewal_order_id?: string | null;
    manual_source_key?: string | null;
    origin_storefront_id?: string | null;
  };
  consumption_context: {
    channel_type?: string | null;
    channel_subject_ref?: string | null;
    provisioning_profile_key?: string | null;
    credential_type?: string | null;
    credential_subject_key?: string | null;
  };
}

export interface CanonicalOrderItem {
  id: string;
  order_id: string;
  item_type: string;
  subject_id?: string | null;
  subject_code?: string | null;
  display_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  currency_code: string;
  item_snapshot: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CanonicalOrder {
  id: string;
  quote_session_id?: string | null;
  checkout_session_id: string;
  user_id: string;
  auth_realm_id: string;
  storefront_id: string;
  merchant_profile_id?: string | null;
  invoice_profile_id?: string | null;
  billing_descriptor_id?: string | null;
  pricebook_id?: string | null;
  pricebook_entry_id?: string | null;
  offer_id?: string | null;
  legal_document_set_id?: string | null;
  program_eligibility_policy_id?: string | null;
  subscription_plan_id?: string | null;
  promo_code_id?: string | null;
  partner_code_id?: string | null;
  sale_channel: string;
  currency_code: string;
  order_status: string;
  settlement_status: string;
  base_price: number;
  addon_amount: number;
  displayed_price: number;
  discount_amount: number;
  wallet_amount: number;
  gateway_amount: number;
  partner_markup: number;
  commission_base_amount: number;
  merchant_snapshot: Record<string, unknown>;
  pricing_snapshot: Record<string, unknown>;
  policy_snapshot: Record<string, unknown>;
  entitlements_snapshot: Record<string, unknown>;
  items: CanonicalOrderItem[];
  created_at: string;
  updated_at: string;
}

export interface TransportBenchmarkRequest {
  proxy_url?: string | null;
  target_host?: string | null;
  target_port?: number | null;
  target_path?: string | null;
  attempts?: number | null;
  download_bytes_limit?: number | null;
  connect_timeout_ms?: number | null;
}

export interface TransportBenchmarkComparisonRequest {
  profile_id: string;
  cores?: EngineCore[];
  benchmark: TransportBenchmarkRequest;
}

export interface TransportBenchmarkMatrixTarget {
  label: string;
  host: string;
  port: number;
  path?: string | null;
}

export interface TransportBenchmarkMatrixRequest {
  profile_id: string;
  cores?: EngineCore[];
  targets: TransportBenchmarkMatrixTarget[];
  benchmark: TransportBenchmarkRequest;
}

export interface TransportBenchmarkSample {
  attempt: number;
  success: boolean;
  connect_latency_ms?: number | null;
  first_byte_latency_ms?: number | null;
  bytes_read: number;
  bytes_written: number;
  throughput_kbps?: number | null;
  error?: string | null;
}

export interface HelixQueuePressureSummary {
  frame_queue_depth: number;
  frame_queue_peak: number;
  active_streams: number;
  pending_open_streams: number;
  max_concurrent_streams: number;
  recent_rtt_p50_ms?: number | null;
  recent_rtt_p95_ms?: number | null;
  recent_stream_peak_frame_queue_depth?: number | null;
  recent_stream_peak_inbound_queue_depth?: number | null;
}

export interface HelixContinuitySummary {
  grace_active: boolean;
  grace_route_endpoint_ref?: string | null;
  grace_remaining_ms?: number | null;
  active_streams: number;
  pending_open_streams: number;
  active_route_quarantined: boolean;
  active_route_quarantine_remaining_ms?: number | null;
  continuity_grace_entries: number;
  successful_continuity_recovers: number;
  failed_continuity_recovers: number;
  last_continuity_recovery_ms?: number | null;
  successful_cross_route_recovers: number;
  last_cross_route_recovery_ms?: number | null;
}

export interface TransportBenchmarkReport {
  schema_version: string;
  run_id: string;
  generated_at: string;
  active_core: string;
  proxy_url: string;
  target_host: string;
  target_port: number;
  target_path: string;
  attempts: number;
  successes: number;
  failures: number;
  median_connect_latency_ms?: number | null;
  p95_connect_latency_ms?: number | null;
  median_first_byte_latency_ms?: number | null;
  p95_first_byte_latency_ms?: number | null;
  median_open_to_first_byte_gap_ms?: number | null;
  p95_open_to_first_byte_gap_ms?: number | null;
  average_throughput_kbps?: number | null;
  helix_queue_pressure?: HelixQueuePressureSummary | null;
  helix_continuity?: HelixContinuitySummary | null;
  bytes_read_total: number;
  bytes_written_total: number;
  samples: TransportBenchmarkSample[];
}

export interface TransportBenchmarkComparisonEntry {
  requested_core: string;
  effective_core?: string | null;
  benchmark?: TransportBenchmarkReport | null;
  error?: string | null;
  relative_connect_latency_ratio?: number | null;
  relative_first_byte_latency_ratio?: number | null;
  relative_open_to_first_byte_gap_ratio?: number | null;
  relative_throughput_ratio?: number | null;
}

export interface TransportBenchmarkComparisonReport {
  schema_version: string;
  run_id: string;
  generated_at: string;
  profile_id: string;
  baseline_core?: string | null;
  entries: TransportBenchmarkComparisonEntry[];
}

export interface TransportBenchmarkMatrixTargetReport {
  label: string;
  host: string;
  port: number;
  path: string;
  comparison: TransportBenchmarkComparisonReport;
}

export interface TransportBenchmarkMatrixCoreSummary {
  core: string;
  completed_targets: number;
  failed_targets: number;
  median_connect_latency_ms?: number | null;
  median_first_byte_latency_ms?: number | null;
  median_open_to_first_byte_gap_ms?: number | null;
  average_throughput_kbps?: number | null;
  average_relative_connect_latency_ratio?: number | null;
  average_relative_first_byte_latency_ratio?: number | null;
  average_relative_open_to_first_byte_gap_ratio?: number | null;
  average_relative_throughput_ratio?: number | null;
}

export interface TransportBenchmarkMatrixReport {
  schema_version: string;
  run_id: string;
  generated_at: string;
  profile_id: string;
  baseline_core?: string | null;
  targets: TransportBenchmarkMatrixTargetReport[];
  core_summaries: TransportBenchmarkMatrixCoreSummary[];
}

export type HelixRecoveryBenchmarkMode = "failover" | "reconnect";

export interface HelixSidecarBenchActionReport {
  schema_version: string;
  action: string;
  success: boolean;
  route_before?: string | null;
  route_after?: string | null;
  recovery_latency_ms?: number | null;
  message?: string | null;
}

export interface HelixRecoveryBenchmarkRequest {
  profile_id: string;
  mode: HelixRecoveryBenchmarkMode;
  benchmark: TransportBenchmarkRequest;
  recovery_timeout_ms?: number | null;
}

export interface HelixRecoveryBenchmarkReport {
  schema_version: string;
  run_id: string;
  generated_at: string;
  profile_id: string;
  mode: string;
  proxy_url: string;
  route_before?: string | null;
  route_after?: string | null;
  ready_recovery_latency_ms?: number | null;
  proxy_ready_latency_ms?: number | null;
  proxy_ready_open_to_first_byte_gap_ms?: number | null;
  proxy_ready_measurement?: string | null;
  proxy_ready_probe?: TransportBenchmarkSample | null;
  recovered: boolean;
  same_route_recovered?: boolean | null;
  health_before?: HelixSidecarHealth | null;
  health_after?: HelixSidecarHealth | null;
  continuity_before?: HelixContinuitySummary | null;
  continuity_after?: HelixContinuitySummary | null;
  telemetry_before?: HelixSidecarTelemetry | null;
  telemetry_after?: HelixSidecarTelemetry | null;
  action?: HelixSidecarBenchActionReport | null;
  post_recovery_benchmark?: TransportBenchmarkReport | null;
  error?: string | null;
}

export interface DiagnosticEntry {
  id: string;
  timestamp: string;
  level: string;
  source: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface HelixDiagnosticsSnapshot {
  backend_url?: string | null;
  desktop_client_id?: string | null;
  last_fallback_reason?: string | null;
  last_manifest_version_id?: string | null;
  last_rollout_id?: string | null;
  transport_profile_id?: string | null;
  prepared_route_count?: number | null;
  health_url?: string | null;
  proxy_url?: string | null;
  live_health?: HelixSidecarHealth | null;
  live_telemetry?: HelixSidecarTelemetry | null;
}

export interface DesktopLifecycleState {
  schema_version: string;
  current_run_id: string;
  started_at: string;
  running: boolean;
  hidden_launch_requested: boolean;
  previous_run_id?: string | null;
  previous_started_at?: string | null;
  previous_exit_kind?: string | null;
  previous_exit_at?: string | null;
  previous_exit_message?: string | null;
  previous_unclean_shutdown_detected: boolean;
  startup_cleanup_performed: boolean;
  system_proxy_cleanup_succeeded: boolean;
  last_exit_kind?: string | null;
  last_exit_at?: string | null;
  last_exit_message?: string | null;
}

export interface DesktopDiagnosticsSnapshot {
  collected_at: string;
  app_name: string;
  app_version: string;
  package_name: string;
  platform: string;
  app_dir: string;
  diagnostics_dir: string;
  support_bundle_dir: string;
  store_path: string;
  lifecycle: DesktopLifecycleState;
  connection_status: ConnectionStatus;
  active_core: string;
  active_profile_id?: string | null;
  local_ip?: string | null;
  local_socks_port?: number | null;
  allow_lan: boolean;
  profile_count: number;
  routing_rule_count: number;
  subscription_count: number;
  split_tunneling_mode: string;
  split_tunneling_app_count: number;
  smart_connect_enabled: boolean;
  stealth_mode_enabled: boolean;
  pqc_enforcement_mode: boolean;
  privacy_shield_level: string;
  last_benchmark_run_id?: string | null;
  last_comparison_run_id?: string | null;
  last_matrix_run_id?: string | null;
  last_recovery_run_id?: string | null;
  helix: HelixDiagnosticsSnapshot;
  recent_entries: DiagnosticEntry[];
  core_log_tail: string[];
  helix_log_tail: string[];
}

export interface SupportBundleExportResult {
  archive_path: string;
  exported_at: string;
  event_count: number;
  includes_core_log: boolean;
  includes_helix_log: boolean;
}

export const getHelixCapabilities =
  async (): Promise<HelixCapabilityDefaults> => {
    return await invoke<HelixCapabilityDefaults>("get_helix_capabilities");
  };

export const getHelixManifest =
  async (): Promise<HelixResolvedManifest | null> => {
    return await invoke<HelixResolvedManifest | null>("get_helix_manifest");
  };

export const getHelixRuntimeState =
  async (): Promise<HelixRuntimeState> => {
    return await invoke<HelixRuntimeState>("get_helix_runtime_state");
  };

export const getCanonicalCustomerProfile =
  async (): Promise<CanonicalCustomerProfile> => {
    return await invoke<CanonicalCustomerProfile>("get_canonical_customer_profile");
  };

export const getCanonicalCurrentEntitlements =
  async (): Promise<CanonicalEntitlementState> => {
    return await invoke<CanonicalEntitlementState>("get_canonical_current_entitlements");
  };

export const getCanonicalCurrentServiceState =
  async (): Promise<CanonicalCurrentServiceState> => {
    return await invoke<CanonicalCurrentServiceState>("get_canonical_current_service_state");
  };

export const getCanonicalOrders =
  async (limit = 20): Promise<CanonicalOrder[]> => {
    return await invoke<CanonicalOrder[]>("get_canonical_orders", { limit });
  };

export const resolveHelixManifest = async (
  baseUrl: string,
  accessToken: string,
  preferredFallbackCore?: StableCore
): Promise<HelixResolvedManifest> => {
  return await invoke<HelixResolvedManifest>("resolve_helix_manifest", {
    baseUrl,
    accessToken,
    preferredFallbackCore: preferredFallbackCore ?? null,
  });
};

export const prepareHelixRuntime =
  async (): Promise<HelixPreparedRuntime> => {
    return await invoke<HelixPreparedRuntime>("prepare_helix_runtime");
  };

export const runTransportBenchmark = async (
  request: TransportBenchmarkRequest
): Promise<TransportBenchmarkReport> => {
  return await invoke<TransportBenchmarkReport>("run_transport_benchmark", { request });
};

export const runTransportCoreComparison = async (
  request: TransportBenchmarkComparisonRequest
): Promise<TransportBenchmarkComparisonReport> => {
  return await invoke<TransportBenchmarkComparisonReport>("run_transport_core_comparison", {
    request,
  });
};

export const runTransportTargetMatrixComparison = async (
  request: TransportBenchmarkMatrixRequest
): Promise<TransportBenchmarkMatrixReport> => {
  return await invoke<TransportBenchmarkMatrixReport>(
    "run_transport_target_matrix_comparison",
    { request }
  );
};

export const runHelixRecoveryBenchmark = async (
  request: HelixRecoveryBenchmarkRequest
): Promise<HelixRecoveryBenchmarkReport> => {
  return await invoke<HelixRecoveryBenchmarkReport>("run_helix_recovery_benchmark", {
    request,
  });
};

export const getDesktopDiagnosticsSnapshot =
  async (): Promise<DesktopDiagnosticsSnapshot> => {
    return await invoke<DesktopDiagnosticsSnapshot>("get_desktop_diagnostics_snapshot");
  };

export const exportDesktopSupportBundle =
  async (): Promise<SupportBundleExportResult> => {
    return await invoke<SupportBundleExportResult>("export_desktop_support_bundle");
  };

export const clearDesktopDiagnosticsLogs = async (): Promise<void> => {
  return await invoke("clear_desktop_diagnostics_logs");
};

export const listenDesktopDiagnostics = async (
  callback: (entry: DiagnosticEntry) => void
) => {
  return await listen<DiagnosticEntry>("desktop-diagnostic", (event) => {
    callback(event.payload);
  });
};

export const listenHelixHealth = async (
  callback: (health: HelixSidecarHealth) => void
) => {
  return await listen<HelixSidecarHealth>("helix-health", (event) => {
    callback(event.payload);
  });
};

export interface AppInfo {
  name: string;
  packageName: string;
  iconBase64: string | null;
  execPath: string;
}

export const getInstalledApps = async (): Promise<AppInfo[]> => {
  return await invoke("get_installed_apps");
};

export const getSplitTunnelingApps = async (): Promise<string[]> => {
  return await invoke("get_split_tunneling_apps");
};

export const saveSplitTunnelingApps = async (apps: string[]): Promise<void> => {
  return await invoke("save_split_tunneling_apps", { apps });
};

export const getSplitTunnelingMode = async (): Promise<string> => {
  return await invoke("get_split_tunneling_mode");
};

export const saveSplitTunnelingMode = async (mode: string): Promise<void> => {
  return await invoke("save_split_tunneling_mode", { mode });
};

export interface LanInfo {
  ip: string;
  port: number;
}

export interface LanDevice {
  ip: string;
  mac: string;
}

export const getLanConnectionInfo = async (): Promise<LanInfo> => {
  return await invoke("get_lan_connection_info");
};

export const enableLanForwarding = async (): Promise<void> => {
  return await invoke("enable_lan_forwarding");
};

export const disableLanForwarding = async (): Promise<void> => {
  return await invoke("disable_lan_forwarding");
};

export const startDeviceDiscovery = async (): Promise<void> => {
  return await invoke("start_device_discovery");
};

export const stopDeviceDiscovery = async (): Promise<void> => {
  return await invoke("stop_device_discovery");
};

export const enableKillswitchCmd = async (): Promise<void> => {
  return await invoke("enable_killswitch_cmd");
};

export const disableKillswitchCmd = async (): Promise<void> => {
  return await invoke("disable_killswitch_cmd");
};

export const repairNetwork = async (): Promise<void> => {
  return await invoke("repair_network");
};

export const applyRoutingFix = async (domain: string): Promise<void> => {
  return await invoke("apply_routing_fix", { domain });
};

export const getStealthMode = async (): Promise<boolean> => {
  return await invoke("get_stealth_mode");
};

export const saveStealthMode = async (enabled: boolean): Promise<void> => {
  return await invoke("save_stealth_mode", { enabled });
};

export interface AuditResult {
  id: string;
  name: string;
  protocol: string;
  status: string;
}

export const auditQuantumReadiness = async (): Promise<AuditResult[]> => {
  return await invoke("audit_quantum_readiness");
};

export const getPrivacyShieldLevel = async (): Promise<string> => {
  return await invoke("get_privacy_shield_level");
};

export const setPrivacyShieldLevel = async (level: string): Promise<void> => {
  return await invoke("set_privacy_shield_level", { level });
};

export const forceUpdateBlocklists = async (): Promise<void> => {
  return await invoke("force_update_blocklists");
};

export const getThreatCount = async (): Promise<number> => {
  return await invoke("get_threat_count");
};

export const listenTrackerBlocked = (callback: (domain: string) => void) => {
  const unlistenPromise = listen<string>("tracker-blocked", (event) => {
    callback(event.payload);
  });
  return () => {
    unlistenPromise.then((f) => f());
  };
};

// Phase 28 - Smart Connect
export interface NetworkProfile {
  auto_connect: boolean;
  stealth_required: boolean;
  kill_switch_required: boolean;
  icon_type: string;
}

export const getSmartConnectStatus = async (): Promise<boolean> => {
  return await invoke("get_smart_connect_status");
};

export const setSmartConnectStatus = async (enabled: boolean): Promise<void> => {
  return await invoke("set_smart_connect_status", { enabled });
};

export const getNetworkRules = async (): Promise<Record<string, NetworkProfile>> => {
  return await invoke("get_network_rules");
};

export const updateNetworkRule = async (ssid: string, profile: NetworkProfile): Promise<void> => {
  return await invoke("update_network_rule", { ssid, profile });
};

export const listenNetworkChanged = (callback: (event: { ssid: string, is_trusted: boolean }) => void) => {
  const unlistenPromise = listen<{ ssid: string, is_trusted: boolean }>("network-changed", (event) => {
    callback(event.payload);
  });
  return () => {
    unlistenPromise.then((f) => f());
  };
};

// Phase 29 - Stealth Diagnostics
export interface CensorshipReport {
    ip_blocked: boolean;
    sni_filtered: boolean;
    udp_blocked: boolean;
    tls_intercepted: boolean;
    recommended_action: string;
    recommended_protocol: string;
}

export const runStealthDiagnostics = async (nodeId: string): Promise<CensorshipReport> => {
    return await invoke("run_stealth_diagnostics", { nodeId });
};

export const applyStealthFix = async (nodeId: string, recommendedProtocol: string): Promise<void> => {
    return await invoke("apply_stealth_fix", { nodeId, recommendedProtocol });
};

export const listenStealthProbeLog = (callback: (log: string) => void) => {
    const unlistenPromise = listen<string>("stealth-probe-log", (event) => callback(event.payload));
    return () => { unlistenPromise.then(f => f()); };
};

// Phase 30 - Telemetry & Analytics
export interface UsageRecord {
  date: string;
  bytes_up: number;
  bytes_down: number;
  protocol: string;
  country_code: string;
}

export const getUsageHistory = async (period: string): Promise<UsageRecord[]> => {
  return await invoke("get_usage_history", { period });
};

export const getGlobalFootprint = async (): Promise<Record<string, number>> => {
    return await invoke("get_global_footprint");
};
