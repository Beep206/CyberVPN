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
  subscriptionId?: string;
}

export interface RoutingRule {
  id: string;
  enabled: boolean;
  domains: string[];
  ips: string[];
  outbound: string;
}

export interface ConnectionStatus {
  status: "disconnected" | "connecting" | "connected" | "error";
  activeId?: string;
  message?: string;
  upBytes: number;
  downBytes: number;
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
export const connectProfile = async (id: string, tunMode: boolean): Promise<void> => {
  return await invoke("connect_profile", { id, tunMode });
};

/** Disconnect the active proxy */
export const disconnectProxy = async (): Promise<void> => {
  return await invoke("disconnect");
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

/** Get the currently selected proxy engine core */
export const getActiveCore = async (): Promise<"sing-box" | "xray"> => {
  return await invoke<"sing-box" | "xray">("get_active_core");
};

/** Save the proxy engine core */
export const saveActiveCore = async (core: "sing-box" | "xray"): Promise<void> => {
  return await invoke("save_active_core", { core });
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
