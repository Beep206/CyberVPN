import type { GetPartnerSessionBootstrapResponse } from '@/lib/api/partner-portal';
import type {
  PartnerComplianceReadiness,
  PartnerComplianceTask,
  PartnerComplianceTaskKind,
  PartnerComplianceTaskStatus,
  PartnerGovernanceState,
  PartnerReviewRequest,
  PartnerWorkspaceRole,
} from '@/features/partner-portal-state/lib/portal-state';
import type { PartnerPrimaryLane } from '@/features/partner-onboarding/lib/application-draft-storage';
import type { PartnerPortalTrafficDeclaration } from '@/features/partner-portal-state/lib/runtime-state';

type PartnerBlockedReason =
  NonNullable<GetPartnerSessionBootstrapResponse['blocked_reasons']>[number];

const TASK_STATUS_PRIORITY: Record<PartnerComplianceTaskStatus, number> = {
  blocked: 0,
  action_required: 1,
  under_review: 2,
  complete: 3,
};

function mergeNotes(current: string[], incoming: string[]): string[] {
  return Array.from(new Set([...current, ...incoming].filter(Boolean)));
}

function normalizeTaskStatus(
  value: string,
): PartnerComplianceTaskStatus {
  if (value === 'complete' || value === 'approved') {
    return 'complete';
  }
  if (value === 'blocked' || value === 'rejected') {
    return 'blocked';
  }
  if (value === 'action_required' || value === 'needs_info' || value === 'open') {
    return 'action_required';
  }
  return 'under_review';
}

function resolveDeclarationTaskKind(
  kind: string,
): PartnerComplianceTaskKind | null {
  if (kind === 'approved_sources') {
    return 'approved_sources';
  }
  if (kind === 'postback_readiness') {
    return 'postback_readiness';
  }
  if (kind.includes('creative')) {
    return 'creative_approval';
  }
  if (kind === 'support_ownership') {
    return 'support_ownership';
  }
  return null;
}

function resolveReviewRequestTaskKind(
  kind: PartnerReviewRequest['kind'],
): PartnerComplianceTaskKind | null {
  if (kind === 'traffic_methods') {
    return 'approved_sources';
  }
  if (kind === 'support_ownership') {
    return 'support_ownership';
  }
  if (kind === 'business_profile' || kind === 'owned_channels') {
    return 'evidence_upload';
  }
  return null;
}

function resolveTaskOwnerRole(
  kind: PartnerComplianceTaskKind,
): PartnerWorkspaceRole {
  if (kind === 'approved_sources' || kind === 'creative_approval' || kind === 'postback_readiness') {
    return 'traffic_manager';
  }
  if (kind === 'support_ownership') {
    return 'support_manager';
  }
  return 'workspace_owner';
}

function upsertTask(
  tasks: Map<PartnerComplianceTaskKind, PartnerComplianceTask>,
  task: {
    kind: PartnerComplianceTaskKind;
    status: PartnerComplianceTaskStatus;
    notes: string[];
    id: string;
  },
): void {
  const { kind, status, notes, id } = task;
  const existing = tasks.get(kind);
  if (!existing) {
    tasks.set(kind, {
      id,
      kind,
      status,
      ownerRole: resolveTaskOwnerRole(kind),
      notes: [...notes],
    });
    return;
  }

  const shouldReplaceStatus =
    TASK_STATUS_PRIORITY[status] < TASK_STATUS_PRIORITY[existing.status];

  tasks.set(kind, {
    ...existing,
    status: shouldReplaceStatus ? status : existing.status,
    notes: mergeNotes(existing.notes, notes),
  });
}

function sortTasks(tasks: PartnerComplianceTask[]): PartnerComplianceTask[] {
  return [...tasks].sort((left, right) => {
    const priorityDiff =
      TASK_STATUS_PRIORITY[left.status] - TASK_STATUS_PRIORITY[right.status];
    if (priorityDiff !== 0) {
      return priorityDiff;
    }
    return left.kind.localeCompare(right.kind);
  });
}

function getRestrictionNotes(
  blockedReason: PartnerBlockedReason,
  fallback: string,
): string[] {
  return (blockedReason.notes?.length ?? 0) > 0
    ? blockedReason.notes ?? []
    : [fallback];
}

export function getComplianceRestrictionReasons(
  blockedReasons: PartnerBlockedReason[] | null | undefined,
): PartnerBlockedReason[] {
  if (!blockedReasons) {
    return [];
  }

  return blockedReasons.filter((item) => (
    item.route_slug === 'compliance'
    || item.route_slug === 'programs'
    || item.route_slug === 'dashboard'
  ));
}

export function getCasesRestrictionReasons(
  blockedReasons: PartnerBlockedReason[] | null | undefined,
): PartnerBlockedReason[] {
  if (!blockedReasons) {
    return [];
  }

  return blockedReasons.filter((item) => (
    item.route_slug === 'dashboard'
    || item.route_slug === 'finance'
    || item.route_slug === 'compliance'
    || item.route_slug === 'programs'
    || item.route_slug === 'integrations'
  ));
}

export function deriveCanonicalComplianceTasks({
  complianceReadiness,
  governanceState,
  primaryLane,
  reviewRequests,
  trafficDeclarations,
  blockedReasons,
}: {
  complianceReadiness: PartnerComplianceReadiness;
  governanceState: PartnerGovernanceState;
  primaryLane: PartnerPrimaryLane | '';
  reviewRequests: PartnerReviewRequest[];
  trafficDeclarations: PartnerPortalTrafficDeclaration[];
  blockedReasons: PartnerBlockedReason[] | null | undefined;
}): PartnerComplianceTask[] {
  const tasks = new Map<PartnerComplianceTaskKind, PartnerComplianceTask>();

  for (const item of trafficDeclarations) {
    const kind = resolveDeclarationTaskKind(item.kind);
    if (!kind) {
      continue;
    }
    upsertTask(tasks, {
      id: `traffic:${kind}`,
      kind,
      status: normalizeTaskStatus(item.status),
      notes: item.notes,
    });
  }

  for (const request of reviewRequests) {
    const kind = resolveReviewRequestTaskKind(request.kind);
    if (!kind) {
      continue;
    }
    upsertTask(tasks, {
      id: `review:${kind}`,
      kind,
      status: request.status === 'open' ? 'action_required' : 'under_review',
      notes: [
        `Review request: ${request.kind}.`,
        ...(request.threadEvents?.map((event) => event.message) ?? []),
      ],
    });
  }

  for (const reason of getComplianceRestrictionReasons(blockedReasons)) {
    if (reason.code === 'compliance_evidence_requested') {
      upsertTask(tasks, {
        id: 'blocked:evidence_upload',
        kind: 'evidence_upload',
        status: 'action_required',
        notes: getRestrictionNotes(
          reason,
          'Additional evidence is required before compliance posture can advance.',
        ),
      });
      continue;
    }

    if (reason.code === 'compliance_blocked') {
      upsertTask(tasks, {
        id: 'blocked:disclosure_attestation',
        kind: 'disclosure_attestation',
        status: 'blocked',
        notes: getRestrictionNotes(
          reason,
          'Compliance-driven actions remain blocked until declarations and evidence are restored.',
        ),
      });
      continue;
    }

    if (reason.code.startsWith('governance_state:')) {
      upsertTask(tasks, {
        id: 'blocked:governance',
        kind: 'disclosure_attestation',
        status: reason.code.endsWith('frozen') ? 'blocked' : 'action_required',
        notes: getRestrictionNotes(
          reason,
          'Governance posture is reducing the current workspace launch surface.',
        ),
      });
    }
  }

  if (complianceReadiness === 'evidence_requested') {
    upsertTask(tasks, {
      id: 'readiness:evidence_upload',
      kind: 'evidence_upload',
      status: 'action_required',
      notes: [
        'Compliance readiness still expects more evidence before the workspace can progress.',
      ],
    });
  }

  if (complianceReadiness === 'blocked') {
    upsertTask(tasks, {
      id: 'readiness:disclosure_attestation',
      kind: 'disclosure_attestation',
      status: 'blocked',
      notes: [
        'Compliance readiness is blocked, so disclosures and supporting evidence remain unresolved.',
      ],
    });
  }

  if (
    (primaryLane === 'performance_media' || primaryLane === 'reseller_api')
    && !tasks.has('postback_readiness')
    && (governanceState === 'watch' || governanceState === 'warning')
  ) {
    upsertTask(tasks, {
      id: 'lane:postback_readiness',
      kind: 'postback_readiness',
      status: 'under_review',
      notes: [
        'Postback and click-tracking posture stays review-bound until the lane is explicitly cleared.',
      ],
    });
  }

  return sortTasks(Array.from(tasks.values()));
}
