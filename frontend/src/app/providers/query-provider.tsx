'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import dynamic from 'next/dynamic';
import { useState } from 'react';
import { queryClientDefaultOptions } from './query-client-policy';

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

type QueryProviderProps = {
  children: React.ReactNode;
  showDevtools?: boolean;
};

export function QueryProvider({ children, showDevtools = false }: QueryProviderProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: queryClientDefaultOptions,
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {showDevtools ? (
        <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
      ) : null}
    </QueryClientProvider>
  );
}
