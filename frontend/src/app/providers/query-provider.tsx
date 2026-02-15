'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { AxiosError } from 'axios';
import dynamic from 'next/dynamic';
import { useState } from 'react';

const STALE_TIME = 60_000; // 1 min
const MAX_RETRY_ATTEMPTS = 2;

function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  const status = (error as AxiosError).response?.status;

  // Auth, validation, and missing-resource errors should fail fast.
  if (status && status < 500) {
    return false;
  }

  // Retry only transient server/network failures with a strict cap.
  return failureCount < MAX_RETRY_ATTEMPTS;
}

function exponentialRetryDelay(attemptIndex: number): number {
  return Math.min(1_000 * 2 ** attemptIndex, 10_000);
}

const ReactQueryDevtools =
  process.env.NODE_ENV === 'production'
    ? () => null
    : dynamic(
        () =>
          import('@tanstack/react-query-devtools').then(
            (mod) => mod.ReactQueryDevtools,
          ),
        { ssr: false },
      );

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: STALE_TIME,
            retry: shouldRetryQuery,
            retryDelay: exponentialRetryDelay,
            refetchOnWindowFocus: false,
            refetchOnReconnect: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
    </QueryClientProvider>
  );
}
