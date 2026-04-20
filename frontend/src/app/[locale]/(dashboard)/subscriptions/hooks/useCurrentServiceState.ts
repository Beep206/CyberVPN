import { useQuery } from '@tanstack/react-query';
import {
  DEFAULT_SERVICE_STATE_REQUEST,
  serviceAccessApi,
  type GetCurrentServiceStateRequest,
} from '@/lib/api/service-access';

export function useCurrentServiceState(
  request: GetCurrentServiceStateRequest = DEFAULT_SERVICE_STATE_REQUEST,
) {
  return useQuery({
    queryKey: [
      'current-service-state',
      request.provider_name,
      request.channel_type,
      request.channel_subject_ref,
      request.provisioning_profile_key,
      request.credential_type,
      request.credential_subject_key,
    ],
    queryFn: async () => {
      const response = await serviceAccessApi.getCurrentServiceState(request);
      return response.data;
    },
    staleTime: 30 * 1000,
  });
}
