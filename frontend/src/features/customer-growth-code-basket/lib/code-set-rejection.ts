export type CheckoutCodeApplicationStatus =
  | 'accepted'
  | 'applied'
  | 'not_selected'
  | 'rejected'
  | 'ambiguous'
  | 'wrong_context'
  | 'unknown';

export type CheckoutCodeSetRejectionApplication = {
  position_entered?: number | null;
  canonical_order?: number | null;
  client_slot_id?: string | null;
  masked_code?: string | null;
  status?: string | null;
  reject_reason?: string | null;
  conflict_code?: string | null;
  wrong_context_target?: string | null;
  user_message_key?: string | null;
  roles?: string[];
};

export type CheckoutCodeSetRejection = {
  code: 'CODE_SET_REJECTED';
  messageKey?: string | null;
  applications: CheckoutCodeSetRejectionApplication[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readString(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
}

function readNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function readStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function normalizeApplication(record: Record<string, unknown>): CheckoutCodeSetRejectionApplication {
  return {
    position_entered: readNumber(record.position_entered),
    canonical_order: readNumber(record.canonical_order),
    client_slot_id: readString(record.client_slot_id),
    masked_code: readString(record.masked_code),
    status: readString(record.status),
    reject_reason: readString(record.reject_reason),
    conflict_code: readString(record.conflict_code),
    wrong_context_target: readString(record.wrong_context_target),
    user_message_key: readString(record.user_message_key),
    roles: readStringList(record.roles),
  };
}

function getStructuredDetail(error: unknown): Record<string, unknown> | null {
  if (!isRecord(error)) {
    return null;
  }

  const response = isRecord(error.response) ? error.response : null;
  const data = response && isRecord(response.data) ? response.data : null;
  const detail = data && isRecord(data.detail) ? data.detail : data;

  return detail;
}

export function normalizeCheckoutCodeApplicationStatus(
  value: unknown,
): CheckoutCodeApplicationStatus {
  const normalized = typeof value === 'string'
    ? value.trim().toLowerCase().replace(/[\s-]+/g, '_')
    : '';

  if (normalized === 'accepted' || normalized === 'selected') {
    return 'accepted';
  }
  if (normalized === 'applied') {
    return 'applied';
  }
  if (normalized === 'not_selected' || normalized === 'not_selected_by_policy') {
    return 'not_selected';
  }
  if (normalized === 'ambiguous' || normalized === 'namespace_ambiguous') {
    return 'ambiguous';
  }
  if (normalized === 'wrong_context') {
    return 'wrong_context';
  }
  if (normalized === 'rejected' || normalized === 'expired' || normalized === 'blocked') {
    return 'rejected';
  }

  return 'unknown';
}

export function isCheckoutCodeSetAcceptedStatus(
  status: CheckoutCodeApplicationStatus | undefined,
): boolean {
  return status === 'accepted' || status === 'applied' || status === 'not_selected';
}

export function isCheckoutCodeSetBlockingStatus(
  status: CheckoutCodeApplicationStatus | undefined,
): boolean {
  return (
    status === 'rejected'
    || status === 'ambiguous'
    || status === 'wrong_context'
    || status === 'unknown'
  );
}

export function extractCheckoutCodeSetRejection(error: unknown): CheckoutCodeSetRejection | null {
  const detail = getStructuredDetail(error);
  if (!detail || detail.code !== 'CODE_SET_REJECTED' || !Array.isArray(detail.applications)) {
    return null;
  }

  const applications = detail.applications
    .filter(isRecord)
    .map(normalizeApplication);

  if (applications.length === 0) {
    return null;
  }

  return {
    code: 'CODE_SET_REJECTED',
    messageKey: readString(detail.message_key),
    applications,
  };
}
