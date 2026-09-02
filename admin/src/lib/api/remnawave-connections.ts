import { apiClient } from './client';
import type { components } from './generated/types';

const REQUEST_ID_PATTERN = /^[A-Za-z0-9_-]{43}$/;
const IDEMPOTENCY_KEY_PATTERN = /^[A-Za-z0-9._:-]{16,128}$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const RECONCILIATION_REFERENCE_PATTERN = /^(?:CASE|INC|REQ|TKT|RW)-[A-Z0-9][A-Z0-9_-]{5,58}$/;
const MAX_CONNECTION_ROWS = 5_000;
const MAX_UNRESOLVED_RECEIPTS = 100;

export type RemnawaveConnectionsCapabilities =
  components['schemas']['RemnawaveConnectionsCapabilitiesResponse'];
type GeneratedReadRequest =
  components['schemas']['RemnawaveConnectionReadRequestResponse'];
export type RemnawaveConnectionReadRequest = Omit<
  GeneratedReadRequest,
  'capabilities'
> & { capabilities: RemnawaveConnectionsCapabilities };
export type RemnawaveConnectionProgress =
  components['schemas']['RemnawaveConnectionProgressResponse'];
export type AdminRemnawaveConnectionIp =
  components['schemas']['AdminRemnawaveConnectionIpResponse'];
export type AdminRemnawaveUserConnectionNode =
  components['schemas']['AdminRemnawaveUserConnectionNodeResponse'];
type GeneratedUserConnectionsStatus =
  components['schemas']['AdminRemnawaveUserConnectionsStatusResponse'];
export type AdminRemnawaveUserConnectionsStatus = Omit<
  GeneratedUserConnectionsStatus,
  'capabilities'
> & { capabilities: RemnawaveConnectionsCapabilities };
export type AdminRemnawaveNodeConnectionUser =
  components['schemas']['AdminRemnawaveNodeConnectionUserResponse'];
type GeneratedNodeConnectionsStatus =
  components['schemas']['AdminRemnawaveNodeConnectionsStatusResponse'];
export type AdminRemnawaveNodeConnectionsStatus = Omit<
  GeneratedNodeConnectionsStatus,
  'capabilities'
> & { capabilities: RemnawaveConnectionsCapabilities };
export type AdminRemnawaveConnectionDropRequest =
  components['schemas']['AdminRemnawaveConnectionDropRequest'];
export type RemnawaveConnectionDropReceipt =
  components['schemas']['RemnawaveConnectionDropReceiptResponse'];
export type AdminRemnawaveConnectionDropReceipt =
  components['schemas']['AdminRemnawaveConnectionDropReceiptResponse'];
export type AdminRemnawaveConnectionDropUnresolvedPage =
  components['schemas']['AdminRemnawaveConnectionDropUnresolvedPageResponse'];
export type AdminRemnawaveConnectionDropReconciliationRequest =
  components['schemas']['AdminRemnawaveConnectionDropReconciliationRequest'];
export type RemnawaveConnectionDropReconciliationReason =
  components['schemas']['RemnawaveConnectionDropReconciliationReason'];

const RECONCILIATION_REASONS = new Set<RemnawaveConnectionDropReconciliationReason>([
  'provider_confirmed_applied',
  'provider_confirmed_not_applied',
  'postcondition_confirmed_applied',
  'postcondition_confirmed_not_applied',
]);

function responseError(label: string): Error {
  return new Error(`Invalid ${label} response from CyberVPN API`);
}

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw responseError(label);
  }
  return value as Record<string, unknown>;
}

function asBoolean(value: unknown, label: string): boolean {
  if (typeof value !== 'boolean') throw responseError(label);
  return value;
}

function asBoundedInteger(
  value: unknown,
  label: string,
  minimum: number,
  maximum: number,
): number {
  if (
    typeof value !== 'number'
    || !Number.isInteger(value)
    || value < minimum
    || value > maximum
  ) {
    throw responseError(label);
  }
  return value;
}

function asBoundedNumber(
  value: unknown,
  label: string,
  minimum: number,
  maximum: number,
): number {
  if (
    typeof value !== 'number'
    || !Number.isFinite(value)
    || value < minimum
    || value > maximum
  ) {
    throw responseError(label);
  }
  return value;
}

function asString(value: unknown, label: string, maximum: number): string {
  if (typeof value !== 'string' || value.length === 0 || value.length > maximum) {
    throw responseError(label);
  }
  return value;
}

function asUuid(value: unknown, label: string): string {
  const uuid = asString(value, label, 36);
  if (!UUID_PATTERN.test(uuid)) throw responseError(label);
  return uuid;
}

function asTimestamp(value: unknown, label: string): string {
  const timestamp = asString(value, label, 64);
  if (Number.isNaN(Date.parse(timestamp))) throw responseError(label);
  return timestamp;
}

function asNullableTimestamp(value: unknown, label: string): string | null {
  if (value === null) return null;
  return asTimestamp(value, label);
}

function asBoundedArray(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value) || value.length > MAX_CONNECTION_ROWS) {
    throw responseError(label);
  }
  return value;
}

function parseCapabilities(value: unknown): RemnawaveConnectionsCapabilities {
  const record = asRecord(value, 'connections capabilities');
  return {
    read_connections: asBoolean(record.read_connections, 'read capability'),
    drop_connections: asBoolean(record.drop_connections, 'drop capability'),
    drop_requires_idempotency_key: asBoolean(
      record.drop_requires_idempotency_key,
      'drop idempotency capability',
    ),
    drop_outcome_may_be_unknown: asBoolean(
      record.drop_outcome_may_be_unknown,
      'drop outcome capability',
    ),
  };
}

function parseIp(value: unknown): AdminRemnawaveConnectionIp {
  const record = asRecord(value, 'connection IP');
  return {
    ip: asString(record.ip, 'connection IP', 64),
    last_seen: asTimestamp(record.last_seen, 'connection last-seen timestamp'),
  };
}

function parseRequest(value: unknown): RemnawaveConnectionReadRequest {
  const record = asRecord(value, 'connection request');
  const requestId = asString(record.request_id, 'connection request ID', 43);
  if (!REQUEST_ID_PATTERN.test(requestId)) throw responseError('connection request ID');

  return {
    request_id: requestId,
    poll_after_seconds: asBoundedInteger(record.poll_after_seconds, 'poll interval', 1, 10),
    expires_in_seconds: asBoundedInteger(record.expires_in_seconds, 'request expiry', 60, 600),
    capabilities: parseCapabilities(record.capabilities),
  };
}

function parseUserStatus(value: unknown): AdminRemnawaveUserConnectionsStatus {
  const record = asRecord(value, 'user connections status');
  const progress = asRecord(record.progress, 'connection progress');
  let result: AdminRemnawaveUserConnectionsStatus['result'] = null;
  let connectionIpCount = 0;

  if (record.result !== null) {
    const resultRecord = asRecord(record.result, 'user connections result');
    result = {
      success: asBoolean(resultRecord.success, 'user connections success'),
      user_id: asBoundedInteger(resultRecord.user_id, 'Remnawave user ID', 1, Number.MAX_SAFE_INTEGER),
      nodes: asBoundedArray(resultRecord.nodes, 'user connection nodes').map((node) => {
        const nodeRecord = asRecord(node, 'user connection node');
        const rawIps = asBoundedArray(nodeRecord.ips, 'connection node IPs');
        connectionIpCount += rawIps.length;
        if (connectionIpCount > MAX_CONNECTION_ROWS) {
          throw responseError('user connection row limit');
        }
        return {
          node_uuid: asUuid(nodeRecord.node_uuid, 'connection node UUID'),
          node_name: asString(nodeRecord.node_name, 'connection node name', 256),
          country_code: asString(nodeRecord.country_code, 'connection country code', 16),
          ips: rawIps.map(parseIp),
        };
      }),
    };
  }

  return {
    is_completed: asBoolean(record.is_completed, 'user request completion'),
    is_failed: asBoolean(record.is_failed, 'user request failure'),
    progress: {
      total: asBoundedInteger(progress.total, 'connection progress total', 0, Number.MAX_SAFE_INTEGER),
      completed: asBoundedInteger(
        progress.completed,
        'connection progress completed',
        0,
        Number.MAX_SAFE_INTEGER,
      ),
      percent: asBoundedNumber(progress.percent, 'connection progress percent', 0, 100),
    },
    result,
    capabilities: parseCapabilities(record.capabilities),
  };
}

function parseNodeStatus(value: unknown): AdminRemnawaveNodeConnectionsStatus {
  const record = asRecord(value, 'node connections status');
  let result: AdminRemnawaveNodeConnectionsStatus['result'] = null;
  let connectionIpCount = 0;

  if (record.result !== null) {
    const resultRecord = asRecord(record.result, 'node connections result');
    result = {
      success: asBoolean(resultRecord.success, 'node connections success'),
      node_uuid: asUuid(resultRecord.node_uuid, 'connection node UUID'),
      users: asBoundedArray(resultRecord.users, 'node connection users').map((user) => {
        const userRecord = asRecord(user, 'node connection user');
        const rawIps = asBoundedArray(userRecord.ips, 'connection user IPs');
        connectionIpCount += rawIps.length;
        if (connectionIpCount > MAX_CONNECTION_ROWS) {
          throw responseError('node connection row limit');
        }
        return {
          user_id: asBoundedInteger(
            userRecord.user_id,
            'Remnawave user ID',
            1,
            Number.MAX_SAFE_INTEGER,
          ),
          ips: rawIps.map(parseIp),
        };
      }),
    };
  }

  return {
    is_completed: asBoolean(record.is_completed, 'node request completion'),
    is_failed: asBoolean(record.is_failed, 'node request failure'),
    result,
    capabilities: parseCapabilities(record.capabilities),
  };
}

function parseDropReceipt(value: unknown): RemnawaveConnectionDropReceipt {
  const record = asRecord(value, 'connection drop receipt');
  const receiptId = asString(record.receipt_id, 'connection drop receipt ID', 43);
  if (!REQUEST_ID_PATTERN.test(receiptId)) throw responseError('connection drop receipt ID');
  if (record.state !== 'accepted' && record.state !== 'outcome_unknown') {
    throw responseError('connection drop state');
  }
  if (record.retry_allowed !== false || typeof record.requires_reconciliation !== 'boolean') {
    throw responseError('connection drop retry contract');
  }

  const expiresAt = record.expires_at ?? null;
  const expiresInSeconds = record.expires_in_seconds ?? null;
  const acceptedLifecycleIsValid = record.state === 'accepted'
    && record.requires_reconciliation === false
    && typeof expiresAt === 'string'
    && expiresAt.length > 0
    && expiresAt.length <= 64
    && !Number.isNaN(Date.parse(expiresAt))
    && typeof expiresInSeconds === 'number'
    && Number.isSafeInteger(expiresInSeconds)
    && expiresInSeconds >= 0
    && expiresInSeconds <= 604_800;
  const ambiguousLifecycleIsValid = record.state === 'outcome_unknown'
    && record.requires_reconciliation === true
    && expiresAt === null
    && expiresInSeconds === null;
  if (!acceptedLifecycleIsValid && !ambiguousLifecycleIsValid) {
    throw responseError('connection drop lifecycle');
  }

  return {
    receipt_id: receiptId,
    state: record.state,
    retry_allowed: false,
    requires_reconciliation: record.requires_reconciliation,
    expires_at: expiresAt,
    expires_in_seconds: expiresInSeconds,
  };
}

function asReconciliationReason(
  value: unknown,
  label: string,
): RemnawaveConnectionDropReconciliationReason {
  if (
    typeof value !== 'string'
    || !RECONCILIATION_REASONS.has(value as RemnawaveConnectionDropReconciliationReason)
  ) {
    throw responseError(label);
  }
  return value as RemnawaveConnectionDropReconciliationReason;
}

function isAppliedReason(reason: RemnawaveConnectionDropReconciliationReason): boolean {
  return reason === 'provider_confirmed_applied'
    || reason === 'postcondition_confirmed_applied';
}

function parseAdminDropReceipt(value: unknown): AdminRemnawaveConnectionDropReceipt {
  const record = asRecord(value, 'admin connection drop receipt');
  const receiptId = asString(record.receipt_id, 'admin connection drop receipt ID', 43);
  if (!REQUEST_ID_PATTERN.test(receiptId)) {
    throw responseError('admin connection drop receipt ID');
  }

  const state = record.state;
  if (state !== 'outcome_unknown' && state !== 'accepted' && state !== 'rejected') {
    throw responseError('admin connection drop state');
  }
  const audience = record.audience;
  if (audience !== 'admin' && audience !== 'partner' && audience !== 'customer') {
    throw responseError('admin connection drop audience');
  }

  const expiresAt = asNullableTimestamp(record.expires_at, 'admin connection drop expiry');
  const expiresInSeconds = record.expires_in_seconds == null
    ? null
    : asBoundedInteger(
      record.expires_in_seconds,
      'admin connection drop expiry seconds',
      0,
      604_800,
    );
  const requiresReconciliation = asBoolean(
    record.requires_reconciliation,
    'admin connection drop reconciliation state',
  );
  const reconciledAt = asNullableTimestamp(
    record.reconciled_at,
    'admin connection drop reconciled timestamp',
  );
  const reconciliationReason = record.reconciliation_reason === null
    ? null
    : asReconciliationReason(
      record.reconciliation_reason,
      'admin connection drop reconciliation reason',
    );
  const reconciliationReference = record.reconciliation_reference == null
    ? null
    : asString(
      record.reconciliation_reference,
      'admin connection drop reconciliation reference',
      64,
    );
  if (
    reconciliationReference !== null
    && !RECONCILIATION_REFERENCE_PATTERN.test(reconciliationReference)
  ) {
    throw responseError('admin connection drop reconciliation reference');
  }

  const reconciliationMetadata = [
    reconciledAt,
    reconciliationReason,
    reconciliationReference,
  ];
  const hasAnyReconciliationMetadata = reconciliationMetadata.some((item) => item !== null);
  const hasCompleteReconciliationMetadata = reconciliationMetadata.every((item) => item !== null);
  if (hasAnyReconciliationMetadata !== hasCompleteReconciliationMetadata) {
    throw responseError('admin connection drop reconciliation metadata');
  }

  const unknownLifecycleIsValid = state === 'outcome_unknown'
    && requiresReconciliation
    && expiresAt === null
    && expiresInSeconds === null
    && !hasAnyReconciliationMetadata;
  const terminalLifecycleIsValid = state !== 'outcome_unknown'
    && !requiresReconciliation
    && expiresAt !== null
    && expiresInSeconds !== null;
  if (!unknownLifecycleIsValid && !terminalLifecycleIsValid) {
    throw responseError('admin connection drop lifecycle');
  }
  if (
    hasCompleteReconciliationMetadata
    && reconciliationReason !== null
    && ((state === 'accepted') !== isAppliedReason(reconciliationReason))
  ) {
    throw responseError('admin connection drop reconciliation outcome');
  }

  return {
    receipt_id: receiptId,
    state,
    audience,
    created_at: asTimestamp(record.created_at, 'admin connection drop created timestamp'),
    updated_at: asTimestamp(record.updated_at, 'admin connection drop updated timestamp'),
    expires_at: expiresAt,
    expires_in_seconds: expiresInSeconds,
    requires_reconciliation: requiresReconciliation,
    reconciled_at: reconciledAt,
    reconciliation_reason: reconciliationReason,
    reconciliation_reference: reconciliationReference,
  };
}

function parseUnresolvedDropReceipts(
  value: unknown,
): AdminRemnawaveConnectionDropUnresolvedPage {
  const record = asRecord(value, 'unresolved connection drop receipt page');
  if (!Array.isArray(record.items) || record.items.length > MAX_UNRESOLVED_RECEIPTS) {
    throw responseError('unresolved connection drop receipts');
  }
  const items = record.items.map(parseAdminDropReceipt);
  if (items.some((item) => item.state !== 'outcome_unknown' || !item.requires_reconciliation)) {
    throw responseError('unresolved connection drop receipt lifecycle');
  }
  const nextCursor = record.next_cursor == null
    ? null
    : canonicalReceiptId(record.next_cursor, 'Unresolved receipt cursor');
  return { items, next_cursor: nextCursor };
}

function positiveUserId(userId: number): number {
  if (!Number.isSafeInteger(userId) || userId < 1) {
    throw new TypeError('Remnawave user ID must be a positive safe integer');
  }
  return userId;
}

function canonicalUuid(uuid: string): string {
  if (!UUID_PATTERN.test(uuid)) throw new TypeError('Node UUID is invalid');
  return uuid.toLowerCase();
}

function canonicalRequestId(requestId: string): string {
  if (!REQUEST_ID_PATTERN.test(requestId)) throw new TypeError('Connection request ID is invalid');
  return requestId;
}

function canonicalReceiptId(receiptId: unknown, label = 'Connection drop receipt ID'): string {
  if (typeof receiptId !== 'string' || !REQUEST_ID_PATTERN.test(receiptId)) {
    throw new TypeError(`${label} is invalid`);
  }
  return receiptId;
}

function canonicalReconciliationRequest(
  body: AdminRemnawaveConnectionDropReconciliationRequest,
): AdminRemnawaveConnectionDropReconciliationRequest {
  const outcome = body.outcome;
  const reason = body.reason;
  const reference = body.reference.trim().toUpperCase();
  if (outcome !== 'accepted' && outcome !== 'rejected') {
    throw new TypeError('Connection drop reconciliation outcome is invalid');
  }
  if (!RECONCILIATION_REASONS.has(reason)) {
    throw new TypeError('Connection drop reconciliation reason is invalid');
  }
  if ((outcome === 'accepted') !== isAppliedReason(reason)) {
    throw new TypeError('Connection drop reconciliation reason does not match the outcome');
  }
  if (!RECONCILIATION_REFERENCE_PATTERN.test(reference)) {
    throw new TypeError('Connection drop reconciliation reference is invalid');
  }
  return { outcome, reason, reference };
}

export const adminRemnawaveConnectionsApi = {
  async requestUserConnections(userId: number): Promise<RemnawaveConnectionReadRequest> {
    const response = await apiClient.post<unknown>(
      `/admin/remnawave/connections/users/${positiveUserId(userId)}/requests`,
    );
    return parseRequest(response.data);
  },

  async getUserConnections(
    userId: number,
    requestId: string,
  ): Promise<AdminRemnawaveUserConnectionsStatus> {
    const response = await apiClient.get<unknown>(
      `/admin/remnawave/connections/users/${positiveUserId(userId)}/requests/${canonicalRequestId(requestId)}`,
    );
    return parseUserStatus(response.data);
  },

  async requestNodeConnections(nodeUuid: string): Promise<RemnawaveConnectionReadRequest> {
    const response = await apiClient.post<unknown>(
      `/admin/remnawave/connections/nodes/${encodeURIComponent(canonicalUuid(nodeUuid))}/requests`,
    );
    return parseRequest(response.data);
  },

  async getNodeConnections(
    nodeUuid: string,
    requestId: string,
  ): Promise<AdminRemnawaveNodeConnectionsStatus> {
    const response = await apiClient.get<unknown>(
      `/admin/remnawave/connections/nodes/${encodeURIComponent(canonicalUuid(nodeUuid))}/requests/${canonicalRequestId(requestId)}`,
    );
    return parseNodeStatus(response.data);
  },

  async dropConnections(
    body: AdminRemnawaveConnectionDropRequest,
    idempotencyKey: string,
  ): Promise<RemnawaveConnectionDropReceipt> {
    if (!IDEMPOTENCY_KEY_PATTERN.test(idempotencyKey)) {
      throw new TypeError('Connection drop idempotency key is invalid');
    }
    const response = await apiClient.post<unknown>(
      '/admin/remnawave/connections/drop',
      body,
      { headers: { 'Idempotency-Key': idempotencyKey } },
    );
    return parseDropReceipt(response.data);
  },

  async listUnresolvedDropReceipts({
    limit = 50,
    cursor = null,
  }: {
    limit?: number;
    cursor?: string | null;
  } = {}): Promise<AdminRemnawaveConnectionDropUnresolvedPage> {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > MAX_UNRESOLVED_RECEIPTS) {
      throw new TypeError('Unresolved receipt page limit is invalid');
    }
    const params: { limit: number; cursor?: string } = { limit };
    if (cursor !== null) params.cursor = canonicalReceiptId(cursor, 'Unresolved receipt cursor');
    const response = await apiClient.get<unknown>(
      '/admin/remnawave/connections/drop-receipts/unresolved',
      { params },
    );
    return parseUnresolvedDropReceipts(response.data);
  },

  async getDropReceipt(receiptId: string): Promise<AdminRemnawaveConnectionDropReceipt> {
    const canonicalId = canonicalReceiptId(receiptId);
    const response = await apiClient.get<unknown>(
      `/admin/remnawave/connections/drop-receipts/${encodeURIComponent(canonicalId)}`,
    );
    return parseAdminDropReceipt(response.data);
  },

  async reconcileDropReceipt(
    receiptId: string,
    body: AdminRemnawaveConnectionDropReconciliationRequest,
  ): Promise<AdminRemnawaveConnectionDropReceipt> {
    const canonicalId = canonicalReceiptId(receiptId);
    const response = await apiClient.post<unknown>(
      `/admin/remnawave/connections/drop-receipts/${encodeURIComponent(canonicalId)}/reconcile`,
      canonicalReconciliationRequest(body),
    );
    return parseAdminDropReceipt(response.data);
  },
};
