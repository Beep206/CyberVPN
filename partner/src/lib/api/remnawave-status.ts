import { apiClient, CANONICAL_IDEMPOTENCY_HEADER } from './client';
import type { components } from './generated/types';

export type PartnerVpnServiceStatus =
  components['schemas']['PartnerVpnServiceStatus'];
type GeneratedPartnerRemnawaveResource =
  components['schemas']['PartnerRemnawaveResourceResponse'];
export type PartnerRemnawaveSafeMutation =
  components['schemas']['PartnerRemnawaveSafeMutation'];
export type PartnerRemnawaveResource = Omit<GeneratedPartnerRemnawaveResource, 'safe_mutations'> & {
  safe_mutations: PartnerRemnawaveSafeMutation[];
};
type GeneratedPartnerRemnawaveResourceList =
  components['schemas']['PartnerRemnawaveResourceListResponse'];
export type PartnerRemnawaveResourceList = Omit<
  GeneratedPartnerRemnawaveResourceList,
  'items' | 'capabilities'
> & {
  items: PartnerRemnawaveResource[];
  capabilities: Omit<
    GeneratedPartnerRemnawaveResourceList['capabilities'],
    'safe_mutations'
  > & {
    safe_mutations: PartnerRemnawaveSafeMutation[];
  };
};
export type PartnerRemnawaveResourceType =
  components['schemas']['PartnerRemnawaveResourceType'];
export type PartnerProfileTagsMutationRequest =
  components['schemas']['PartnerProfileTagsMutationRequest'];
export type PartnerProfileTagsMutationResponse =
  components['schemas']['PartnerProfileTagsMutationResponse'];
export type PartnerIntegrationMetadataMutationRequest =
  components['schemas']['PartnerIntegrationMetadataMutationRequest'];
export type PartnerIntegrationMetadataMutationResponse =
  components['schemas']['PartnerIntegrationMetadataMutationResponse'];
type GeneratedPartnerRemnawaveMutationReceipt =
  components['schemas']['PartnerRemnawaveMutationReceipt'];
export type PartnerRemnawaveMutationReceipt = Omit<
  GeneratedPartnerRemnawaveMutationReceipt,
  'state'
> & {
  state: 'accepted' | 'reconciliation_required';
};
export type PartnerRemnawaveMutationOutcome<TValue> =
  | { kind: 'completed'; value: TValue }
  | { kind: 'accepted'; receipt: PartnerRemnawaveMutationReceipt }
  | { kind: 'reconciliation_required'; receipt: PartnerRemnawaveMutationReceipt };
type PartnerRemnawavePermission =
  components['schemas']['PartnerRemnawavePermission'];
type PartnerRemnawaveOperation =
  components['schemas']['PartnerRemnawaveOperation'];

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const IDEMPOTENCY_KEY_RE = /^[A-Za-z0-9._:-]{16,160}$/;
const PROFILE_TAG_RE = /^[A-Z0-9_:]{1,36}$/;
const RESOURCE_TYPES = new Set<PartnerRemnawaveResourceType>([
  'node',
  'host',
  'profile',
  'squad',
  'tag',
  'integration',
  'shared_list',
  'service_identity',
]);
const PERMISSIONS = new Set<PartnerRemnawavePermission>([
  'remnawave_read',
  'remnawave_write',
  'remnawave_execute',
]);
const OPERATIONS = new Set<PartnerRemnawaveOperation>([
  'inspect_assignment',
  'mutate_resource',
  'execute_resource',
  'browser_ssh',
]);
const SAFE_MUTATIONS = new Set<PartnerRemnawaveSafeMutation>([
  'profile_tags',
  'integration_metadata',
]);
const SAFE_MUTATION_ORDER: readonly PartnerRemnawaveSafeMutation[] = [
  'profile_tags',
  'integration_metadata',
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseWorkspaceStatus(
  value: unknown,
  expectedWorkspaceId: string,
): PartnerVpnServiceStatus {
  if (!isRecord(value) || !isRecord(value.capabilities)) {
    throw new Error('Invalid partner VPN service status response');
  }

  const workspaceId = value.workspace_id;
  const assignedResources = value.assigned_resources;
  const degradedReason = value.degraded_reason;
  if (
    workspaceId !== expectedWorkspaceId
    || typeof assignedResources !== 'number'
    || !Number.isFinite(assignedResources)
    || assignedResources < 0
    || typeof value.degraded !== 'boolean'
    || (degradedReason !== null && typeof degradedReason !== 'string')
    || typeof value.capabilities.connections !== 'boolean'
    || typeof value.capabilities.usage !== 'boolean'
    || typeof value.capabilities.devices !== 'boolean'
  ) {
    throw new Error('Invalid partner VPN service status response');
  }

  return {
    workspace_id: workspaceId,
    capabilities: {
      connections: value.capabilities.connections,
      usage: value.capabilities.usage,
      devices: value.capabilities.devices,
    },
    assigned_resources: assignedResources,
    degraded: value.degraded,
    degraded_reason: degradedReason,
  };
}

function isAllowedString<TValue extends string>(
  value: unknown,
  allowed: ReadonlySet<TValue>,
): value is TValue {
  return typeof value === 'string' && Array.from(allowed).some((item) => item === value);
}

function isStringArrayFromSet<TValue extends string>(
  value: unknown,
  allowed: ReadonlySet<TValue>,
): value is TValue[] {
  return Array.isArray(value)
    && value.every((item) => isAllowedString(item, allowed))
    && new Set(value).size === value.length;
}

function arraysEqual<TValue>(left: readonly TValue[], right: readonly TValue[]): boolean {
  return left.length === right.length && left.every((item, index) => item === right[index]);
}

function isValidProfileTags(value: unknown): value is string[] {
  return Array.isArray(value)
    && value.length <= 10
    && value.every((tag) => typeof tag === 'string' && PROFILE_TAG_RE.test(tag))
    && new Set(value).size === value.length;
}

function parseResource(
  value: unknown,
  expectedWorkspaceId: string,
  expectedResourceType?: PartnerRemnawaveResourceType,
  expectedResourceUuid?: string,
): PartnerRemnawaveResource {
  if (!isRecord(value)) {
    throw new Error('Invalid partner Remnawave resource response');
  }
  const safeMutations = value.safe_mutations;
  if (
    value.workspace_id !== expectedWorkspaceId
    || !isAllowedString(value.resource_type, RESOURCE_TYPES)
    || typeof value.resource_uuid !== 'string'
    || value.resource_uuid.length === 0
    || (expectedResourceType !== undefined && value.resource_type !== expectedResourceType)
    || (expectedResourceUuid !== undefined && value.resource_uuid !== expectedResourceUuid)
    || !isStringArrayFromSet(value.effective_permissions, PERMISSIONS)
    || !isStringArrayFromSet(value.available_operations, OPERATIONS)
    || !isStringArrayFromSet(value.unavailable_operations, OPERATIONS)
    || !isStringArrayFromSet(value.forbidden_operations, OPERATIONS)
    || typeof value.provider_details_available !== 'boolean'
    || !isStringArrayFromSet(safeMutations, SAFE_MUTATIONS)
  ) {
    throw new Error('Invalid partner Remnawave resource response');
  }

  const availableOperations = value.available_operations;
  const unavailableOperations = value.unavailable_operations;
  const forbiddenOperations = value.forbidden_operations;
  const hasWritePermission = value.effective_permissions.includes('remnawave_write');
  const expectedSafeMutations: PartnerRemnawaveSafeMutation[] = hasWritePermission
    && value.resource_type === 'profile'
    ? ['profile_tags']
    : hasWritePermission && value.resource_type === 'integration'
      ? ['integration_metadata']
      : [];
  const mutationIsAvailable = expectedSafeMutations.length === 1;
  if (
    !arraysEqual(safeMutations, expectedSafeMutations)
    || availableOperations.length !== (mutationIsAvailable ? 2 : 1)
    || !availableOperations.includes('inspect_assignment')
    || availableOperations.includes('execute_resource')
    || availableOperations.includes('browser_ssh')
    || availableOperations.includes('mutate_resource') !== mutationIsAvailable
    || unavailableOperations.length !== (mutationIsAvailable ? 1 : 2)
    || unavailableOperations.includes('execute_resource') !== true
    || unavailableOperations.includes('mutate_resource') === mutationIsAvailable
    || forbiddenOperations.length !== 1
    || forbiddenOperations[0] !== 'browser_ssh'
    || value.provider_details_available
  ) {
    throw new Error('Invalid partner Remnawave resource response');
  }

  return {
    workspace_id: value.workspace_id,
    resource_type: value.resource_type,
    resource_uuid: value.resource_uuid,
    effective_permissions: value.effective_permissions,
    available_operations: availableOperations,
    unavailable_operations: unavailableOperations,
    forbidden_operations: forbiddenOperations,
    provider_details_available: false,
    safe_mutations: safeMutations,
  };
}

function parseResourceList(
  value: unknown,
  expectedWorkspaceId: string,
): PartnerRemnawaveResourceList {
  if (!isRecord(value) || !isRecord(value.capabilities) || !Array.isArray(value.items)) {
    throw new Error('Invalid partner Remnawave resource list response');
  }
  const { capabilities } = value;
  const nextOffset = value.next_offset;
  const safeMutations = capabilities.safe_mutations;
  const stableSafeMutations = SAFE_MUTATION_ORDER.filter(
    (mutation) => Array.isArray(safeMutations) && safeMutations.includes(mutation),
  );
  if (
    value.workspace_id !== expectedWorkspaceId
    || value.items.length > 50
    || typeof value.total !== 'number'
    || !Number.isSafeInteger(value.total)
    || value.total < 0
    || value.total < value.items.length
    || (nextOffset !== null
      && (typeof nextOffset !== 'number'
        || !Number.isSafeInteger(nextOffset)
        || nextOffset < 0
        || nextOffset > 10_000))
    || capabilities.inspect_assignment !== true
    || capabilities.execute_resource !== false
    || capabilities.browser_ssh !== false
    || !isStringArrayFromSet(safeMutations, SAFE_MUTATIONS)
    || !arraysEqual(safeMutations, stableSafeMutations)
    || capabilities.mutate_resource !== (safeMutations.length > 0)
    || capabilities.mutation_unavailable_reason !== (safeMutations.length > 0
      ? 'limited_to_explicit_profile_and_integration_grants'
      : 'no_current_write_granted_safe_mutation')
  ) {
    throw new Error('Invalid partner Remnawave resource list response');
  }

  const items = value.items.map((item) => parseResource(item, expectedWorkspaceId));
  if (items.some((item) => item.safe_mutations.some((mutation) => !safeMutations.includes(mutation)))) {
    throw new Error('Invalid partner Remnawave resource list response');
  }

  return {
    workspace_id: expectedWorkspaceId,
    items,
    total: value.total,
    next_offset: nextOffset,
    capabilities: {
      inspect_assignment: true,
      mutate_resource: safeMutations.length > 0,
      execute_resource: false,
      browser_ssh: false,
      mutation_unavailable_reason: safeMutations.length > 0
        ? 'limited_to_explicit_profile_and_integration_grants'
        : 'no_current_write_granted_safe_mutation',
      safe_mutations: safeMutations,
    },
  };
}

function validateMutationBoundary(
  workspaceId: string,
  resourceUuid: string,
  idempotencyKey: string,
): void {
  if (
    !UUID_RE.test(workspaceId)
    || !UUID_RE.test(resourceUuid)
    || !IDEMPOTENCY_KEY_RE.test(idempotencyKey)
  ) {
    throw new Error('Invalid partner Remnawave mutation request');
  }
}

function parseMutationReceipt(
  value: unknown,
  expectedResourceType: PartnerRemnawaveResourceType,
  expectedResourceUuid: string,
): PartnerRemnawaveMutationReceipt {
  if (
    !isRecord(value)
    || typeof value.attempt_id !== 'string'
    || !UUID_RE.test(value.attempt_id)
    || (value.state !== 'accepted' && value.state !== 'reconciliation_required')
    || value.resource_type !== expectedResourceType
    || value.resource_uuid !== expectedResourceUuid
    || typeof value.requires_reconciliation !== 'boolean'
    || value.requires_reconciliation !== (value.state === 'reconciliation_required')
  ) {
    throw new Error('Invalid partner Remnawave mutation receipt');
  }
  return {
    attempt_id: value.attempt_id,
    state: value.state,
    resource_type: expectedResourceType,
    resource_uuid: expectedResourceUuid,
    requires_reconciliation: value.requires_reconciliation,
  };
}

function parseMutationOutcome<TValue>(
  value: unknown,
  responseStatus: number,
  expectedResourceType: PartnerRemnawaveResourceType,
  expectedResourceUuid: string,
  parseCompleted: (candidate: unknown) => TValue,
): PartnerRemnawaveMutationOutcome<TValue> {
  if (responseStatus !== 200 && responseStatus !== 202) {
    throw new Error('Invalid partner Remnawave mutation response status');
  }
  if (responseStatus === 202 || (isRecord(value) && 'attempt_id' in value)) {
    const receipt = parseMutationReceipt(value, expectedResourceType, expectedResourceUuid);
    return receipt.state === 'accepted'
      ? { kind: 'accepted', receipt }
      : { kind: 'reconciliation_required', receipt };
  }
  return { kind: 'completed', value: parseCompleted(value) };
}

function parseProfileTagsMutationResponse(
  value: unknown,
  expectedResourceUuid: string,
  expectedTags: readonly string[],
): PartnerProfileTagsMutationResponse {
  if (
    !isRecord(value)
    || value.resource_uuid !== expectedResourceUuid
    || !isValidProfileTags(value.tags)
    || !arraysEqual(value.tags, expectedTags)
  ) {
    throw new Error('Invalid partner profile-tags mutation response');
  }
  return { resource_uuid: value.resource_uuid, tags: value.tags };
}

function validateIntegrationMetadataRequest(
  body: PartnerIntegrationMetadataMutationRequest,
): void {
  const keys = Object.keys(body);
  if (
    keys.length === 0
    || keys.some((key) => key !== 'name' && key !== 'description')
  ) {
    throw new Error('Invalid partner integration-metadata mutation request');
  }
  if (
    Object.prototype.hasOwnProperty.call(body, 'name')
    && (typeof body.name !== 'string'
      || body.name.length < 2
      || body.name.length > 30
      || body.name.trim() !== body.name)
  ) {
    throw new Error('Invalid partner integration-metadata mutation request');
  }
  if (
    Object.prototype.hasOwnProperty.call(body, 'description')
    && body.description !== null
    && (typeof body.description !== 'string'
      || body.description.length > 255
      || body.description.trim() !== body.description)
  ) {
    throw new Error('Invalid partner integration-metadata mutation request');
  }
}

function parseIntegrationMetadataMutationResponse(
  value: unknown,
  expectedResourceUuid: string,
  expectedBody: PartnerIntegrationMetadataMutationRequest,
): PartnerIntegrationMetadataMutationResponse {
  if (
    !isRecord(value)
    || value.resource_uuid !== expectedResourceUuid
    || typeof value.name !== 'string'
    || value.name.length < 2
    || value.name.length > 30
    || value.name.trim() !== value.name
    || (value.description !== null
      && (typeof value.description !== 'string'
        || value.description.length > 255
        || value.description.trim() !== value.description))
    || (Object.prototype.hasOwnProperty.call(expectedBody, 'name')
      && value.name !== expectedBody.name)
    || (Object.prototype.hasOwnProperty.call(expectedBody, 'description')
      && value.description !== expectedBody.description)
  ) {
    throw new Error('Invalid partner integration-metadata mutation response');
  }
  return {
    resource_uuid: value.resource_uuid,
    name: value.name,
    description: value.description,
  };
}

export const partnerRemnawaveStatusApi = {
  getWorkspaceStatus: async (workspaceId: string): Promise<PartnerVpnServiceStatus> => {
    const response = await apiClient.get<unknown>(
      `/partner-workspaces/${encodeURIComponent(workspaceId)}/vpn-service-status`,
    );
    return parseWorkspaceStatus(response.data, workspaceId);
  },
  listWorkspaceResources: async (
    workspaceId: string,
    offset = 0,
  ): Promise<PartnerRemnawaveResourceList> => {
    if (!Number.isSafeInteger(offset) || offset < 0 || offset > 10_000) {
      throw new Error('Invalid partner Remnawave resource offset');
    }
    const response = await apiClient.get<unknown>(
      `/partner-workspaces/${encodeURIComponent(workspaceId)}/remnawave/resources`,
      { params: { limit: 50, offset } },
    );
    return parseResourceList(response.data, workspaceId);
  },
  getWorkspaceResource: async (
    workspaceId: string,
    resourceType: PartnerRemnawaveResourceType,
    resourceUuid: string,
  ): Promise<PartnerRemnawaveResource> => {
    const response = await apiClient.get<unknown>(
      `/partner-workspaces/${encodeURIComponent(workspaceId)}/remnawave/resources/${encodeURIComponent(resourceType)}/${encodeURIComponent(resourceUuid)}`,
    );
    return parseResource(response.data, workspaceId, resourceType, resourceUuid);
  },
  updateProfileTags: async (
    workspaceId: string,
    resourceUuid: string,
    body: PartnerProfileTagsMutationRequest,
    idempotencyKey: string,
  ): Promise<PartnerRemnawaveMutationOutcome<PartnerProfileTagsMutationResponse>> => {
    validateMutationBoundary(workspaceId, resourceUuid, idempotencyKey);
    if (!isValidProfileTags(body.tags)) {
      throw new Error('Invalid partner profile-tags mutation request');
    }
    const response = await apiClient.patch<unknown>(
      `/partner-workspaces/${encodeURIComponent(workspaceId)}/remnawave/resources/profile/${encodeURIComponent(resourceUuid)}/tags`,
      body,
      { headers: { [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey } },
    );
    return parseMutationOutcome(
      response.data,
      response.status,
      'profile',
      resourceUuid,
      (candidate) => parseProfileTagsMutationResponse(candidate, resourceUuid, body.tags),
    );
  },
  updateIntegrationMetadata: async (
    workspaceId: string,
    resourceUuid: string,
    body: PartnerIntegrationMetadataMutationRequest,
    idempotencyKey: string,
  ): Promise<PartnerRemnawaveMutationOutcome<PartnerIntegrationMetadataMutationResponse>> => {
    validateMutationBoundary(workspaceId, resourceUuid, idempotencyKey);
    validateIntegrationMetadataRequest(body);
    const response = await apiClient.patch<unknown>(
      `/partner-workspaces/${encodeURIComponent(workspaceId)}/remnawave/resources/integration/${encodeURIComponent(resourceUuid)}/metadata`,
      body,
      { headers: { [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey } },
    );
    return parseMutationOutcome(
      response.data,
      response.status,
      'integration',
      resourceUuid,
      (candidate) => parseIntegrationMetadataMutationResponse(candidate, resourceUuid, body),
    );
  },
};
