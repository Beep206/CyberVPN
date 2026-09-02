import type { AxiosResponse } from 'axios';
import { apiClient, CANONICAL_IDEMPOTENCY_HEADER } from './client';
import type { components } from './generated/types';

const OPERATOR_PREFIX = '/admin/remnawave-operator';

export const REMNAWAVE_TAG_RESOURCES = [
  'subscription-page-configs',
  'users',
  'subscription-templates',
  'config-profiles',
  'internal-squads',
  'external-squads',
  'nodes',
  'node-plugins',
  'hosts',
] as const;

export const REMNAWAVE_MUTABLE_TAG_RESOURCES = [
  'subscription-page-configs',
  'subscription-templates',
  'config-profiles',
  'internal-squads',
  'external-squads',
  'node-plugins',
] as const;

export type RemnawaveTagResource = (typeof REMNAWAVE_TAG_RESOURCES)[number];
export type RemnawaveMutableTagResource =
  (typeof REMNAWAVE_MUTABLE_TAG_RESOURCES)[number];

export type OperatorMutationReceipt =
  components['schemas']['OperatorMutationReceipt'];

export type OperatorMutationOutcome<T> =
  | { kind: 'committed'; resource: T }
  | { kind: 'reconciliation'; receipt: OperatorMutationReceipt };

export type RemnawaveTags = components['schemas']['TagsResponse'];
export type SetRemnawaveTagsRequest = components['schemas']['SetTagsRequest'];
export type SetRemnawaveTagsResponse = components['schemas']['SetTagsResponse'];
export type GeoCheckRequest = components['schemas']['GeoCheckRequest'];
export type GeoCheckJob = components['schemas']['GeoCheckJobResponse'];
export type GeoCheckImage = components['schemas']['GeoCheckImage'];
export type GeoCheckResult = components['schemas']['GeoCheckResult'];
export type GeoCheckStatus = components['schemas']['GeoCheckResultResponse'];
export type NodeIntegration = components['schemas']['NodeIntegration'];
export type NodeIntegrationCollection =
  components['schemas']['AdminNodeIntegrationCollection'];
export type CreateNodeIntegrationRequest =
  components['schemas']['CreateNodeIntegrationRequest'];
export type UpdateNodeIntegrationRequest =
  components['schemas']['UpdateNodeIntegrationRequest'];
export type SharedListPreview = components['schemas']['SharedListPreview'];
export type SharedListPreviewCollection =
  components['schemas']['AdminSharedListPreviewCollection'];
export type SharedList = components['schemas']['SharedList'];
export type SharedListMutationRequest =
  components['schemas']['SharedListMutationRequest'];
export type RootSnippet = components['schemas']['Snippet'];
export type RootSnippetCollection = components['schemas']['AdminSnippetCollection'];
export type RootSnippetMutationRequest = components['schemas']['SnippetMutationRequest'];

function isOperatorMutationReceipt(value: unknown): value is OperatorMutationReceipt {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Partial<OperatorMutationReceipt>;
  return (
    typeof candidate.attempt_id === 'string'
    && (candidate.state === 'accepted' || candidate.state === 'reconciliation_required')
    && typeof candidate.resource_kind === 'string'
    && typeof candidate.requires_reconciliation === 'boolean'
  );
}

function classifyMutation<T>(
  response: AxiosResponse<T | OperatorMutationReceipt>,
): OperatorMutationOutcome<T> {
  if (response.status === 202) {
    if (!isOperatorMutationReceipt(response.data)) {
      throw new Error('Invalid Remnawave reconciliation receipt');
    }
    return { kind: 'reconciliation', receipt: response.data };
  }
  return { kind: 'committed', resource: response.data as T };
}

function classifyDeletion(
  response: AxiosResponse<null | OperatorMutationReceipt>,
): OperatorMutationOutcome<null> {
  const outcome = classifyMutation(response);
  return outcome.kind === 'reconciliation'
    ? outcome
    : { kind: 'committed', resource: null };
}

export function createOperatorIdempotencyKey(): string {
  if (
    typeof globalThis.crypto === 'undefined'
    || typeof globalThis.crypto.randomUUID !== 'function'
  ) {
    throw new Error('Secure idempotency key generation is unavailable');
  }
  return globalThis.crypto.randomUUID();
}

function mutationHeaders(idempotencyKey: string) {
  return { [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey };
}

export const remnawaveOperatorApi = {
  getTags: (resource: RemnawaveTagResource) =>
    apiClient.get<RemnawaveTags>(
      `${OPERATOR_PREFIX}/tags/${encodeURIComponent(resource)}`,
    ),
  setTags: async (
    resource: RemnawaveMutableTagResource,
    data: SetRemnawaveTagsRequest,
    idempotencyKey: string,
  ) => classifyMutation(
    await apiClient.patch<SetRemnawaveTagsResponse | OperatorMutationReceipt>(
      `${OPERATOR_PREFIX}/tags/${encodeURIComponent(resource)}`,
      data,
      { headers: mutationHeaders(idempotencyKey) },
    ),
  ),
  startGeoCheck: async (
    nodeUuid: string,
    data: GeoCheckRequest,
    idempotencyKey: string,
  ) => classifyMutation(
    await apiClient.post<GeoCheckJob | OperatorMutationReceipt>(
      `${OPERATOR_PREFIX}/geocheck/nodes/${encodeURIComponent(nodeUuid)}`,
      data,
      { headers: mutationHeaders(idempotencyKey) },
    ),
  ),
  getGeoCheck: (jobId: string) =>
    apiClient.get<GeoCheckStatus>(
      `${OPERATOR_PREFIX}/geocheck/jobs/${encodeURIComponent(jobId)}`,
    ),
  listNodeIntegrations: () =>
    apiClient.get<NodeIntegrationCollection>(`${OPERATOR_PREFIX}/node-integrations`),
  createNodeIntegration: async (
    data: CreateNodeIntegrationRequest,
    idempotencyKey: string,
  ) => classifyMutation(
    await apiClient.post<NodeIntegration | OperatorMutationReceipt>(
      `${OPERATOR_PREFIX}/node-integrations`,
      data,
      { headers: mutationHeaders(idempotencyKey) },
    ),
  ),
  updateNodeIntegration: async (
    data: UpdateNodeIntegrationRequest,
    idempotencyKey: string,
  ) => classifyMutation(
    await apiClient.patch<NodeIntegration | OperatorMutationReceipt>(
      `${OPERATOR_PREFIX}/node-integrations`,
      data,
      { headers: mutationHeaders(idempotencyKey) },
    ),
  ),
  deleteNodeIntegration: async (uuid: string, idempotencyKey: string) => {
    const response = await apiClient.delete<null | OperatorMutationReceipt>(
      `${OPERATOR_PREFIX}/node-integrations/${encodeURIComponent(uuid)}`,
      { headers: mutationHeaders(idempotencyKey) },
    );
    return classifyDeletion(response);
  },
  listSharedLists: () =>
    apiClient.get<SharedListPreviewCollection>(`${OPERATOR_PREFIX}/shared-lists`),
  getSharedList: (name: string) =>
    apiClient.get<SharedList>(`${OPERATOR_PREFIX}/shared-lists/by-name`, {
      params: { name },
    }),
  createSharedList: async (
    data: SharedListMutationRequest,
    idempotencyKey: string,
  ) => classifyMutation(
    await apiClient.post<SharedList | OperatorMutationReceipt>(
      `${OPERATOR_PREFIX}/shared-lists`,
      data,
      { headers: mutationHeaders(idempotencyKey) },
    ),
  ),
  updateSharedList: async (
    data: SharedListMutationRequest,
    idempotencyKey: string,
  ) => classifyMutation(
    await apiClient.patch<SharedList | OperatorMutationReceipt>(
      `${OPERATOR_PREFIX}/shared-lists`,
      data,
      { headers: mutationHeaders(idempotencyKey) },
    ),
  ),
  deleteSharedList: async (name: string, idempotencyKey: string) =>
    classifyDeletion(
      await apiClient.delete<null | OperatorMutationReceipt>(
        `${OPERATOR_PREFIX}/shared-lists`,
        {
          data: { name },
          headers: mutationHeaders(idempotencyKey),
        },
      ),
    ),
  syncSharedList: async (name: string, idempotencyKey: string) =>
    classifyMutation(
      await apiClient.post<null | OperatorMutationReceipt>(
        `${OPERATOR_PREFIX}/shared-lists/actions/sync`,
        { name },
        { headers: mutationHeaders(idempotencyKey) },
      ),
    ),
  listRootSnippets: () =>
    apiClient.get<RootSnippetCollection>(`${OPERATOR_PREFIX}/snippets`),
  createRootSnippet: async (
    data: RootSnippetMutationRequest,
    idempotencyKey: string,
  ) => classifyMutation(
    await apiClient.post<RootSnippet | OperatorMutationReceipt>(
      `${OPERATOR_PREFIX}/snippets`,
      data,
      { headers: mutationHeaders(idempotencyKey) },
    ),
  ),
  updateRootSnippet: async (
    data: RootSnippetMutationRequest,
    idempotencyKey: string,
  ) => classifyMutation(
    await apiClient.patch<RootSnippet | OperatorMutationReceipt>(
      `${OPERATOR_PREFIX}/snippets`,
      data,
      { headers: mutationHeaders(idempotencyKey) },
    ),
  ),
  deleteRootSnippet: async (name: string, idempotencyKey: string) =>
    classifyDeletion(
      await apiClient.delete<null | OperatorMutationReceipt>(
        `${OPERATOR_PREFIX}/snippets`,
        {
          data: { name },
          headers: mutationHeaders(idempotencyKey),
        },
      ),
    ),
  syncRootSnippet: async (name: string, idempotencyKey: string) =>
    classifyMutation(
      await apiClient.post<null | OperatorMutationReceipt>(
        `${OPERATOR_PREFIX}/snippets/actions/sync`,
        { name },
        { headers: mutationHeaders(idempotencyKey) },
      ),
    ),
};
