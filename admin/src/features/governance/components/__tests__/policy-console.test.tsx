import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PolicyConsole } from '../policy-console';

const {
  mockGetSettings,
  mockCreateSetting,
  mockUpdateSetting,
  mockGetMiniAppRuntimeConfig,
  mockUpdateMiniAppRuntimeConfig,
  mockGetMiniAppLaunchReadinessConfig,
  mockUpdateMiniAppLaunchReadinessConfig,
  mockGetMiniAppLaunchSummary,
  mockExecuteMiniAppLaunchAction,
  mockGetMiniAppLaunchTimeline,
} = vi.hoisted(() => ({
  mockGetSettings: vi.fn(),
  mockCreateSetting: vi.fn(),
  mockUpdateSetting: vi.fn(),
  mockGetMiniAppRuntimeConfig: vi.fn(),
  mockUpdateMiniAppRuntimeConfig: vi.fn(),
  mockGetMiniAppLaunchReadinessConfig: vi.fn(),
  mockUpdateMiniAppLaunchReadinessConfig: vi.fn(),
  mockGetMiniAppLaunchSummary: vi.fn(),
  mockExecuteMiniAppLaunchAction: vi.fn(),
  mockGetMiniAppLaunchTimeline: vi.fn(),
}));

vi.mock('@/lib/api/governance', () => ({
  governanceApi: {
    getSettings: (...args: unknown[]) => mockGetSettings(...args),
    createSetting: (...args: unknown[]) => mockCreateSetting(...args),
    updateSetting: (...args: unknown[]) => mockUpdateSetting(...args),
    getMiniAppRuntimeConfig: (...args: unknown[]) => mockGetMiniAppRuntimeConfig(...args),
    updateMiniAppRuntimeConfig: (...args: unknown[]) => mockUpdateMiniAppRuntimeConfig(...args),
    getMiniAppLaunchReadinessConfig: (...args: unknown[]) => mockGetMiniAppLaunchReadinessConfig(...args),
    updateMiniAppLaunchReadinessConfig: (...args: unknown[]) => mockUpdateMiniAppLaunchReadinessConfig(...args),
    getMiniAppLaunchSummary: (...args: unknown[]) => mockGetMiniAppLaunchSummary(...args),
    executeMiniAppLaunchAction: (...args: unknown[]) => mockExecuteMiniAppLaunchAction(...args),
    getMiniAppLaunchTimeline: (...args: unknown[]) => mockGetMiniAppLaunchTimeline(...args),
  },
}));

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

describe('PolicyConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetSettings.mockResolvedValue({ data: [] });
    mockCreateSetting.mockResolvedValue({ data: {} });
    mockUpdateSetting.mockResolvedValue({ data: {} });
    mockGetMiniAppRuntimeConfig.mockResolvedValue({
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
        updated_at: '2026-04-22T11:30:00Z',
        updated_by: '62cf4dca-c181-4b12-9ab8-ef1d9da9085b',
      },
    });
    mockUpdateMiniAppRuntimeConfig.mockResolvedValue({
      data: {
        key: 'miniapp.runtime',
        rollout: {
          enabled: true,
          mode: 'rollback',
          trial_enabled: true,
          checkout_enabled: false,
          config_enabled: true,
          maintenance_message: 'Canary rollback in progress',
          canary_telegram_user_ids: [123456789, 987654321],
        },
        description: 'Operator-controlled rollout policy',
        updated_at: '2026-04-22T11:35:00Z',
        updated_by: '62cf4dca-c181-4b12-9ab8-ef1d9da9085b',
      },
    });
    mockGetMiniAppLaunchReadinessConfig.mockResolvedValue({
      data: {
        key: 'miniapp.launch_readiness',
        readiness: {
          observability_acknowledged: true,
          incident_runbook_acknowledged: false,
          checkout_canary_passed: true,
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
        updated_at: '2026-04-22T11:31:00Z',
        updated_by: '62cf4dca-c181-4b12-9ab8-ef1d9da9085b',
      },
    });
    mockUpdateMiniAppLaunchReadinessConfig.mockResolvedValue({
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
        updated_at: '2026-04-22T11:40:00Z',
        updated_by: '62cf4dca-c181-4b12-9ab8-ef1d9da9085b',
      },
    });
    mockGetMiniAppLaunchSummary.mockResolvedValue({
      data: {
        launch_state: 'canary_in_progress',
        live_switch_allowed: false,
        next_action: 'complete_launch_gates',
        primary_action: null,
        available_actions: ['enter_maintenance', 'start_rollback'],
        blockers: ['incident_channel_missing', 'primary_oncall_contact_missing'],
        runtime: {
          enabled: true,
          mode: 'canary',
          trial_enabled: true,
          checkout_enabled: false,
          config_enabled: true,
          maintenance_message: 'Checkout temporarily paused',
          canary_telegram_user_ids: [123456789],
        },
        readiness: {
          observability_acknowledged: true,
          incident_runbook_acknowledged: false,
          checkout_canary_passed: true,
          config_delivery_canary_passed: false,
          rollback_drill_acknowledged: false,
          support_window_confirmed: false,
          customer_comms_ready: false,
          status_page_template_ready: false,
          incident_channel: null,
          rollback_commander: '@ops-lead',
          primary_oncall_contact: null,
          release_window_note: 'Friday 18:00 UTC',
          is_ready: false,
        },
      },
    });
    mockExecuteMiniAppLaunchAction.mockResolvedValue({
      data: {
        launch_state: 'rollback_in_progress',
        live_switch_allowed: false,
        next_action: 'finish_rollback',
        primary_action: 'return_to_canary',
        available_actions: ['return_to_canary', 'enter_maintenance'],
        blockers: ['rollback_mode_active'],
        runtime: {
          enabled: true,
          mode: 'rollback',
          trial_enabled: true,
          checkout_enabled: false,
          config_enabled: true,
          maintenance_message: 'Checkout temporarily paused',
          canary_telegram_user_ids: [123456789],
        },
        readiness: {
          observability_acknowledged: true,
          incident_runbook_acknowledged: false,
          checkout_canary_passed: true,
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
      },
    });
    mockGetMiniAppLaunchTimeline.mockResolvedValue({
      data: [
        {
          id: 'timeline_001',
          created_at: '2026-04-22T12:00:00Z',
          admin_id: '62cf4dca-c181-4b12-9ab8-ef1d9da9085b',
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
  });

  it('submits the dedicated mini app runtime governance mutation', async () => {
    renderWithQueryClient(<PolicyConsole />);

    const maintenanceInput = screen.getByPlaceholderText(
      'policy.runtimeControl.maintenancePlaceholder',
    );
    const reasonInput = screen.getByPlaceholderText(
      'policy.runtimeControl.changeReasonPlaceholder',
    );

    await waitFor(() => {
      expect(maintenanceInput).toHaveValue('Checkout temporarily paused');
    });

    fireEvent.change(maintenanceInput, {
      target: { value: 'Canary rollback in progress' },
    });
    fireEvent.change(reasonInput, {
      target: { value: 'stabilize payment status errors' },
    });
    fireEvent.change(screen.getByDisplayValue('policy.runtimeControl.status.canary'), {
      target: { value: 'rollback' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'policy.runtimeControl.apply' }));

    await waitFor(() => {
      expect(mockUpdateMiniAppRuntimeConfig).toHaveBeenCalledWith({
        enabled: true,
        mode: 'rollback',
        trial_enabled: true,
        checkout_enabled: false,
        config_enabled: true,
        maintenance_message: 'Canary rollback in progress',
        canary_telegram_user_ids: [123456789],
        change_reason: 'stabilize payment status errors',
      });
    });
  });

  it('submits the dedicated mini app launch readiness mutation', async () => {
    renderWithQueryClient(<PolicyConsole />);

    const releaseWindowInput = screen.getByPlaceholderText(
      'policy.launchReadiness.releaseWindowNotePlaceholder',
    );
    const reasonInput = screen.getByPlaceholderText(
      'policy.launchReadiness.changeReasonPlaceholder',
    );

    await waitFor(() => {
      expect(releaseWindowInput).toHaveValue('Friday 18:00 UTC');
    });

    fireEvent.click(screen.getByLabelText('policy.launchReadiness.items.incidentRunbook'));
    fireEvent.click(screen.getByLabelText('policy.launchReadiness.items.configDeliveryCanary'));
    fireEvent.click(screen.getByLabelText('policy.launchReadiness.items.rollbackDrill'));
    fireEvent.click(screen.getByLabelText('policy.launchReadiness.items.supportWindow'));
    fireEvent.click(screen.getByLabelText('policy.launchReadiness.items.customerComms'));
    fireEvent.click(screen.getByLabelText('policy.launchReadiness.items.statusPageTemplate'));
    fireEvent.change(reasonInput, {
      target: { value: 'all gates green after canary' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'policy.launchReadiness.apply' }));

    await waitFor(() => {
      expect(mockUpdateMiniAppLaunchReadinessConfig).toHaveBeenCalledWith({
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
    });
  });

  it('renders launch summary blockers from the server-derived summary', async () => {
    renderWithQueryClient(<PolicyConsole />);

    await waitFor(() => {
      const summaryHeading = screen.getByRole('heading', {
        name: 'policy.launchSummary.title',
      });
      const summaryCard = summaryHeading.closest('article');

      expect(mockGetMiniAppLaunchSummary).toHaveBeenCalled();
      expect(summaryCard).not.toBeNull();
      expect(within(summaryCard as HTMLElement).getByText('@ops-lead')).toBeInTheDocument();
      expect(within(summaryCard as HTMLElement).getByText('policy.launchSummary.liveSwitchBlocked')).toBeInTheDocument();
    });
  });

  it('executes summary-driven launch actions', async () => {
    renderWithQueryClient(<PolicyConsole />);

    const reasonInput = screen.getByPlaceholderText(
      'policy.launchActions.reasonPlaceholder',
    );

    await waitFor(() => {
      expect(screen.getByRole('button', {
        name: 'policy.launchActions.items.start_rollback',
      })).toBeInTheDocument();
    });

    fireEvent.change(reasonInput, {
      target: { value: 'checkout status regression in canary' },
    });
    fireEvent.click(screen.getByRole('button', {
      name: 'policy.launchActions.items.start_rollback',
    }));

    await waitFor(() => {
      expect(mockExecuteMiniAppLaunchAction).toHaveBeenCalledWith({
        action: 'start_rollback',
        change_reason: 'checkout status regression in canary',
      });
    });
  });

  it('renders recent mini app launch timeline entries', async () => {
    renderWithQueryClient(<PolicyConsole />);

    await waitFor(() => {
      expect(mockGetMiniAppLaunchTimeline).toHaveBeenCalledWith({ limit: 6 });
    });

    await waitFor(() => {
      const timelineHeading = screen.getByRole('heading', {
        name: 'policy.launchTimeline.title',
      });
      const timelineCard = timelineHeading.closest('article');

      expect(timelineCard).not.toBeNull();
      expect(within(timelineCard as HTMLElement).getByText('policy.launchActions.items.start_rollback')).toBeInTheDocument();
      expect(within(timelineCard as HTMLElement).getByText('checkout regression in canary')).toBeInTheDocument();
    });
  });

  it('renders a derived mini app launch checklist for operator review', async () => {
    renderWithQueryClient(<PolicyConsole />);

    await waitFor(() => {
      const checklistHeading = screen.getByRole('heading', {
        name: 'policy.launchChecklist.title',
      });
      const checklistCard = checklistHeading.closest('article');

      expect(checklistCard).not.toBeNull();
      expect(within(checklistCard as HTMLElement).getByText('policy.launchChecklist.releaseWindow')).toBeInTheDocument();
      expect(within(checklistCard as HTMLElement).getByText('Friday 18:00 UTC')).toBeInTheDocument();
      expect(within(checklistCard as HTMLElement).getByText('@ops-lead')).toBeInTheDocument();
      expect(within(checklistCard as HTMLElement).getAllByText('policy.launchChecklist.missingValue').length).toBeGreaterThan(0);
    });
  });
});
