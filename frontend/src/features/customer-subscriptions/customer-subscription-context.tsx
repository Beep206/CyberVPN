'use client';

import { useQuery } from '@tanstack/react-query';
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  customerSubscriptionsApi,
  type CustomerSubscriptionSummary,
  type CustomerSubscriptionsResponse,
} from '@/lib/api/customer-subscriptions';

const STORAGE_PREFIX = 'cybervpn:selected-subscription';
const SUBSCRIPTIONS_STALE_MS = 30_000;
const SUBSCRIPTIONS_REFETCH_MS = 45_000;

type CustomerSubscriptionContextValue = {
  defaultSubscriptionKey: string | null;
  isError: boolean;
  isLoading: boolean;
  limitations: string[];
  refetch: () => void;
  selectedSubscription: CustomerSubscriptionSummary | null;
  selectedSubscriptionKey: string | null;
  setSelectedSubscriptionKey: (subscriptionKey: string) => void;
  subscriptions: CustomerSubscriptionSummary[];
};

const CustomerSubscriptionContext = createContext<CustomerSubscriptionContextValue | null>(null);

function visiblePolling(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) {
      return false;
    }

    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      return false;
    }

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return false;
    }

    return intervalMs;
  };
}

function getStorageKey(data: CustomerSubscriptionsResponse | undefined): string | null {
  if (!data?.customer_account_id || !data.auth_realm_id) {
    return null;
  }

  return `${STORAGE_PREFIX}:${data.customer_account_id}:${data.auth_realm_id}`;
}

function readStoredSubscriptionKey(storageKey: string | null): string | null {
  if (!storageKey || typeof window === 'undefined') {
    return null;
  }

  return window.localStorage.getItem(storageKey);
}

function writeStoredSubscriptionKey(storageKey: string | null, subscriptionKey: string): void {
  if (!storageKey || typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(storageKey, subscriptionKey);
}

export function CustomerSubscriptionProvider({ children }: { children: ReactNode }) {
  const [selectedSubscriptionKeyOverride, setSelectedSubscriptionKeyOverride] = useState<string | null>(null);

  const subscriptionsQuery = useQuery({
    queryKey: ['customer-subscriptions'],
    queryFn: async () => {
      const response = await customerSubscriptionsApi.list();
      return response.data;
    },
    staleTime: SUBSCRIPTIONS_STALE_MS,
    refetchInterval: visiblePolling(SUBSCRIPTIONS_REFETCH_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
  });

  const data = subscriptionsQuery.data;
  const isError = subscriptionsQuery.isError;
  const isLoading = subscriptionsQuery.isPending;
  const refetchSubscriptions = subscriptionsQuery.refetch;
  const subscriptions = useMemo(() => data?.items ?? [], [data]);
  const storageKey = getStorageKey(data);
  const availableKeys = useMemo(
    () => new Set(subscriptions.map((subscription) => subscription.subscription_key)),
    [subscriptions],
  );

  const storedSubscriptionKey = readStoredSubscriptionKey(storageKey);
  const selectedSubscriptionKey =
    selectedSubscriptionKeyOverride && availableKeys.has(selectedSubscriptionKeyOverride)
      ? selectedSubscriptionKeyOverride
      : storedSubscriptionKey && availableKeys.has(storedSubscriptionKey)
        ? storedSubscriptionKey
        : data?.default_subscription_key ?? null;

  const setSelectedSubscriptionKey = useCallback(
    (subscriptionKey: string) => {
      if (!availableKeys.has(subscriptionKey)) {
        return;
      }

      setSelectedSubscriptionKeyOverride(subscriptionKey);
      writeStoredSubscriptionKey(storageKey, subscriptionKey);
    },
    [availableKeys, storageKey],
  );

  const selectedSubscription = useMemo(
    () =>
      subscriptions.find((subscription) => subscription.subscription_key === selectedSubscriptionKey) ??
      subscriptions.find((subscription) => subscription.subscription_key === data?.default_subscription_key) ??
      null,
    [data?.default_subscription_key, selectedSubscriptionKey, subscriptions],
  );

  const value = useMemo<CustomerSubscriptionContextValue>(
    () => ({
      defaultSubscriptionKey: data?.default_subscription_key ?? null,
      isError,
      isLoading,
      limitations: data?.limitations ?? [],
      refetch: () => {
        void refetchSubscriptions();
      },
      selectedSubscription,
      selectedSubscriptionKey: selectedSubscription?.subscription_key ?? selectedSubscriptionKey,
      setSelectedSubscriptionKey,
      subscriptions,
    }),
    [
      data?.default_subscription_key,
      data?.limitations,
      isError,
      isLoading,
      refetchSubscriptions,
      selectedSubscription,
      selectedSubscriptionKey,
      setSelectedSubscriptionKey,
      subscriptions,
    ],
  );

  return (
    <CustomerSubscriptionContext.Provider value={value}>
      {children}
    </CustomerSubscriptionContext.Provider>
  );
}

export function useCustomerSubscriptions() {
  const context = useContext(CustomerSubscriptionContext);

  if (!context) {
    return {
      defaultSubscriptionKey: null,
      isError: false,
      isLoading: false,
      limitations: [],
      refetch: () => {},
      selectedSubscription: null,
      selectedSubscriptionKey: null,
      setSelectedSubscriptionKey: () => {},
      subscriptions: [],
    } satisfies CustomerSubscriptionContextValue;
  }

  return context;
}
