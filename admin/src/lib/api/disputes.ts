import { apiClient } from './client';
import type { operations } from './generated/types';

type ListDisputeCasesParams =
  operations['list_dispute_cases_api_v1_dispute_cases__get']['parameters']['query'];
type ListDisputeCasesResponse =
  operations['list_dispute_cases_api_v1_dispute_cases__get']['responses'][200]['content']['application/json'];
type CreateDisputeCaseRequest =
  operations['create_dispute_case_api_v1_dispute_cases__post']['requestBody']['content']['application/json'];
type CreateDisputeCaseResponse =
  operations['create_dispute_case_api_v1_dispute_cases__post']['responses'][201]['content']['application/json'];
type GetDisputeCaseResponse =
  operations['get_dispute_case_api_v1_dispute_cases__dispute_case_id__get']['responses'][200]['content']['application/json'];

export const disputesApi = {
  listDisputeCases: (params?: ListDisputeCasesParams) =>
    apiClient.get<ListDisputeCasesResponse>('/dispute-cases', { params }),

  createDisputeCase: (data: CreateDisputeCaseRequest) =>
    apiClient.post<CreateDisputeCaseResponse>('/dispute-cases', data),

  getDisputeCase: (disputeCaseId: string) =>
    apiClient.get<GetDisputeCaseResponse>(`/dispute-cases/${disputeCaseId}`),
};

export type {
  CreateDisputeCaseRequest,
  CreateDisputeCaseResponse,
  GetDisputeCaseResponse,
  ListDisputeCasesParams,
  ListDisputeCasesResponse,
};
