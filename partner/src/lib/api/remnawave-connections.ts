import { apiClient, CANONICAL_IDEMPOTENCY_HEADER } from './client';
import type { components } from './generated/types';

const OPAQUE_RECEIPT_RE = /^[A-Za-z0-9_-]{43}$/;
const IDEMPOTENCY_KEY_RE = /^[A-Za-z0-9._:-]{16,128}$/;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type RemnawaveConnectionsCapabilities =
  components['schemas']['RemnawaveConnectionsCapabilitiesResponse'];

type GeneratedConnectionReadRequest =
  components['schemas']['RemnawaveConnectionReadRequestResponse'];
export type PartnerRemnawaveConnectionReadRequest = Omit<
  GeneratedConnectionReadRequest,
  'capabilities'
> & {
  capabilities: RemnawaveConnectionsCapabilities;
};

type GeneratedPartnerNodeConnectionsStatus =
  components['schemas']['PartnerRemnawaveNodeConnectionsStatusResponse'];
export type PartnerRemnawaveNodeConnectionsStatus = Omit<
  GeneratedPartnerNodeConnectionsStatus,
  'connected_user_count' | 'active_ip_count' | 'capabilities'
> & {
  connected_user_count: number | null;
  active_ip_count: number | null;
  capabilities: RemnawaveConnectionsCapabilities;
};

export type PartnerRemnawaveConnectionDropReceipt =
  components['schemas']['RemnawaveConnectionDropReceiptResponse'];

export type PartnerRemnawaveConnectionDropRequest =
  components['schemas']['PartnerRemnawaveConnectionDropRequest'];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseCapabilities(value: unknown): RemnawaveConnectionsCapabilities {
  if (
    !isRecord(value)
    || typeof value.read_connections !== 'boolean'
    || typeof value.drop_connections !== 'boolean'
    || typeof value.drop_requires_idempotency_key !== 'boolean'
    || typeof value.drop_outcome_may_be_unknown !== 'boolean'
  ) {
    throw new Error('Invalid partner Remnawave connections capabilities');
  }

  return {
    read_connections: value.read_connections,
    drop_connections: value.drop_connections,
    drop_requires_idempotency_key: value.drop_requires_idempotency_key,
    drop_outcome_may_be_unknown: value.drop_outcome_may_be_unknown,
  };
}

function parseBoundedInteger(
  value: unknown,
  minimum: number,
  maximum: number,
): number | null {
  return typeof value === 'number'
    && Number.isSafeInteger(value)
    && value >= minimum
    && value <= maximum
    ? value
    : null;
}

function parseConnectionReadRequest(value: unknown): PartnerRemnawaveConnectionReadRequest {
  if (!isRecord(value) || typeof value.request_id !== 'string' || !OPAQUE_RECEIPT_RE.test(value.request_id)) {
    throw new Error('Invalid partner Remnawave connection request response');
  }
  const pollAfterSeconds = parseBoundedInteger(value.poll_after_seconds, 1, 10);
  const expiresInSeconds = parseBoundedInteger(value.expires_in_seconds, 60, 600);
  if (pollAfterSeconds === null || expiresInSeconds === null) {
    throw new Error('Invalid partner Remnawave connection request response');
  }

  return {
    request_id: value.request_id,
    poll_after_seconds: pollAfterSeconds,
    expires_in_seconds: expiresInSeconds,
    capabilities: parseCapabilities(value.capabilities),
  };
}

function parseNullableCount(value: unknown): number | null {
  if (value === null) return null;
  const parsed = parseBoundedInteger(value, 0, Number.MAX_SAFE_INTEGER);
  if (parsed === null) {
    throw new Error('Invalid partner Remnawave node connections response');
  }
  return parsed;
}

function parseNullableTimestamp(value: unknown): string | null {
  if (value === null) return null;
  if (typeof value !== 'string' || value.length > 64 || Number.isNaN(Date.parse(value))) {
    throw new Error('Invalid partner Remnawave node connections response');
  }
  return value;
}

function parseNodeConnectionsStatus(
  value: unknown,
  expectedNodeUuid: string,
): PartnerRemnawaveNodeConnectionsStatus {
  if (
    !isRecord(value)
    || value.node_uuid !== expectedNodeUuid
    || typeof value.is_completed !== 'boolean'
    || typeof value.is_failed !== 'boolean'
    || (value.success !== null && typeof value.success !== 'boolean')
  ) {
    throw new Error('Invalid partner Remnawave node connections response');
  }

  const connectedUserCount = parseNullableCount(value.connected_user_count);
  const activeIpCount = parseNullableCount(value.active_ip_count);
  const countsAreBothNull = connectedUserCount === null && activeIpCount === null;
  const countsAreBothPresent = connectedUserCount !== null && activeIpCount !== null;
  if (
    (!countsAreBothNull && !countsAreBothPresent)
    || (countsAreBothPresent && connectedUserCount > activeIpCount)
    || (value.success === null && !countsAreBothNull)
    || (value.success !== null && !countsAreBothPresent)
    || (value.is_failed && value.success === true)
  ) {
    throw new Error('Invalid partner Remnawave node connections response');
  }

  return {
    is_completed: value.is_completed,
    is_failed: value.is_failed,
    success: value.success,
    node_uuid: value.node_uuid,
    connected_user_count: connectedUserCount,
    active_ip_count: activeIpCount,
    last_seen_at: parseNullableTimestamp(value.last_seen_at),
    capabilities: parseCapabilities(value.capabilities),
  };
}

function parseDropReceipt(value: unknown): PartnerRemnawaveConnectionDropReceipt {
  if (
    !isRecord(value)
    || typeof value.receipt_id !== 'string'
    || !OPAQUE_RECEIPT_RE.test(value.receipt_id)
    || (value.state !== 'accepted' && value.state !== 'outcome_unknown')
    || value.retry_allowed !== false
    || typeof value.requires_reconciliation !== 'boolean'
  ) {
    throw new Error('Invalid partner Remnawave connection drop receipt');
  }

  const expiresAt = value.expires_at ?? null;
  const expiresInSeconds = value.expires_in_seconds ?? null;
  const acceptedLifecycleIsValid = value.state === 'accepted'
    && value.requires_reconciliation === false
    && typeof expiresAt === 'string'
    && expiresAt.length > 0
    && expiresAt.length <= 64
    && !Number.isNaN(Date.parse(expiresAt))
    && typeof expiresInSeconds === 'number'
    && Number.isSafeInteger(expiresInSeconds)
    && expiresInSeconds >= 0
    && expiresInSeconds <= 604_800;
  const ambiguousLifecycleIsValid = value.state === 'outcome_unknown'
    && value.requires_reconciliation === true
    && expiresAt === null
    && expiresInSeconds === null;
  if (!acceptedLifecycleIsValid && !ambiguousLifecycleIsValid) {
    throw new Error('Invalid partner Remnawave connection drop receipt');
  }

  return {
    receipt_id: value.receipt_id,
    state: value.state,
    retry_allowed: false,
    requires_reconciliation: value.requires_reconciliation,
    expires_at: expiresAt,
    expires_in_seconds: expiresInSeconds,
  };
}

export const partnerRemnawaveConnectionsApi = {
  requestNodeConnections: async (
    workspaceId: string,
    nodeUuid: string,
  ): Promise<PartnerRemnawaveConnectionReadRequest> => {
    const response = await apiClient.post<unknown>(
      `/partner-workspaces/${encodeURIComponent(workspaceId)}/remnawave/connections/nodes/${encodeURIComponent(nodeUuid)}/requests`,
    );
    return parseConnectionReadRequest(response.data);
  },

  getNodeConnections: async (
    workspaceId: string,
    nodeUuid: string,
    requestId: string,
  ): Promise<PartnerRemnawaveNodeConnectionsStatus> => {
    const response = await apiClient.get<unknown>(
      `/partner-workspaces/${encodeURIComponent(workspaceId)}/remnawave/connections/nodes/${encodeURIComponent(nodeUuid)}/requests/${encodeURIComponent(requestId)}`,
    );
    return parseNodeConnectionsStatus(response.data, nodeUuid);
  },

  dropNodeConnectionsByServiceIdentity: async (
    workspaceId: string,
    nodeUuid: string,
    serviceIdentityUuid: string,
    idempotencyKey: string,
  ): Promise<PartnerRemnawaveConnectionDropReceipt> => {
    if (
      !UUID_RE.test(serviceIdentityUuid)
      || !IDEMPOTENCY_KEY_RE.test(idempotencyKey)
    ) {
      throw new Error('Invalid partner Remnawave connection drop request');
    }
    const payload: PartnerRemnawaveConnectionDropRequest = {
      serviceIdentityUuid,
    };
    const response = await apiClient.post<unknown>(
      `/partner-workspaces/${encodeURIComponent(workspaceId)}/remnawave/connections/nodes/${encodeURIComponent(nodeUuid)}/drop`,
      payload,
      {
        headers: {
          [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey,
        },
      },
    );
    return parseDropReceipt(response.data);
  },
};
