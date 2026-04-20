import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ConnectionStatus, LastConnectionOptions } from "../../api/ipc";
import { ConnectionProvider, useConnection } from "../use-connection";

const {
  mockConnectProfile,
  mockDisconnectProxy,
  mockGetConnectionStatus,
  mockGetLastConnectionOptions,
  mockListenConnectionOptions,
  mockListenConnectionStatus,
  mockListenTrafficUpdate,
  mockSaveLastConnectionOptions,
} = vi.hoisted(() => ({
  mockConnectProfile: vi.fn(),
  mockDisconnectProxy: vi.fn(),
  mockGetConnectionStatus: vi.fn(),
  mockGetLastConnectionOptions: vi.fn(),
  mockListenConnectionOptions: vi.fn(),
  mockListenConnectionStatus: vi.fn(),
  mockListenTrafficUpdate: vi.fn(),
  mockSaveLastConnectionOptions: vi.fn(),
}));

let connectionStatusListener: ((status: ConnectionStatus) => void) | undefined;
let trafficListener: ((traffic: { up: number; down: number }) => void) | undefined;

vi.mock("../../api/ipc", () => ({
  connectProfile: mockConnectProfile,
  disconnectProxy: mockDisconnectProxy,
  getConnectionStatus: mockGetConnectionStatus,
  getLastConnectionOptions: mockGetLastConnectionOptions,
  listenConnectionOptions: mockListenConnectionOptions,
  listenConnectionStatus: mockListenConnectionStatus,
  listenTrafficUpdate: mockListenTrafficUpdate,
  saveLastConnectionOptions: mockSaveLastConnectionOptions,
}));

const initialStatus: ConnectionStatus = {
  status: "disconnected",
  upBytes: 0,
  downBytes: 0,
};

const initialOptions: LastConnectionOptions = {
  profileId: null,
  tunMode: false,
  systemProxy: false,
  activeCore: "sing-box",
  sourceSurface: "dashboard",
  favoriteProfileIds: [],
  lastStableProfileId: null,
  lastStableConnectedAt: null,
  lastAction: null,
  lastRequestedAt: null,
  lastConnectedAt: null,
  lastDisconnectedAt: null,
};

function ConnectionHarness() {
  const connection = useConnection();

  return (
    <div>
      <div data-testid="ready">{connection.isReady ? "ready" : "booting"}</div>
      <pre data-testid="status">{JSON.stringify(connection.status)}</pre>
      <pre data-testid="options">{JSON.stringify(connection.options)}</pre>
      <button
        type="button"
        onClick={() =>
          void connection.connect("profile-2", {
            tunMode: true,
            systemProxy: true,
            sourceSurface: "dashboard",
          })
        }
      >
        connect
      </button>
      <button type="button" onClick={() => void connection.disconnect("dashboard")}>
        disconnect
      </button>
    </div>
  );
}

function readJson(testId: string) {
  return JSON.parse(screen.getByTestId(testId).textContent ?? "{}");
}

beforeEach(() => {
  connectionStatusListener = undefined;
  trafficListener = undefined;

  mockConnectProfile.mockReset().mockResolvedValue(undefined);
  mockDisconnectProxy.mockReset().mockResolvedValue(undefined);
  mockGetConnectionStatus.mockReset().mockResolvedValue(initialStatus);
  mockGetLastConnectionOptions.mockReset().mockResolvedValue(initialOptions);
  mockSaveLastConnectionOptions.mockReset().mockImplementation(async (options) => options);

  mockListenConnectionStatus.mockReset().mockImplementation(async (callback) => {
    connectionStatusListener = callback;
    return vi.fn();
  });
  mockListenConnectionOptions.mockReset().mockImplementation(async (callback) => {
    void callback;
    return vi.fn();
  });
  mockListenTrafficUpdate.mockReset().mockImplementation(async (callback) => {
    trafficListener = callback;
    return vi.fn();
  });
});

describe("ConnectionProvider lifecycle", () => {
  it("hydrates from IPC and applies live status and traffic events", async () => {
    render(
      <ConnectionProvider>
        <ConnectionHarness />
      </ConnectionProvider>,
    );

    await screen.findByText("ready");
    expect(readJson("status")).toMatchObject({ status: "disconnected", upBytes: 0, downBytes: 0 });
    expect(readJson("options")).toMatchObject({ tunMode: false, systemProxy: false });

    await act(async () => {
      connectionStatusListener?.({
        status: "connected",
        activeId: "profile-1",
        activeCore: "sing-box",
        proxyUrl: "socks5://127.0.0.1:2080",
        message: null,
        upBytes: 0,
        downBytes: 0,
      });
    });

    expect(readJson("status")).toMatchObject({
      status: "connected",
      activeId: "profile-1",
      proxyUrl: "socks5://127.0.0.1:2080",
    });

    await act(async () => {
      trafficListener?.({ up: 128, down: 256 });
    });

    expect(readJson("status")).toMatchObject({ upBytes: 128, downBytes: 256 });
  });

  it("moves through connecting and disconnecting states around IPC commands", async () => {
    mockGetConnectionStatus.mockResolvedValue({
      ...initialStatus,
      status: "connected",
      activeId: "profile-1",
    });
    mockGetLastConnectionOptions.mockResolvedValue({
      ...initialOptions,
      profileId: "profile-1",
      tunMode: true,
      systemProxy: true,
    });

    render(
      <ConnectionProvider>
        <ConnectionHarness />
      </ConnectionProvider>,
    );

    await screen.findByText("ready");

    fireEvent.click(screen.getByRole("button", { name: "disconnect" }));

    await waitFor(() => {
      expect(mockDisconnectProxy).toHaveBeenCalledWith("dashboard");
      expect(readJson("status")).toMatchObject({ status: "disconnecting" });
    });

    await act(async () => {
      connectionStatusListener?.({
        ...initialStatus,
        status: "disconnected",
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "connect" }));

    await waitFor(() => {
      expect(mockConnectProfile).toHaveBeenCalledWith("profile-2", true, true, "dashboard");
      expect(readJson("status")).toMatchObject({
        status: "connecting",
        activeId: "profile-2",
      });
    });
  });
});
