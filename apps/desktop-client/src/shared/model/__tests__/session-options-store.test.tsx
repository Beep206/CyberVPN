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

let connectionOptionsListener: ((options: LastConnectionOptions) => void) | undefined;

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

const persistedOptions: LastConnectionOptions = {
  profileId: "profile-1",
  tunMode: true,
  systemProxy: true,
  activeCore: "sing-box",
  sourceSurface: "dashboard",
  favoriteProfileIds: ["profile-1", "profile-7"],
  lastStableProfileId: "profile-1",
  lastStableConnectedAt: 1710000100000,
  lastAction: "connect_requested",
  lastRequestedAt: 1710000000000,
  lastConnectedAt: null,
  lastDisconnectedAt: null,
};

function SessionOptionsHarness() {
  const connection = useConnection();

  return (
    <div>
      <div data-testid="ready">{connection.isReady ? "ready" : "booting"}</div>
      <pre data-testid="options">{JSON.stringify(connection.options)}</pre>
      <button
        type="button"
        onClick={() =>
          void connection.updateOptions((current) => ({
            ...current,
            tunMode: false,
            systemProxy: false,
            sourceSurface: "tray-menu",
          }))
        }
      >
        persist
      </button>
    </div>
  );
}

function readOptions() {
  return JSON.parse(screen.getByTestId("options").textContent ?? "{}");
}

beforeEach(() => {
  connectionOptionsListener = undefined;

  mockConnectProfile.mockReset().mockResolvedValue(undefined);
  mockDisconnectProxy.mockReset().mockResolvedValue(undefined);
  mockGetConnectionStatus.mockReset().mockResolvedValue(initialStatus);
  mockGetLastConnectionOptions.mockReset().mockResolvedValue(persistedOptions);
  mockSaveLastConnectionOptions.mockReset().mockImplementation(async (options) => options);
  mockListenConnectionStatus.mockReset().mockResolvedValue(vi.fn());
  mockListenTrafficUpdate.mockReset().mockResolvedValue(vi.fn());
  mockListenConnectionOptions.mockReset().mockImplementation(async (callback) => {
    connectionOptionsListener = callback;
    return vi.fn();
  });
});

describe("session options persistence", () => {
  it("hydrates persisted options for dashboard-facing re-entry", async () => {
    render(
      <ConnectionProvider>
        <SessionOptionsHarness />
      </ConnectionProvider>,
    );

    await screen.findByText("ready");
    await waitFor(() => {
      expect(readOptions()).toMatchObject({
        profileId: "profile-1",
        tunMode: true,
        systemProxy: true,
        sourceSurface: "dashboard",
      });
    });
  });

  it("persists option updates and accepts backend option events", async () => {
    render(
      <ConnectionProvider>
        <SessionOptionsHarness />
      </ConnectionProvider>,
    );

    await screen.findByText("ready");
    fireEvent.click(screen.getByRole("button", { name: "persist" }));

    await waitFor(() => {
      expect(mockSaveLastConnectionOptions).toHaveBeenCalledWith(
        expect.objectContaining({
          profileId: "profile-1",
          tunMode: false,
          systemProxy: false,
          sourceSurface: "tray-menu",
          favoriteProfileIds: ["profile-1", "profile-7"],
          lastStableProfileId: "profile-1",
        }),
      );
    });

    expect(readOptions()).toMatchObject({
      tunMode: false,
      systemProxy: false,
      sourceSurface: "tray-menu",
    });

    await act(async () => {
      connectionOptionsListener?.({
        ...persistedOptions,
        profileId: "profile-9",
        tunMode: true,
        systemProxy: false,
        sourceSurface: "global-hotkey",
      });
    });

    expect(readOptions()).toMatchObject({
      profileId: "profile-9",
      tunMode: true,
      systemProxy: false,
      sourceSurface: "global-hotkey",
    });
  });
});
