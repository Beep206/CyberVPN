import type {
  GetPartnerWorkspacePostbackReadinessResponse,
  PartnerBotResponse,
} from '@/lib/api/partner-portal';
import type { PartnerTechnicalReadiness } from '@/features/partner-portal-state/lib/portal-state';

export type PartnerProvisioningAvailability = 'enabled' | 'conditional' | 'blocked';

const ACTIVE_JOB_STATUSES = new Set([
  'queued',
  'validating_partner',
  'reserving_bot_identity',
  'applying_branding',
  'configuring_commands',
  'configuring_menu_button',
  'binding_webhook',
  'binding_miniapp',
  'generating_launch_assets',
  'publishing',
]);

const INTERVENTION_JOB_STATUSES = new Set([
  'manual_intervention_required',
  'failed_validation',
  'failed_bot_creation',
  'failed_token_fetch',
  'failed_webhook_binding',
  'failed_branding',
  'rollback_required',
]);

const INTERVENTION_BOT_STATUSES = new Set([
  'degraded',
  'failed',
  'revoked',
  'suspended',
]);

export interface PartnerBotProvisioningReadiness {
  managedPathAvailability: PartnerProvisioningAvailability;
  manualFallbackAvailability: PartnerProvisioningAvailability;
  postbackAvailability: PartnerProvisioningAvailability;
  activeBots: number;
  pendingBots: number;
  interventionBots: number;
  suspendedBots: number;
  managedPathBots: number;
  manualPathBots: number;
  readyManagedBindings: number;
  notes: string[];
}

function hasManagedBinding(bot: PartnerBotResponse): boolean {
  return Boolean(bot.managed_by_bot_id || bot.telegram_bot_id || bot.telegram_username);
}

function hasActiveProvisioning(bot: PartnerBotResponse): boolean {
  return (
    bot.status === 'provisioning_requested'
    || bot.status === 'provisioning_running'
    || ACTIVE_JOB_STATUSES.has(bot.latest_provisioning_job?.job_status ?? '')
  );
}

function needsIntervention(bot: PartnerBotResponse): boolean {
  return (
    INTERVENTION_BOT_STATUSES.has(bot.status)
    || INTERVENTION_JOB_STATUSES.has(bot.latest_provisioning_job?.job_status ?? '')
    || Boolean(bot.provisioning_last_error)
  );
}

export function buildPartnerBotProvisioningReadiness({
  bots,
  technicalReadiness,
  postbackReadiness,
}: {
  bots: PartnerBotResponse[];
  technicalReadiness: PartnerTechnicalReadiness;
  postbackReadiness?: GetPartnerWorkspacePostbackReadinessResponse | null;
}): PartnerBotProvisioningReadiness {
  const managedPathBots = bots.filter((bot) => bot.provisioning_path === 'managed_bot');
  const manualPathBots = bots.filter((bot) => bot.provisioning_path === 'manual_token');
  const activeBots = bots.filter((bot) => bot.status === 'active').length;
  const pendingBots = bots.filter((bot) => hasActiveProvisioning(bot)).length;
  const interventionBots = bots.filter((bot) => needsIntervention(bot)).length;
  const suspendedBots = bots.filter((bot) => bot.status === 'suspended').length;
  const readyManagedBindings = managedPathBots.filter(
    (bot) => bot.status === 'active' && hasManagedBinding(bot),
  ).length;
  const postbackStatus = postbackReadiness?.status ?? null;

  let managedPathAvailability: PartnerProvisioningAvailability = 'conditional';
  if (technicalReadiness === 'blocked') {
    managedPathAvailability = 'blocked';
  } else if (readyManagedBindings > 0 && postbackStatus === 'complete') {
    managedPathAvailability = 'enabled';
  }

  let manualFallbackAvailability: PartnerProvisioningAvailability = 'enabled';
  if (technicalReadiness === 'blocked') {
    manualFallbackAvailability = 'blocked';
  }

  let postbackAvailability: PartnerProvisioningAvailability = 'conditional';
  if (technicalReadiness === 'blocked' || postbackStatus === 'blocked') {
    postbackAvailability = 'blocked';
  } else if (postbackStatus === 'complete') {
    postbackAvailability = 'enabled';
  }

  const notes: string[] = [];
  if (managedPathAvailability === 'conditional') {
    notes.push('managed_path_operator_handoff');
  }
  if (manualFallbackAvailability === 'enabled') {
    notes.push('manual_path_available');
  }
  if (interventionBots > 0) {
    notes.push('operator_attention_required');
  }
  if (postbackStatus === 'in_progress') {
    notes.push('postback_under_review');
  }
  if (postbackStatus === 'blocked') {
    notes.push('postback_blocked');
  }

  return {
    managedPathAvailability,
    manualFallbackAvailability,
    postbackAvailability,
    activeBots,
    pendingBots,
    interventionBots,
    suspendedBots,
    managedPathBots: managedPathBots.length,
    manualPathBots: manualPathBots.length,
    readyManagedBindings,
    notes,
  };
}
