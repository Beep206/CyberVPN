'use client';

import { useContext } from 'react';
import { QueryClientContext } from '@tanstack/react-query';
import { QueryProvider } from '@/app/providers/query-provider';
import { SupportTicketsClient } from './SupportTicketsClient';

type SupportTicketsRouteProps = {
  variant: 'dashboard' | 'miniapp';
};

export function SupportTicketsRoute({ variant }: SupportTicketsRouteProps) {
  const queryClient = useContext(QueryClientContext);
  const content = <SupportTicketsClient variant={variant} />;

  if (queryClient) {
    return content;
  }

  return <QueryProvider showDevtools={false}>{content}</QueryProvider>;
}
