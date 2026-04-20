import {
  createContext,
  startTransition,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  connectProfile,
  disconnectProxy,
  getConnectionStatus,
  getLastConnectionOptions,
  listenConnectionStatus,
  listenConnectionOptions,
  listenTrafficUpdate,
  type ConnectionStatus,
  type LastConnectionOptions,
  saveLastConnectionOptions,
} from "../api/ipc";

const initialConnectionStatus: ConnectionStatus = {
  status: "disconnected",
  upBytes: 0,
  downBytes: 0,
};

type ConnectOptions = {
  tunMode: boolean;
  systemProxy?: boolean;
  sourceSurface?: string;
};

type ConnectionContextValue = {
  isReady: boolean;
  status: ConnectionStatus;
  options: LastConnectionOptions;
  refreshStatus: () => Promise<ConnectionStatus>;
  connect: (profileId: string, options: ConnectOptions) => Promise<void>;
  disconnect: (sourceSurface?: string) => Promise<void>;
  updateOptions: (
    updater:
      | Partial<LastConnectionOptions>
      | ((current: LastConnectionOptions) => Partial<LastConnectionOptions>)
  ) => Promise<LastConnectionOptions>;
};

const ConnectionContext = createContext<ConnectionContextValue | undefined>(undefined);

const initialConnectionOptions: LastConnectionOptions = {
  profileId: null,
  tunMode: false,
  systemProxy: false,
  activeCore: "sing-box",
  sourceSurface: "unknown",
  favoriteProfileIds: [],
  lastStableProfileId: null,
  lastStableConnectedAt: null,
  lastAction: null,
  lastRequestedAt: null,
  lastConnectedAt: null,
  lastDisconnectedAt: null,
};

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

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ConnectionStatus>(initialConnectionStatus);
  const [sessionOptions, setSessionOptions] = useState<LastConnectionOptions>(
    initialConnectionOptions
  );
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let isMounted = true;
    let cleanup: (() => void) | undefined;

    const applyStatus = (nextStatus: ConnectionStatus) => {
      if (!isMounted) {
        return;
      }

      startTransition(() => {
        setStatus(nextStatus);
      });
    };

    const syncStatus = async () => {
      try {
        const [nextStatus, nextOptions] = await Promise.all([
          getConnectionStatus(),
          getLastConnectionOptions(),
        ]);
        applyStatus(nextStatus);
        startTransition(() => {
          setSessionOptions(nextOptions);
        });
      } catch (error) {
        console.error("Failed to hydrate connection session", error);
      } finally {
        if (isMounted) {
          setIsReady(true);
        }
      }
    };

    const setupListeners = async () => {
      const unlistenStatus = await listenConnectionStatus((nextStatus) => {
        applyStatus(nextStatus);
      });

      const unlistenOptions = await listenConnectionOptions((nextOptions) => {
        if (!isMounted) {
          return;
        }

        startTransition(() => {
          setSessionOptions(nextOptions);
        });
      });

      const unlistenTraffic = await listenTrafficUpdate((traffic) => {
        if (!isMounted) {
          return;
        }

        startTransition(() => {
          setStatus((current) => ({
            ...current,
            upBytes: traffic.up,
            downBytes: traffic.down,
          }));
        });
      });

      cleanup = () => {
        unlistenStatus();
        unlistenOptions();
        unlistenTraffic();
      };
    };

    void syncStatus();
    void setupListeners();

    return () => {
      isMounted = false;
      cleanup?.();
    };
  }, []);

  const refreshStatus = async () => {
    const nextStatus = await getConnectionStatus();
    startTransition(() => {
      setStatus(nextStatus);
    });
    return nextStatus;
  };

  const connect = async (profileId: string, connectOptions: ConnectOptions) => {
    const sourceSurface = connectOptions.sourceSurface ?? "dashboard";
    const optimisticOptions: LastConnectionOptions = {
      ...initialConnectionOptions,
      ...sessionOptions,
      ...{
        profileId,
        tunMode: connectOptions.tunMode,
        systemProxy: connectOptions.systemProxy ?? false,
        sourceSurface,
        lastAction: "connect_requested",
        lastRequestedAt: Date.now(),
      },
      activeCore:
        sessionOptions.activeCore || status.activeCore || initialConnectionOptions.activeCore,
    };

    startTransition(() => {
      setStatus((current) => ({
        ...current,
        status: "connecting",
        activeId: profileId,
        message: null,
      }));
      setSessionOptions((current) => ({
        ...current,
        ...optimisticOptions,
        activeCore: current.activeCore || optimisticOptions.activeCore,
      }));
    });

    try {
      await connectProfile(
        profileId,
        connectOptions.tunMode,
        connectOptions.systemProxy ?? false,
        sourceSurface
      );
    } catch (error) {
      const message = formatUnknownError(error);
      startTransition(() => {
        setStatus((current) => ({
          ...current,
          status: "error",
          activeId: profileId,
          message,
        }));
      });
      throw error;
    }
  };

  const disconnect = async (sourceSurface = "dashboard") => {
    if (status.status === "disconnected" || status.status === "disconnecting") {
      return;
    }

    startTransition(() => {
      setStatus((current) => ({
        ...current,
        status: "disconnecting",
      }));
    });

    try {
      await disconnectProxy(sourceSurface);
    } catch (error) {
      const message = formatUnknownError(error);
      startTransition(() => {
        setStatus((current) => ({
          ...current,
          status: "error",
          message,
        }));
      });
      throw error;
    }
  };

  const updateOptions: ConnectionContextValue["updateOptions"] = async (updater) => {
    const nextPatch = typeof updater === "function" ? updater(sessionOptions) : updater;
    const persisted = await saveLastConnectionOptions({
      ...sessionOptions,
      ...nextPatch,
    });

    startTransition(() => {
      setSessionOptions(persisted);
    });

    return persisted;
  };

  return (
    <ConnectionContext.Provider
      value={{
        isReady,
        status,
        options: sessionOptions,
        refreshStatus,
        connect,
        disconnect,
        updateOptions,
      }}
    >
      {children}
    </ConnectionContext.Provider>
  );
}

export function useConnection() {
  const context = useContext(ConnectionContext);

  if (!context) {
    throw new Error("useConnection must be used within a ConnectionProvider");
  }

  return context;
}

export { initialConnectionStatus };
