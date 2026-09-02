import { apiClient } from './client';
import type { components } from './generated/types';
import {
  buildFreshAuthRequestConfig,
  type FreshAuthRequestOptions,
} from './fresh-auth';

type GeneratedRemnawaveCapabilities =
  components['schemas']['AdminRemnawaveCapabilities'];

export const REMNAWAVE_CAPABILITY_KEYS = [
  'numeric_user_ids',
  'connections',
  'geo_check',
  'node_integrations',
  'shared_lists',
  'node_ssh',
  'tags',
  'host_mapper',
  'root_snippets',
  'redis_stream_export',
] as const satisfies readonly (keyof GeneratedRemnawaveCapabilities)[];

export type RemnawaveCapabilityKey = keyof GeneratedRemnawaveCapabilities;
type ExpectNever<T extends never> = T;
export type RemnawaveCapabilityKeysAreExhaustive = ExpectNever<
  Exclude<RemnawaveCapabilityKey, (typeof REMNAWAVE_CAPABILITY_KEYS)[number]>
>;
export type AdminRemnawaveStreamHealth =
  components['schemas']['AdminRemnawaveStreamHealth'];
export type RemnawaveStreamKey = AdminRemnawaveStreamHealth['key'];
export type RemnawaveStreamStatus = AdminRemnawaveStreamHealth['status'];
export type AdminRemnawaveCapabilitiesAndStreams =
  components['schemas']['AdminRemnawaveCapabilitiesAndStreams'];
export type AdminRemnawaveNodeDiagnostics =
  components['schemas']['AdminRemnawaveNodeDiagnosticsResponse'];
export type AdminRemnawaveNodeSshTicket =
  components['schemas']['AdminRemnawaveNodeSshTicketResponse'];
export type RemnawaveResourceGrant =
  components['schemas']['RemnawaveResourceGrantResponse'];
export type RemnawaveResourceGrantCreate =
  components['schemas']['RemnawaveResourceGrantCreateRequest'];
export type RemnawaveResourceGrantRevoke =
  components['schemas']['RemnawaveResourceGrantRevokeRequest'];

export const REMNAWAVE_RESOURCE_TYPES = [
  'node',
  'host',
  'profile',
  'squad',
  'tag',
  'integration',
  'shared_list',
  'service_identity',
] as const satisfies readonly RemnawaveResourceGrantCreate['resource_type'][];

export const REMNAWAVE_PARTNER_PERMISSION_KEYS = [
  'remnawave_read',
  'remnawave_write',
  'remnawave_execute',
] as const;

export type RemnawavePartnerPermissionKey =
  (typeof REMNAWAVE_PARTNER_PERMISSION_KEYS)[number];

export const adminRemnawaveStatusApi = {
  getCapabilitiesAndStreams: () =>
    apiClient.get<AdminRemnawaveCapabilitiesAndStreams>(
      '/admin/remnawave/capabilities-and-streams',
    ),
  getNodeDiagnostics: () =>
    apiClient.get<AdminRemnawaveNodeDiagnostics>(
      '/admin/remnawave/nodes/diagnostics',
    ),
  listResourceGrants: (params: {
    workspace_id?: string;
    include_revoked?: boolean;
  } = {}) =>
    apiClient.get<components['schemas']['RemnawaveResourceGrantListResponse']>(
      '/admin/remnawave-resource-grants',
      { params },
    ),
  createResourceGrant: (data: RemnawaveResourceGrantCreate) =>
    apiClient.post<RemnawaveResourceGrant>(
      '/admin/remnawave-resource-grants',
      data,
    ),
  revokeResourceGrant: (grantId: string, data: RemnawaveResourceGrantRevoke) =>
    apiClient.post<RemnawaveResourceGrant>(
      `/admin/remnawave-resource-grants/${encodeURIComponent(grantId)}/revoke`,
      data,
    ),
  issueNodeSshTicket: (
    nodeUuid: string,
    reason: string,
    options: FreshAuthRequestOptions,
  ) =>
    apiClient.post<AdminRemnawaveNodeSshTicket>(
      `/admin/remnawave/node-ssh/nodes/${encodeURIComponent(nodeUuid)}/tickets`,
      { reason },
      buildFreshAuthRequestConfig(options),
    ),
  revokeNodeSshTicket: (ticket: string, reason: string) =>
    apiClient.post<void>(
      '/admin/remnawave/node-ssh/tickets/revoke',
      { reason, ticket },
    ),
};
