import { describe, expect, it } from 'vitest';
import { buildPartnerBotProvisioningReadiness } from './partner-bot-readiness';
import type {
  GetPartnerWorkspacePostbackReadinessResponse,
  PartnerBotResponse,
} from '@/lib/api/partner-portal';

function createBot(overrides: Partial<PartnerBotResponse> = {}): PartnerBotResponse {
  return {
    id: 'bot_001',
    partner_account_id: 'workspace_001',
    bot_key: 'alpha-bot',
    display_name: 'Alpha Bot',
    default_locale: 'en-EN',
    provisioning_path: 'managed_bot',
    token_status: 'missing',
    status: 'draft',
    release_channel: 'stable',
    created_at: '2026-04-22T10:00:00Z',
    updated_at: '2026-04-22T10:00:00Z',
    ...overrides,
  };
}

function createPostbackReadiness(
  overrides: Partial<GetPartnerWorkspacePostbackReadinessResponse> = {},
): GetPartnerWorkspacePostbackReadinessResponse {
  return {
    status: 'complete',
    delivery_status: 'delivered',
    scope_label: 'Tracking and postback handoff',
    credential_id: 'cred_001',
    credential_status: 'ready',
    notes: ['Workspace-scoped postback is ready.'],
    ...overrides,
  };
}

describe('buildPartnerBotProvisioningReadiness', () => {
  it('marks managed path as enabled only when a live managed binding and complete postback readiness exist', () => {
    const readiness = buildPartnerBotProvisioningReadiness({
      bots: [
        createBot({
          status: 'active',
          managed_by_bot_id: 'manager_001',
          telegram_bot_id: '777000',
        }),
      ],
      technicalReadiness: 'ready',
      postbackReadiness: createPostbackReadiness(),
    });

    expect(readiness.managedPathAvailability).toBe('enabled');
    expect(readiness.manualFallbackAvailability).toBe('enabled');
    expect(readiness.postbackAvailability).toBe('enabled');
    expect(readiness.readyManagedBindings).toBe(1);
    expect(readiness.activeBots).toBe(1);
  });

  it('keeps managed path conditional and flags intervention when failures still require operator follow-up', () => {
    const readiness = buildPartnerBotProvisioningReadiness({
      bots: [
        createBot({
          id: 'bot_001',
          provisioning_path: 'managed_bot',
          status: 'failed',
          provisioning_last_error: 'Webhook binding failed',
          latest_provisioning_job: {
            id: 'job_001',
            partner_bot_id: 'bot_001',
            partner_account_id: 'workspace_001',
            provisioning_path: 'managed_bot',
            job_status: 'manual_intervention_required',
            attempt_count: 1,
            queued_at: '2026-04-22T10:00:00Z',
            created_at: '2026-04-22T10:00:00Z',
            updated_at: '2026-04-22T10:10:00Z',
          },
        }),
        createBot({
          id: 'bot_002',
          bot_key: 'beta-bot',
          display_name: 'Beta Bot',
          provisioning_path: 'manual_token',
          status: 'provisioning_requested',
        }),
      ],
      technicalReadiness: 'in_progress',
      postbackReadiness: createPostbackReadiness({
        status: 'in_progress',
        delivery_status: 'paused',
      }),
    });

    expect(readiness.managedPathAvailability).toBe('conditional');
    expect(readiness.manualFallbackAvailability).toBe('enabled');
    expect(readiness.postbackAvailability).toBe('conditional');
    expect(readiness.pendingBots).toBe(1);
    expect(readiness.interventionBots).toBe(1);
    expect(readiness.notes).toContain('managed_path_operator_handoff');
    expect(readiness.notes).toContain('operator_attention_required');
    expect(readiness.notes).toContain('postback_under_review');
  });

  it('blocks launch-sensitive paths when technical readiness is blocked', () => {
    const readiness = buildPartnerBotProvisioningReadiness({
      bots: [
        createBot({
          provisioning_path: 'manual_token',
          status: 'suspended',
        }),
      ],
      technicalReadiness: 'blocked',
      postbackReadiness: createPostbackReadiness({
        status: 'blocked',
        delivery_status: 'failed',
      }),
    });

    expect(readiness.managedPathAvailability).toBe('blocked');
    expect(readiness.manualFallbackAvailability).toBe('blocked');
    expect(readiness.postbackAvailability).toBe('blocked');
    expect(readiness.suspendedBots).toBe(1);
    expect(readiness.notes).toContain('postback_blocked');
  });
});
