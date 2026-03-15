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
