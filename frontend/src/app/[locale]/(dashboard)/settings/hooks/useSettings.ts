'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { profileApi, twofaApi, securityApi } from '@/lib/api';

/**
 * Hook to fetch user profile
 */
export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: async () => {
      const response = await profileApi.getProfile();
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook to update user profile
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      display_name?: string;
      avatar_url?: string | null;
      language?: string;
      timezone?: string;
    }) => {
      const response = await profileApi.updateProfile(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });
}

/**
 * Hook to fetch 2FA status
 */
export function useTwoFactorStatus() {
  return useQuery({
    queryKey: ['twofa', 'status'],
    queryFn: async () => {
      const response = await twofaApi.getStatus();
      return response.data;
    },
    staleTime: 30 * 1000,
  });
}
