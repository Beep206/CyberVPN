import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  mockGet,
  mockPost,
  mockPut,
} = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPut: vi.fn(),
}));

vi.mock('../client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    put: (...args: unknown[]) => mockPut(...args),
  },
}));

import { governanceApi } from '../governance';

describe('governanceApi mini app runtime operations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads the dedicated mini app runtime system config', async () => {
    mockGet.mockResolvedValue({
      status: 200,
      data: {
        key: 'miniapp.runtime',
        rollout: {
          enabled: true,
          mode: 'canary',
          trial_enabled: true,
          checkout_enabled: false,
          config_enabled: true,
          maintenance_message: 'Checkout temporarily paused',
          canary_telegram_user_ids: [123456789],
        },
        description: 'Operator-controlled rollout policy',
        updated_at: '2026-04-22T10:15:00Z',
        updated_by: 'admin_001',
      },
    });

    const response = await governanceApi.getMiniAppRuntimeConfig();

    expect(mockGet).toHaveBeenCalledWith('/admin/system-config/miniapp-runtime');
    expect(response.status).toBe(200);
    expect(response.data.rollout.checkout_enabled).toBe(false);
  });

  it('updates the dedicated mini app runtime system config', async () => {
    mockPut.mockResolvedValue({
      status: 200,
      data: {
        key: 'miniapp.runtime',
        rollout: {
          enabled: false,
          mode: 'rollback',
          trial_enabled: false,
          checkout_enabled: false,
          config_enabled: true,
          maintenance_message: 'Maintenance window',
          canary_telegram_user_ids: [123456789, 987654321],
        },
        description: 'Operator-controlled rollout policy',
        updated_at: '2026-04-22T10:20:00Z',
        updated_by: 'admin_002',
      },
    });

    const response = await governanceApi.updateMiniAppRuntimeConfig({
      enabled: false,
      mode: 'rollback',
      trial_enabled: false,
      checkout_enabled: false,
      config_enabled: true,
      maintenance_message: 'Maintenance window',
      canary_telegram_user_ids: [123456789, 987654321],
      change_reason: 'canary rollback',
    });

    expect(mockPut).toHaveBeenCalledWith('/admin/system-config/miniapp-runtime', {
      enabled: false,
      mode: 'rollback',
      trial_enabled: false,
      checkout_enabled: false,
      config_enabled: true,
      maintenance_message: 'Maintenance window',
      canary_telegram_user_ids: [123456789, 987654321],
      change_reason: 'canary rollback',
    });
    expect(response.status).toBe(200);
    expect(response.data.rollout.enabled).toBe(false);
  });

  it('loads mini app launch readiness system config', async () => {
    mockGet.mockResolvedValue({
      status: 200,
      data: {
        key: 'miniapp.launch_readiness',
        readiness: {
          observability_acknowledged: true,
          incident_runbook_acknowledged: true,
          checkout_canary_passed: false,
          config_delivery_canary_passed: false,
          rollback_drill_acknowledged: false,
          support_window_confirmed: false,
          customer_comms_ready: false,
          status_page_template_ready: false,
          incident_channel: '#miniapp-war-room',
          rollback_commander: '@ops-lead',
          primary_oncall_contact: '@backend-oncall',
          release_window_note: 'Friday 18:00 UTC',
          is_ready: false,
        },
        description: 'Launch gates',
        updated_at: '2026-04-22T10:30:00Z',
        updated_by: 'admin_003',
      },
    });

    const response = await governanceApi.getMiniAppLaunchReadinessConfig();

    expect(mockGet).toHaveBeenCalledWith('/admin/system-config/miniapp-launch-readiness');
    expect(response.status).toBe(200);
    expect(response.data.readiness.observability_acknowledged).toBe(true);
    expect(response.data.readiness.incident_channel).toBe('#miniapp-war-room');
  });

  it('updates mini app launch readiness system config', async () => {
    mockPut.mockResolvedValue({
      status: 200,
      data: {
        key: 'miniapp.launch_readiness',
        readiness: {
          observability_acknowledged: true,
          incident_runbook_acknowledged: true,
          checkout_canary_passed: true,
          config_delivery_canary_passed: true,
          rollback_drill_acknowledged: true,
          support_window_confirmed: true,
          customer_comms_ready: true,
          status_page_template_ready: true,
          incident_channel: '#miniapp-war-room',
          rollback_commander: '@ops-lead',
          primary_oncall_contact: '@backend-oncall',
          release_window_note: 'Friday 18:00 UTC',
          is_ready: true,
        },
        description: 'Launch gates',
        updated_at: '2026-04-22T10:31:00Z',
        updated_by: 'admin_003',
      },
    });

    const response = await governanceApi.updateMiniAppLaunchReadinessConfig({
      observability_acknowledged: true,
      incident_runbook_acknowledged: true,
      checkout_canary_passed: true,
      config_delivery_canary_passed: true,
      rollback_drill_acknowledged: true,
      support_window_confirmed: true,
      customer_comms_ready: true,
      status_page_template_ready: true,
      incident_channel: '#miniapp-war-room',
      rollback_commander: '@ops-lead',
      primary_oncall_contact: '@backend-oncall',
      release_window_note: 'Friday 18:00 UTC',
      change_reason: 'all gates green after canary',
    });

    expect(mockPut).toHaveBeenCalledWith('/admin/system-config/miniapp-launch-readiness', {
      observability_acknowledged: true,
      incident_runbook_acknowledged: true,
      checkout_canary_passed: true,
      config_delivery_canary_passed: true,
      rollback_drill_acknowledged: true,
      support_window_confirmed: true,
      customer_comms_ready: true,
      status_page_template_ready: true,
      incident_channel: '#miniapp-war-room',
      rollback_commander: '@ops-lead',
      primary_oncall_contact: '@backend-oncall',
      release_window_note: 'Friday 18:00 UTC',
      change_reason: 'all gates green after canary',
    });
    expect(response.status).toBe(200);
    expect(response.data.readiness.is_ready).toBe(true);
  });

  it('loads mini app launch summary', async () => {
    mockGet.mockResolvedValue({
      status: 200,
      data: {
        launch_state: 'canary_in_progress',
        live_switch_allowed: false,
        next_action: 'complete_launch_gates',
        blockers: ['incident_channel_missing'],
        runtime: {
          enabled: true,
          mode: 'canary',
          trial_enabled: true,
          checkout_enabled: true,
          config_enabled: true,
          maintenance_message: null,
          canary_telegram_user_ids: [123456789],
        },
        readiness: {
          observability_acknowledged: true,
          incident_runbook_acknowledged: true,
          checkout_canary_passed: true,
          config_delivery_canary_passed: true,
          rollback_drill_acknowledged: true,
          support_window_confirmed: true,
          customer_comms_ready: true,
          status_page_template_ready: true,
          incident_channel: null,
          rollback_commander: '@ops-lead',
          primary_oncall_contact: '@backend-oncall',
          release_window_note: 'Friday 18:00 UTC',
          is_ready: false,
        },
      },
    });

    const response = await governanceApi.getMiniAppLaunchSummary();

    expect(mockGet).toHaveBeenCalledWith('/admin/system-config/miniapp-launch-summary');
    expect(response.status).toBe(200);
    expect(response.data.launch_state).toBe('canary_in_progress');
    expect(response.data.blockers).toContain('incident_channel_missing');
  });

  it('executes server-authoritative mini app launch actions', async () => {
    mockPost.mockResolvedValue({
      status: 200,
      data: {
        launch_state: 'live',
        live_switch_allowed: true,
        next_action: 'keep_canary',
        primary_action: null,
        available_actions: ['start_rollback', 'enter_maintenance', 'return_to_canary'],
        blockers: [],
        runtime: {
          enabled: true,
          mode: 'live',
          trial_enabled: true,
          checkout_enabled: true,
          config_enabled: true,
          maintenance_message: null,
          canary_telegram_user_ids: [123456789],
        },
        readiness: {
          observability_acknowledged: true,
          incident_runbook_acknowledged: true,
          checkout_canary_passed: true,
          config_delivery_canary_passed: true,
          rollback_drill_acknowledged: true,
          support_window_confirmed: true,
          customer_comms_ready: true,
          status_page_template_ready: true,
          incident_channel: '#miniapp-war-room',
          rollback_commander: '@ops-lead',
          primary_oncall_contact: '@backend-oncall',
          release_window_note: 'Friday 18:00 UTC',
          is_ready: true,
        },
      },
    });

    const response = await governanceApi.executeMiniAppLaunchAction({
      action: 'promote_to_live',
      change_reason: 'canary metrics stable',
    });

    expect(mockPost).toHaveBeenCalledWith('/admin/system-config/miniapp-launch-actions', {
      action: 'promote_to_live',
      change_reason: 'canary metrics stable',
    });
    expect(response.status).toBe(200);
    expect(response.data.launch_state).toBe('live');
  });

  it('loads mini app launch timeline entries', async () => {
    mockGet.mockResolvedValue({
      status: 200,
      data: [
        {
          id: 'timeline_001',
          created_at: '2026-04-22T12:00:00Z',
          admin_id: 'admin_007',
          action: 'system_config.miniapp_launch_action.executed',
          event_type: 'launch_action',
          action_name: 'start_rollback',
          resulting_runtime_mode: 'rollback',
          resulting_launch_state: 'rollback_in_progress',
          readiness_ready: null,
          change_reason: 'checkout regression in canary',
          entity_id: 'miniapp.runtime',
        },
      ],
    });

    const response = await governanceApi.getMiniAppLaunchTimeline({ limit: 5 });

    expect(mockGet).toHaveBeenCalledWith('/admin/system-config/miniapp-launch-timeline', {
      params: { limit: 5 },
    });
    expect(response.status).toBe(200);
    expect(response.data[0]?.event_type).toBe('launch_action');
    expect(response.data[0]?.action_name).toBe('start_rollback');
  });
});
