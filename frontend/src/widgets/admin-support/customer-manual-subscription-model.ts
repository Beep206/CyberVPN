export const STAGE1_MANUAL_SUBSCRIPTION_AUDIT_ACTION =
  'customer_subscription_manual_granted';

export type Stage1ManualSubscriptionRole =
  | 'admin'
  | 'finance'
  | 'operator'
  | 'owner'
  | 'owner/super_admin'
  | 'owner_super_admin'
  | 'super_admin'
  | 'support'
  | 'viewer';

export type ManualSubscriptionRequestPayload = {
  device_limit: number;
  duration_days: number;
  reason: string;
  traffic_limit_bytes?: number | null;
};

export type ManualSubscriptionResult = {
  audit_action: string;
  config_delivery_required: boolean;
  created: boolean;
  duration_days: number;
  expires_at: string;
  operation: 'grant' | 'extend';
  previous_expires_at: string | null;
  remnawave_uuid: string;
  status: string;
  subscription_url_changed: boolean;
  user_id: string;
};

export type ManualSubscriptionRequestValidation =
  | {
      ok: true;
      payload: ManualSubscriptionRequestPayload;
    }
  | {
      error: string;
      ok: false;
    };

export type SafeManualSubscriptionSummary = {
  auditAction: string;
  configDeliveryRequired: boolean;
  created: boolean;
  durationDays: number;
  expiresAt: string;
  operation: 'grant' | 'extend';
  previousExpiresAt: string | null;
  status: string;
  subscriptionUrlChanged: boolean;
  userId: string;
  vpnIdentity: string;
};

const ALLOWED_MANUAL_SUBSCRIPTION_ROLES = new Set<Stage1ManualSubscriptionRole>([
  'admin',
  'operator',
  'owner',
  'owner/super_admin',
  'owner_super_admin',
  'super_admin',
]);

export function canApplyManualSubscription(
  role: Stage1ManualSubscriptionRole,
): boolean {
  return ALLOWED_MANUAL_SUBSCRIPTION_ROLES.has(role);
}

export function buildManualSubscriptionEndpoint(userId: string): string {
  return `/admin/mobile-users/${encodeURIComponent(userId)}/subscription/manual-grant`;
}

export function buildManualSubscriptionRequest({
  deviceLimit,
  durationDays,
  reason,
  trafficLimitBytes,
}: {
  deviceLimit: number;
  durationDays: number;
  reason: string;
  trafficLimitBytes?: number | null;
}): ManualSubscriptionRequestValidation {
  const trimmedReason = reason.trim();

  if (trimmedReason.length < 3) {
    return {
      error: 'Manual subscription operation requires an operator reason.',
      ok: false,
    };
  }

  if (trimmedReason.length > 1000) {
    return {
      error: 'Manual subscription operation reason is too long.',
      ok: false,
    };
  }

  if (!Number.isInteger(durationDays) || durationDays < 1 || durationDays > 365) {
    return {
      error: 'Manual subscription duration must be between 1 and 365 days.',
      ok: false,
    };
  }

  if (!Number.isInteger(deviceLimit) || deviceLimit < 1 || deviceLimit > 10) {
    return {
      error: 'Manual subscription device limit must be between 1 and 10.',
      ok: false,
    };
  }

  if (
    trafficLimitBytes !== undefined &&
    trafficLimitBytes !== null &&
    (!Number.isInteger(trafficLimitBytes) || trafficLimitBytes <= 0)
  ) {
    return {
      error: 'Manual subscription traffic limit must be positive or empty.',
      ok: false,
    };
  }

  return {
    ok: true,
    payload: {
      device_limit: deviceLimit,
      duration_days: durationDays,
      reason: trimmedReason,
      traffic_limit_bytes: trafficLimitBytes ?? null,
    },
  };
}

export function summarizeManualSubscriptionResult(
  result: ManualSubscriptionResult,
): SafeManualSubscriptionSummary {
  return {
    auditAction: result.audit_action,
    configDeliveryRequired: result.config_delivery_required,
    created: result.created,
    durationDays: result.duration_days,
    expiresAt: result.expires_at,
    operation: result.operation,
    previousExpiresAt: result.previous_expires_at,
    status: result.status,
    subscriptionUrlChanged: result.subscription_url_changed,
    userId: result.user_id,
    vpnIdentity: result.remnawave_uuid,
  };
}
