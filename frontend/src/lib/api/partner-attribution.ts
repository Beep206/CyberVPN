import { apiClient } from './client';

export type PartnerAttributionTransferConsumeRequest = {
  transfer_token: string;
};

export type PartnerAttributionTransferConsumeResponse = {
  attribution_id: string;
  expires_at: string;
  masked_code: string;
};

export type PartnerAttributionClaimRequest = {
  fallback_token?: string | null;
};

export type PartnerAttributionClaimResponse = {
  status: string;
  partner_account_id?: string | null;
  partner_code_id?: string | null;
  binding_id?: string | null;
  claimed_at?: string | null;
};

export const partnerAttributionApi = {
  consumeTransfer: (data: PartnerAttributionTransferConsumeRequest) =>
    apiClient.post<PartnerAttributionTransferConsumeResponse>('/partner-attribution/transfer/consume', data),

  claim: (data: PartnerAttributionClaimRequest = {}) =>
    apiClient.post<PartnerAttributionClaimResponse>('/partner-attribution/claim', data),
};
