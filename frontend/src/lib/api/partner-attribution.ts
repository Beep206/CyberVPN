import { apiClient } from './client';
import type { operations } from './generated/types';

export type PartnerAttributionTransferConsumeRequest =
  operations['consume_partner_attribution_transfer_api_v1_partner_attribution_transfer_consume_post']['requestBody']['content']['application/json'];

export type PartnerAttributionTransferConsumeResponse =
  operations['consume_partner_attribution_transfer_api_v1_partner_attribution_transfer_consume_post']['responses'][200]['content']['application/json'];

export type PartnerAttributionClaimRequest =
  operations['claim_partner_attribution_api_v1_partner_attribution_claim_post']['requestBody']['content']['application/json'];

export type PartnerAttributionClaimResponse =
  operations['claim_partner_attribution_api_v1_partner_attribution_claim_post']['responses'][200]['content']['application/json'];

export const partnerAttributionApi = {
  consumeTransfer: (data: PartnerAttributionTransferConsumeRequest) =>
    apiClient.post<PartnerAttributionTransferConsumeResponse>('/partner-attribution/transfer/consume', data),

  claim: (data: PartnerAttributionClaimRequest = {}) =>
    apiClient.post<PartnerAttributionClaimResponse>('/partner-attribution/claim', data),
};
