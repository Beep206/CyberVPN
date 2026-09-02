import { apiClient, CANONICAL_IDEMPOTENCY_HEADER } from './client';
import type { components } from './generated/types';

const IDEMPOTENCY_KEY_PATTERN = /^[A-Za-z0-9._:-]{16,128}$/;

export type CustomerVpnServiceStatus =
  components['schemas']['CustomerVpnServiceStatus'];
export type RemnawaveConnectionReadRequest =
  components['schemas']['RemnawaveConnectionReadRequestResponse'];
export type CustomerRemnawaveConnectionsStatus =
  components['schemas']['CustomerRemnawaveConnectionsStatusResponse'];
export type RemnawaveConnectionDropReceipt =
  components['schemas']['RemnawaveConnectionDropReceiptResponse'];
type RemnawaveConnectionCapabilities =
  components['schemas']['RemnawaveConnectionsCapabilitiesResponse'];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseCustomerStatus(value: unknown): CustomerVpnServiceStatus {
  if (
    !isRecord(value)
    || typeof value.connections_available !== 'boolean'
    || typeof value.usage_available !== 'boolean'
    || typeof value.devices_available !== 'boolean'
    || typeof value.degraded !== 'boolean'
    || (value.degraded_reason !== null && typeof value.degraded_reason !== 'string')
  ) {
    throw new Error('Invalid customer VPN service status response');
  }

  return {
    connections_available: value.connections_available,
    usage_available: value.usage_available,
    devices_available: value.devices_available,
    degraded: value.degraded,
    degraded_reason: value.degraded_reason,
  };
}

function parseConnectionCapabilities(value: unknown): RemnawaveConnectionCapabilities {
  if (
    !isRecord(value)
    || typeof value.read_connections !== 'boolean'
    || typeof value.drop_connections !== 'boolean'
    || typeof value.drop_requires_idempotency_key !== 'boolean'
    || typeof value.drop_outcome_may_be_unknown !== 'boolean'
  ) {
    throw new Error('Invalid customer Remnawave connection capabilities');
  }

  return {
    read_connections: value.read_connections,
    drop_connections: value.drop_connections,
    drop_requires_idempotency_key: value.drop_requires_idempotency_key,
    drop_outcome_may_be_unknown: value.drop_outcome_may_be_unknown,
  };
}

function parseConnectionReadRequest(value: unknown): RemnawaveConnectionReadRequest {
  if (
    !isRecord(value)
    || typeof value.request_id !== 'string'
    || !/^[A-Za-z0-9_-]{43}$/.test(value.request_id)
    || typeof value.poll_after_seconds !== 'number'
    || !Number.isInteger(value.poll_after_seconds)
    || value.poll_after_seconds < 1
    || value.poll_after_seconds > 10
    || typeof value.expires_in_seconds !== 'number'
    || !Number.isInteger(value.expires_in_seconds)
    || value.expires_in_seconds < 60
    || value.expires_in_seconds > 600
  ) {
    throw new Error('Invalid customer Remnawave connection request response');
  }
  return {
    request_id: value.request_id,
    poll_after_seconds: value.poll_after_seconds,
    expires_in_seconds: value.expires_in_seconds,
    capabilities: parseConnectionCapabilities(value.capabilities),
  };
}

function isNonNegativeIntegerOrNull(value: unknown): value is number | null {
  return value === null
    || (typeof value === 'number' && Number.isInteger(value) && value >= 0);
}

function parseCustomerConnectionsStatus(value: unknown): CustomerRemnawaveConnectionsStatus {
  if (
    !isRecord(value)
    || typeof value.is_completed !== 'boolean'
    || typeof value.is_failed !== 'boolean'
    || !isRecord(value.progress)
    || typeof value.progress.total !== 'number'
    || !Number.isInteger(value.progress.total)
    || value.progress.total < 0
    || typeof value.progress.completed !== 'number'
    || !Number.isInteger(value.progress.completed)
    || value.progress.completed < 0
    || value.progress.completed > value.progress.total
    || typeof value.progress.percent !== 'number'
    || value.progress.percent < 0
    || value.progress.percent > 100
    || (value.success !== null && typeof value.success !== 'boolean')
    || (value.connected !== null && typeof value.connected !== 'boolean')
    || !isNonNegativeIntegerOrNull(value.connected_node_count)
    || !isNonNegativeIntegerOrNull(value.active_ip_count)
    || (value.last_seen_at !== null
      && (typeof value.last_seen_at !== 'string' || Number.isNaN(Date.parse(value.last_seen_at))))
  ) {
    throw new Error('Invalid customer Remnawave connections status response');
  }
  return {
    is_completed: value.is_completed,
    is_failed: value.is_failed,
    progress: {
      total: value.progress.total,
      completed: value.progress.completed,
      percent: value.progress.percent,
    },
    success: value.success,
    connected: value.connected,
    connected_node_count: value.connected_node_count,
    active_ip_count: value.active_ip_count,
    last_seen_at: value.last_seen_at,
    capabilities: parseConnectionCapabilities(value.capabilities),
  };
}

function parseConnectionDropReceipt(value: unknown): RemnawaveConnectionDropReceipt {
  if (
    !isRecord(value)
    || typeof value.receipt_id !== 'string'
    || !/^[A-Za-z0-9_-]{43}$/.test(value.receipt_id)
    || (value.state !== 'accepted' && value.state !== 'outcome_unknown')
    || value.retry_allowed !== false
    || typeof value.requires_reconciliation !== 'boolean'
  ) {
    throw new Error('Invalid customer Remnawave connection drop receipt');
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
    throw new Error('Invalid customer Remnawave connection drop receipt');
  }

  return {
    receipt_id: value.receipt_id,
    state: value.state,
    retry_allowed: value.retry_allowed,
    requires_reconciliation: value.requires_reconciliation,
    expires_at: expiresAt,
    expires_in_seconds: expiresInSeconds,
  };
}

export const remnawaveStatusApi = {
  getCustomerStatus: async (): Promise<CustomerVpnServiceStatus> => {
    const response = await apiClient.get<unknown>('/customer/vpn-service-status');
    return parseCustomerStatus(response.data);
  },
  requestCustomerConnections: async (): Promise<RemnawaveConnectionReadRequest> => {
    const response = await apiClient.post<unknown>('/customer/remnawave/connections/requests');
    return parseConnectionReadRequest(response.data);
  },
  getCustomerConnections: async (
    requestId: string,
  ): Promise<CustomerRemnawaveConnectionsStatus> => {
    const response = await apiClient.get<unknown>(
      `/customer/remnawave/connections/requests/${encodeURIComponent(requestId)}`,
    );
    return parseCustomerConnectionsStatus(response.data);
  },
  dropCustomerConnections: async (
    idempotencyKey: string,
  ): Promise<RemnawaveConnectionDropReceipt> => {
    if (!IDEMPOTENCY_KEY_PATTERN.test(idempotencyKey)) {
      throw new TypeError('Customer connection drop idempotency key is invalid');
    }
    const response = await apiClient.post<unknown>(
      '/customer/remnawave/connections/drop',
      undefined,
      { headers: { [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey } },
    );
    return parseConnectionDropReceipt(response.data);
  },
};
