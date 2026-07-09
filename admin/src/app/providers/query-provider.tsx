'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import dynamic from 'next/dynamic';
import { useState } from 'react';
import { queryClientDefaultOptions } from './query-client-policy';

const isReactQueryDevtoolsEnabled =
  process.env.NODE_ENV !== 'production'
  && process.env.NEXT_PUBLIC_ENABLE_REACT_QUERY_DEVTOOLS === 'true';

const ReactQueryDevtools =
  isReactQueryDevtoolsEnabled
    ? dynamic(
        () =>
          import('@tanstack/react-query-devtools').then(
            (mod) => mod.ReactQueryDevtools,
          ),
        { ssr: false },
      )
    : () => null;

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: queryClientDefaultOptions,
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
    </QueryClientProvider>
  );
}
