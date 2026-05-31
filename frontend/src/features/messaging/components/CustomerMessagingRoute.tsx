'use client';

import { useContext } from 'react';
import { QueryClientContext } from '@tanstack/react-query';
import { QueryProvider } from '@/app/providers/query-provider';
import { CustomerMessagingClient } from './CustomerMessagingClient';

export function CustomerMessagingRoute() {
  const queryClient = useContext(QueryClientContext);
  const content = <CustomerMessagingClient />;

  if (queryClient) {
    return content;
  }

  return <QueryProvider showDevtools={false}>{content}</QueryProvider>;
}
