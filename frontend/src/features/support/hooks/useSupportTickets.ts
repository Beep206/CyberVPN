import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  supportTicketsApi,
  type SupportTicketCreateRequest,
  type SupportTicketListParams,
  type SupportTicketReplyRequest,
} from '@/lib/api/support-tickets';

export const supportTicketKeys = {
  all: ['support-tickets'] as const,
  detail: (ticketRef: string | null) =>
    [...supportTicketKeys.all, 'detail', ticketRef ?? 'none'] as const,
  lists: () => [...supportTicketKeys.all, 'list'] as const,
  list: (params: SupportTicketListParams) =>
    [
      ...supportTicketKeys.lists(),
      params.status ?? 'all',
      params.category ?? 'all',
      params.cursor ?? 'first',
      params.limit ?? 50,
    ] as const,
};

export function useSupportTicketList(params: SupportTicketListParams) {
  return useQuery({
    queryKey: supportTicketKeys.list(params),
    queryFn: async () => {
      const { data } = await supportTicketsApi.list(params);
      return data;
    },
    staleTime: 30_000,
  });
}

export function useSupportTicketDetail(ticketRef: string | null) {
  return useQuery({
    enabled: Boolean(ticketRef),
    queryKey: supportTicketKeys.detail(ticketRef),
    queryFn: async () => {
      if (!ticketRef) {
        throw new Error('Support ticket reference is required');
      }

      const { data } = await supportTicketsApi.get(ticketRef);
      return data;
    },
    staleTime: 15_000,
  });
}

export function useCreateSupportTicket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SupportTicketCreateRequest) => {
      const { data } = await supportTicketsApi.create(payload);
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: supportTicketKeys.all });
    },
  });
}

export function useReplySupportTicket(ticketRef: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SupportTicketReplyRequest) => {
      if (!ticketRef) {
        throw new Error('Support ticket reference is required');
      }

      const { data } = await supportTicketsApi.reply(ticketRef, payload);
      return data;
    },
    onSuccess: async (ticket) => {
      queryClient.setQueryData(supportTicketKeys.detail(ticket.public_id), ticket);
      await queryClient.invalidateQueries({ queryKey: supportTicketKeys.lists() });
    },
  });
}

export function useCloseSupportTicket(ticketRef: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      if (!ticketRef) {
        throw new Error('Support ticket reference is required');
      }

      const { data } = await supportTicketsApi.close(ticketRef);
      return data;
    },
    onSuccess: async (ticket) => {
      queryClient.setQueryData(supportTicketKeys.detail(ticket.public_id), ticket);
      await queryClient.invalidateQueries({ queryKey: supportTicketKeys.lists() });
    },
  });
}

export function useReopenSupportTicket(ticketRef: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      if (!ticketRef) {
        throw new Error('Support ticket reference is required');
      }

      const { data } = await supportTicketsApi.reopen(ticketRef);
      return data;
    },
    onSuccess: async (ticket) => {
      queryClient.setQueryData(supportTicketKeys.detail(ticket.public_id), ticket);
      await queryClient.invalidateQueries({ queryKey: supportTicketKeys.lists() });
    },
  });
}
