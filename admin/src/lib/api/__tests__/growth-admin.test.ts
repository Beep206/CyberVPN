import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { growthApi } from '../growth';

const API_BASE = '*/api/v1';
const ORIGINAL_SEND_BEACON = navigator.sendBeacon;
const sendBeacon = vi.fn();

const MATCH_ANY_API_ORIGIN = {
  promoCodes: `${API_BASE}/admin/promo-codes`,
  promoCodeById: `${API_BASE}/admin/promo-codes/:promoId`,
  inviteCodes: `${API_BASE}/admin/invite-codes`,
  partnerPromote: `${API_BASE}/admin/partners/promote`,
  referralOverview: `${API_BASE}/admin/referrals/overview`,
  referralUserDetail: `${API_BASE}/admin/referrals/users/:userId`,
  growthSignalsOverview: `${API_BASE}/admin/growth-signals/overview`,
  growthReportingOverview: `${API_BASE}/admin/growth-reporting/overview`,
  growthReportingGovernance: `${API_BASE}/admin/growth-reporting/governance`,
  growthReportingRefresh: `${API_BASE}/admin/growth-reporting/refresh`,
  growthReportingExport: `${API_BASE}/admin/growth-reporting/export`,
  growthReportingGovernanceExport: `${API_BASE}/admin/growth-reporting/governance/export`,
  growthReportingSubscriptions: `${API_BASE}/admin/growth-reporting/subscriptions`,
  growthReportingSubscriptionUpdate: `${API_BASE}/admin/growth-reporting/subscriptions/:subscriptionId`,
  growthReportingSubscriptionPause: `${API_BASE}/admin/growth-reporting/subscriptions/:subscriptionId/pause`,
  growthReportingSubscriptionResume: `${API_BASE}/admin/growth-reporting/subscriptions/:subscriptionId/resume`,
  growthReportingSubscriptionFollowup: `${API_BASE}/admin/growth-reporting/subscriptions/:subscriptionId/follow-up/:action`,
  growthReportingDeliveries: `${API_BASE}/admin/growth-reporting/deliveries`,
  growthReportingDeliveryArtifact: `${API_BASE}/admin/growth-reporting/deliveries/:deliveryId/artifact`,
  growthSignalsAbuseQueue: `${API_BASE}/admin/growth-signals/abuse-queue`,
  growthNotificationDeliveries: `${API_BASE}/admin/growth-notification-deliveries`,
  growthNotificationDeliveryDetail: `${API_BASE}/admin/growth-notification-deliveries/:deliveryId`,
  growthNotificationDeliveryExport: `${API_BASE}/admin/growth-notification-deliveries/:deliveryId/export`,
  growthNotificationDeliveriesManual: `${API_BASE}/admin/growth-notification-deliveries/manual`,
  growthNotificationDeliveryResend: `${API_BASE}/admin/growth-notification-deliveries/:deliveryId/resend`,
  growthNotificationDeliveryPause: `${API_BASE}/admin/growth-notification-deliveries/:deliveryId/pause`,
  growthNotificationDeliveryRevoke: `${API_BASE}/admin/growth-notification-deliveries/:deliveryId/revoke`,
  growthNotificationDeliveryResolve: `${API_BASE}/admin/growth-notification-deliveries/:deliveryId/resolve`,
  partners: `${API_BASE}/admin/partners`,
  partnerDetail: `${API_BASE}/admin/partners/:userId`,
  growthCodeLookup: `${API_BASE}/admin/growth-codes/lookup`,
  giftCodes: `${API_BASE}/admin/gift-codes`,
  giftCodesIssue: `${API_BASE}/admin/gift-codes/issue`,
  giftCodeBatchesIssue: `${API_BASE}/admin/gift-code-batches/issue`,
  partnerWorkspaces: `${API_BASE}/admin/partner-workspaces`,
  partnerWorkspaceDetail: `${API_BASE}/admin/partner-workspaces/:workspaceId`,
};

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
  sendBeacon.mockClear();
  Object.defineProperty(window.navigator, 'sendBeacon', {
    configurable: true,
    value: sendBeacon,
  });
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
  Object.defineProperty(window.navigator, 'sendBeacon', {
    configurable: true,
    value: ORIGINAL_SEND_BEACON,
  });
});

describe('growthApi promo code operations', () => {
  it('loads growth signals overview', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.growthSignalsOverview, () =>
        HttpResponse.json({
          total_codes: 24,
          active_codes: 18,
          total_redemptions: 9,
          active_reservations: 2,
          blocked_reward_count: 1,
          available_referral_credit_usd: 37.5,
          code_status_breakdown: [{ key: 'promo:active', count: 8 }],
          resolution_result_breakdown: [{ key: 'accepted', count: 12 }],
          rejection_reason_breakdown: [{ key: 'code_conflicts_with_partner_binding', count: 3 }],
          redemption_breakdown: [{ key: 'gift', count: 4 }],
          reward_status_breakdown: [{ key: 'available', count: 5 }],
          reward_type_breakdown: [{ key: 'referral_credit', count: 5 }],
          recent_lifecycle_events: [
            {
              id: 'evt_001',
              event_name: 'gift.issued',
              event_family: 'gift',
              aggregate_type: 'growth_code',
              aggregate_id: 'gift_001',
              occurred_at: '2026-04-21T10:00:00Z',
              event_status: 'pending_publication',
            },
          ],
        }),
      ),
    );

    const response = await growthApi.getGrowthSignalsOverview();

    expect(response.status).toBe(200);
    expect(response.data.total_codes).toBe(24);
    expect(response.data.recent_lifecycle_events[0]?.event_name).toBe('gift.issued');
  });

  it('refreshes, loads, and exports growth reporting rollups', async () => {
    server.use(
      http.post(MATCH_ANY_API_ORIGIN.growthReportingRefresh, () =>
        HttpResponse.json({
          trigger_kind: 'manual',
          window_start: '2026-04-09',
          window_end: '2026-04-22',
          latest_rollup_date: '2026-04-22',
          refreshed_at: '2026-04-22T14:00:00Z',
          rows_written: 18,
          families_updated: ['gift', 'invite', 'promo', 'referral'],
          coverage_notes: ['rollup coverage note'],
        }),
      ),
      http.get(MATCH_ANY_API_ORIGIN.growthReportingOverview, () =>
        HttpResponse.json({
          window_start: '2026-04-09',
          window_end: '2026-04-22',
          latest_rollup_date: '2026-04-22',
          refreshed_at: '2026-04-22T14:00:00Z',
          family_summaries: [
            {
              family: 'promo',
              issued_total: 4,
              resolution_attempts_total: 11,
              resolution_accepted_total: 8,
              resolution_rejected_total: 3,
              redemption_total: 0,
              reservations_reserved_total: 6,
              reservations_consumed_total: 5,
              reservations_released_total: 1,
              reservations_expired_total: 0,
              rewards_created_total: 0,
              rewards_available_total: 0,
              rewards_reversed_total: 0,
              reward_created_amount_usd: 0,
              reward_available_amount_usd: 0,
              reward_reversed_amount_usd: 0,
            },
          ],
          daily_points: [
            {
              report_date: '2026-04-22',
              family: 'promo',
              issued_total: 1,
              resolution_attempts_total: 2,
              resolution_accepted_total: 1,
              resolution_rejected_total: 1,
              redemption_total: 0,
              reservations_reserved_total: 1,
              reservations_consumed_total: 1,
              reservations_released_total: 0,
              reservations_expired_total: 0,
              rewards_created_total: 0,
              rewards_available_total: 0,
              rewards_reversed_total: 0,
              reward_created_amount_usd: 0,
              reward_available_amount_usd: 0,
              reward_reversed_amount_usd: 0,
            },
          ],
          totals: {
            family: 'all',
            issued_total: 6,
            resolution_attempts_total: 11,
            resolution_accepted_total: 8,
            resolution_rejected_total: 3,
            redemption_total: 2,
            reservations_reserved_total: 6,
            reservations_consumed_total: 5,
            reservations_released_total: 1,
            reservations_expired_total: 0,
            rewards_created_total: 3,
            rewards_available_total: 2,
            rewards_reversed_total: 1,
            reward_created_amount_usd: 15,
            reward_available_amount_usd: 10,
            reward_reversed_amount_usd: 5,
          },
          health: {
            freshness_status: 'fresh',
            stale_reason: null,
            refresh_age_seconds: 120,
            expected_refresh_interval_seconds: 3600,
            stale_after_seconds: 10800,
            auto_refresh_enabled: true,
            latest_attempt_at: '2026-04-22T14:00:00Z',
            latest_success_at: '2026-04-22T14:00:00Z',
            latest_failure_at: null,
            latest_failure_message: null,
            latest_run: {
              id: 'run_001',
              trigger_kind: 'worker',
              refresh_status: 'success',
              requested_window_days: 30,
              window_start: '2026-03-24',
              window_end: '2026-04-22',
              latest_rollup_date: '2026-04-22',
              rows_written: 18,
              families_updated: ['gift', 'invite', 'promo', 'referral'],
              error_message: null,
              started_at: '2026-04-22T13:59:58Z',
              finished_at: '2026-04-22T14:00:00Z',
              refreshed_at: '2026-04-22T14:00:00Z',
            },
          },
          executive_summary: {
            total_issued: 6,
            total_redemptions: 2,
            total_reward_available_usd: 10,
            total_reward_reversed_usd: 5,
            resolution_acceptance_rate_pct: 72.7,
            dominant_family: 'promo',
            highlights: ['Executive note'],
          },
          coverage_notes: ['rollup coverage note'],
        }),
      ),
      http.get(MATCH_ANY_API_ORIGIN.growthReportingGovernance, () =>
        HttpResponse.json({
          generated_at: '2026-04-22T14:30:00Z',
          active_subscription_count: 3,
          paused_subscription_count: 1,
          coverage_gap_count: 2,
          followup_open_count: 2,
          followup_overdue_count: 1,
          coverage_counts: [
            { coverage_state: 'active_healthy', count: 1 },
            { coverage_state: 'delivery_suppressed', count: 1 },
            { coverage_state: 'recipient_domain_blocked', count: 1 },
          ],
          followup_queue: [
            {
              subscription_id: 'sub_gap_001',
              recipient_email: 'ops-board@blocked.test',
              audience_key: 'ops',
              health_status: 'recipient_domain_blocked',
              followup: {
                status: 'open',
                reason_code: 'recipient_domain_blocked',
                opened_at: '2026-04-22T14:00:00Z',
                due_at: '2026-04-22T16:00:00Z',
                last_notified_at: '2026-04-22T14:30:00Z',
                resolved_at: null,
                resolution_code: null,
                is_overdue: false,
                action_required: true,
              },
              next_delivery_at: '2026-04-22T15:00:00Z',
              latest_delivery_status: 'skipped',
              latest_delivery_reason: 'recipient_domain_blocked',
            },
          ],
          recent_decisions: [
            {
              delivery_id: 'delivery_gap_001',
              subscription_id: 'sub_gap_001',
              recipient_email: 'ops-board@blocked.test',
              audience_key: 'ops',
              template_key: 'ops_exec',
              decision_kind: 'recipient_domain_blocked',
              status_reason: 'recipient_domain_blocked',
              created_at: '2026-04-22T14:20:00Z',
              planned_at: '2026-04-22T14:20:00Z',
              window_start: '2026-04-08',
              window_end: '2026-04-22',
              can_export_artifact: true,
              summary: 'Delivery skipped because the recipient domain is blocked by policy.',
            },
          ],
          recent_audit_events: [
            {
              id: 'audit_growth_001',
              action: 'growth_reporting.subscription.updated',
              entity_id: 'sub_gap_001',
              actor_label: 'Growth Admin',
              reason_code: 'recipient_governance_refresh',
              changed_fields: ['recipient_email', 'policy.allowed_recipient_domains'],
              created_at: '2026-04-22T14:10:00Z',
            },
          ],
          notes: ['1 active subscription is blocked by recipient domain policy.'],
        }),
      ),
      http.get(MATCH_ANY_API_ORIGIN.growthReportingExport, () =>
        new HttpResponse(JSON.stringify({ export_kind: 'growth_reporting_rollups' }), {
          headers: {
            'Content-Type': 'application/json',
            'Content-Disposition': 'attachment; filename=\"growth-reporting-2026-04-09-2026-04-22.json\"',
          },
        }),
      ),
      http.get(MATCH_ANY_API_ORIGIN.growthReportingGovernanceExport, () =>
        new HttpResponse(JSON.stringify({ export_kind: 'growth_reporting_governance_snapshot' }), {
          headers: {
            'Content-Type': 'application/json',
            'Content-Disposition': 'attachment; filename=\"growth-reporting-governance-2026-04-22.json\"',
          },
        }),
      ),
    );

    const refreshResponse = await growthApi.refreshGrowthReporting({ window_days: 30 });
    const overviewResponse = await growthApi.getGrowthReportingOverview({ window_days: 14 });
    const governanceResponse = await growthApi.getGrowthReportingGovernanceOverview();
    const exportResponse = await growthApi.exportGrowthReportingOverview({ window_days: 30 });
    const governanceExportResponse = await growthApi.exportGrowthReportingGovernanceSnapshot();

    expect(refreshResponse.status).toBe(200);
    expect(refreshResponse.data.rows_written).toBe(18);
    expect(refreshResponse.data.trigger_kind).toBe('manual');
    expect(overviewResponse.status).toBe(200);
    expect(overviewResponse.data.family_summaries[0]?.family).toBe('promo');
    expect(overviewResponse.data.totals.reward_created_amount_usd).toBe(15);
    expect(overviewResponse.data.health.freshness_status).toBe('fresh');
    expect(overviewResponse.data.executive_summary.dominant_family).toBe('promo');
    expect(governanceResponse.status).toBe(200);
    expect(governanceResponse.data.coverage_gap_count).toBe(2);
    expect(governanceResponse.data.followup_open_count).toBe(2);
    expect(governanceResponse.data.recent_decisions[0]?.decision_kind).toBe('recipient_domain_blocked');
    expect(exportResponse.status).toBe(200);
    expect(exportResponse.headers['content-disposition']).toContain('attachment; filename=');
    expect(exportResponse.data).toBeInstanceOf(Blob);
    expect(governanceExportResponse.status).toBe(200);
    expect(governanceExportResponse.headers['content-disposition']).toContain('attachment; filename=');
    expect(governanceExportResponse.data).toBeInstanceOf(Blob);
  });

  it('manages recurring growth reporting subscriptions and delivery artifacts', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.growthReportingSubscriptions, () =>
        HttpResponse.json({
          items: [
            {
              id: 'sub_001',
              recipient_email: 'finance-growth@example.test',
              recipient_name: 'Finance',
              audience_key: 'finance',
              delivery_channel: 'email',
              cadence: 'daily',
              report_window_days: 30,
              subscription_status: 'active',
              next_delivery_at: '2026-04-22T15:00:00Z',
              last_delivery_attempt_at: '2026-04-22T14:00:00Z',
              last_success_at: '2026-04-22T14:01:00Z',
              latest_delivery_status: 'delivered',
              latest_delivery_reason: null,
              health_status: 'healthy',
              followup: {
                status: 'none',
                reason_code: null,
                opened_at: null,
                due_at: null,
                last_notified_at: null,
                resolved_at: null,
                resolution_code: null,
                is_overdue: false,
                action_required: false,
              },
              policy: {
                template_key: 'finance_exec',
                template_locale: 'en-EN',
                email_subject_prefix: '[CyberVPN][Growth][Finance]',
                title_override: null,
                recipient_domain_policy: 'allowlist_only',
                allowed_recipient_domains: ['example.test'],
                suppressed_until: null,
                suppression_reason_code: null,
              },
            },
          ],
          total: 1,
          overdue_count: 0,
          active_count: 1,
          retention_rollup_days: 180,
          retention_refresh_run_days: 180,
          retention_delivery_days: 90,
        }),
      ),
      http.post(MATCH_ANY_API_ORIGIN.growthReportingSubscriptions, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: 'sub_002',
            recipient_email: body.recipient_email,
            recipient_name: body.recipient_name,
            audience_key: body.audience_key,
            delivery_channel: 'email',
            cadence: body.cadence,
            report_window_days: body.report_window_days,
            subscription_status: 'active',
            next_delivery_at: '2026-04-22T16:00:00Z',
            last_delivery_attempt_at: null,
            last_success_at: null,
            latest_delivery_status: null,
            latest_delivery_reason: null,
            health_status: 'healthy',
            followup: {
              status: 'none',
              reason_code: null,
              opened_at: null,
              due_at: null,
              last_notified_at: null,
              resolved_at: null,
              resolution_code: null,
              is_overdue: false,
              action_required: false,
            },
            policy: body.policy,
          },
          { status: 201 },
        );
      }),
      http.put(MATCH_ANY_API_ORIGIN.growthReportingSubscriptionUpdate, async ({ params, request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: params.subscriptionId,
          recipient_email: body.recipient_email,
          recipient_name: body.recipient_name,
          audience_key: body.audience_key,
          delivery_channel: 'email',
          cadence: body.cadence,
          report_window_days: body.report_window_days,
          subscription_status: 'active',
          next_delivery_at: '2026-04-22T17:00:00Z',
          last_delivery_attempt_at: '2026-04-22T14:00:00Z',
          last_success_at: '2026-04-22T14:01:00Z',
          latest_delivery_status: 'delivered',
          latest_delivery_reason: null,
          health_status: 'suppressed',
          followup: {
            status: 'open',
            reason_code: 'delivery_suppressed',
            opened_at: '2026-04-22T14:05:00Z',
            due_at: '2026-04-23T13:00:00Z',
            last_notified_at: null,
            resolved_at: null,
            resolution_code: null,
            is_overdue: false,
            action_required: true,
          },
          policy: body.policy,
        });
      }),
      http.post(MATCH_ANY_API_ORIGIN.growthReportingSubscriptionPause, ({ params }) =>
        HttpResponse.json({
          id: params.subscriptionId,
          recipient_email: 'finance-growth@example.test',
          recipient_name: 'Finance',
          audience_key: 'finance',
          delivery_channel: 'email',
          cadence: 'daily',
          report_window_days: 30,
          subscription_status: 'paused',
          next_delivery_at: '2026-04-22T15:00:00Z',
          last_delivery_attempt_at: '2026-04-22T14:00:00Z',
          last_success_at: '2026-04-22T14:01:00Z',
          latest_delivery_status: 'delivered',
          latest_delivery_reason: null,
          health_status: 'paused',
          followup: {
            status: 'resolved',
            reason_code: 'delivery_suppressed',
            opened_at: '2026-04-22T14:05:00Z',
            due_at: '2026-04-23T13:00:00Z',
            last_notified_at: '2026-04-22T14:10:00Z',
            resolved_at: '2026-04-22T14:10:00Z',
            resolution_code: 'ops_pause',
            is_overdue: false,
            action_required: false,
          },
          policy: {
            template_key: 'finance_exec',
            template_locale: 'en-EN',
            email_subject_prefix: '[CyberVPN][Growth][Finance]',
            title_override: null,
            recipient_domain_policy: 'allowlist_only',
            allowed_recipient_domains: ['example.test'],
            suppressed_until: null,
            suppression_reason_code: null,
          },
        }),
      ),
      http.post(MATCH_ANY_API_ORIGIN.growthReportingSubscriptionResume, ({ params }) =>
        HttpResponse.json({
          id: params.subscriptionId,
          recipient_email: 'finance-growth@example.test',
          recipient_name: 'Finance',
          audience_key: 'finance',
          delivery_channel: 'email',
          cadence: 'daily',
          report_window_days: 30,
          subscription_status: 'active',
          next_delivery_at: '2026-04-22T16:00:00Z',
          last_delivery_attempt_at: '2026-04-22T14:00:00Z',
          last_success_at: '2026-04-22T14:01:00Z',
          latest_delivery_status: 'delivered',
          latest_delivery_reason: null,
          health_status: 'healthy',
          followup: {
            status: 'none',
            reason_code: null,
            opened_at: null,
            due_at: null,
            last_notified_at: null,
            resolved_at: null,
            resolution_code: null,
            is_overdue: false,
            action_required: false,
          },
          policy: {
            template_key: 'finance_exec',
            template_locale: 'en-EN',
            email_subject_prefix: '[CyberVPN][Growth][Finance]',
            title_override: null,
            recipient_domain_policy: 'allowlist_only',
            allowed_recipient_domains: ['example.test'],
            suppressed_until: null,
            suppression_reason_code: null,
          },
        }),
      ),
      http.post(MATCH_ANY_API_ORIGIN.growthReportingSubscriptionFollowup, ({ params }) =>
        HttpResponse.json({
          id: params.subscriptionId,
          recipient_email: 'finance-growth@example.test',
          recipient_name: 'Finance',
          audience_key: 'finance',
          delivery_channel: 'email',
          cadence: 'daily',
          report_window_days: 30,
          subscription_status: 'active',
          next_delivery_at: '2026-04-22T16:00:00Z',
          last_delivery_attempt_at: '2026-04-22T14:00:00Z',
          last_success_at: '2026-04-22T14:01:00Z',
          latest_delivery_status: 'skipped',
          latest_delivery_reason: 'delivery_suppressed',
          health_status: 'suppressed',
          followup: {
            status: 'resolved',
            reason_code: 'delivery_suppressed',
            opened_at: '2026-04-22T14:05:00Z',
            due_at: '2026-04-23T13:00:00Z',
            last_notified_at: '2026-04-22T14:20:00Z',
            resolved_at: '2026-04-22T14:20:00Z',
            resolution_code: 'admin_recovered',
            is_overdue: false,
            action_required: false,
          },
          policy: {
            template_key: 'finance_exec',
            template_locale: 'en-EN',
            email_subject_prefix: '[CyberVPN][Growth][Finance]',
            title_override: null,
            recipient_domain_policy: 'allowlist_only',
            allowed_recipient_domains: ['example.test'],
            suppressed_until: null,
            suppression_reason_code: null,
          },
        }),
      ),
      http.get(MATCH_ANY_API_ORIGIN.growthReportingDeliveries, () =>
        HttpResponse.json({
          items: [
            {
              id: 'delivery_001',
              subscription_id: 'sub_001',
              recipient_email: 'finance-growth@example.test',
              recipient_name: 'Finance',
              audience_key: 'finance',
              delivery_channel: 'email',
              cadence: 'daily',
              report_window_days: 30,
              template_key: 'finance_exec',
              template_locale: 'en-EN',
              subject_line: '[CyberVPN][Growth][Finance] Daily digest 2026-04-22',
              title_line: 'Finance growth reporting digest',
              delivery_status: 'delivered',
              status_reason: null,
              freshness_status: 'fresh',
              artifact_checksum: 'checksum-1',
              provider_name: 'smtp',
              provider_message_id: 'msg-1',
              failure_message: null,
              window_start: '2026-03-24',
              window_end: '2026-04-22',
              planned_at: '2026-04-22T15:00:00Z',
              started_at: '2026-04-22T15:00:05Z',
              delivered_at: '2026-04-22T15:00:10Z',
              created_at: '2026-04-22T15:00:00Z',
              updated_at: '2026-04-22T15:00:10Z',
              can_export_artifact: true,
              policy: {
                template_key: 'finance_exec',
                template_locale: 'en-EN',
                email_subject_prefix: '[CyberVPN][Growth][Finance]',
                title_override: null,
                recipient_domain_policy: 'allowlist_only',
                allowed_recipient_domains: ['example.test'],
                suppressed_until: null,
                suppression_reason_code: null,
              },
            },
          ],
          total: 1,
          failed_count: 0,
        }),
      ),
      http.get(MATCH_ANY_API_ORIGIN.growthReportingDeliveryArtifact, () =>
        new HttpResponse(JSON.stringify({ export_kind: 'growth_reporting_delivery_artifact' }), {
          headers: {
            'Content-Type': 'application/json',
            'Content-Disposition': 'attachment; filename=\"growth-reporting-delivery-finance-2026-03-24-2026-04-22.json\"',
          },
        }),
      ),
    );

    const subscriptionsResponse = await growthApi.listGrowthReportingSubscriptions();
    const createResponse = await growthApi.createGrowthReportingSubscription({
      recipient_email: 'risk-growth@example.test',
      recipient_name: 'Risk',
      audience_key: 'risk',
      cadence: 'weekly',
      report_window_days: 30,
      policy: {
        template_key: 'risk_exec',
        recipient_domain_policy: 'allowlist_only',
        allowed_recipient_domains: ['example.test'],
      },
    });
    const updateResponse = await growthApi.updateGrowthReportingSubscription('sub_001', {
      recipient_email: 'finance-leads@example.test',
      recipient_name: 'Finance Leads',
      audience_key: 'finance',
      cadence: 'daily',
      report_window_days: 45,
      policy: {
        template_key: 'finance_exec',
        template_locale: 'en-EN',
        email_subject_prefix: '[CyberVPN][Growth][Finance][Exec]',
        title_override: 'Finance board digest',
        recipient_domain_policy: 'allowlist_only',
        allowed_recipient_domains: ['example.test'],
        suppressed_until: '2026-04-23T12:00:00Z',
        suppression_reason_code: 'board_freeze',
      },
      reason_code: 'recipient_governance_refresh',
    });
    const pauseResponse = await growthApi.pauseGrowthReportingSubscription('sub_001', {
      reason_code: 'ops_pause',
    });
    const resumeResponse = await growthApi.resumeGrowthReportingSubscription('sub_001', {
      reason_code: 'ops_resume',
    });
    const followupResponse = await growthApi.updateGrowthReportingGovernanceFollowup('sub_001', 'resolve', {
      reason_code: 'admin_recovered',
    });
    const deliveriesResponse = await growthApi.listGrowthReportingDeliveries({ limit: 5 });
    const artifactResponse = await growthApi.exportGrowthReportingDeliveryArtifact('delivery_001');

    expect(subscriptionsResponse.status).toBe(200);
    expect(subscriptionsResponse.data.total).toBe(1);
    expect(createResponse.status).toBe(201);
    expect(createResponse.data.audience_key).toBe('risk');
    expect(createResponse.data.policy.template_key).toBe('risk_exec');
    expect(updateResponse.status).toBe(200);
    expect(updateResponse.data.recipient_email).toBe('finance-leads@example.test');
    expect(updateResponse.data.policy.suppression_reason_code).toBe('board_freeze');
    expect(pauseResponse.status).toBe(200);
    expect(pauseResponse.data.subscription_status).toBe('paused');
    expect(resumeResponse.status).toBe(200);
    expect(resumeResponse.data.subscription_status).toBe('active');
    expect(followupResponse.status).toBe(200);
    expect(followupResponse.data.followup.status).toBe('resolved');
    expect(deliveriesResponse.status).toBe(200);
    expect(deliveriesResponse.data.items[0]?.delivery_status).toBe('delivered');
    expect(deliveriesResponse.data.items[0]?.template_key).toBe('finance_exec');
    expect(artifactResponse.status).toBe(200);
    expect(artifactResponse.headers['content-disposition']).toContain('attachment; filename=');
    expect(artifactResponse.data).toBeInstanceOf(Blob);
  });

  it('lists growth abuse signals', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.growthSignalsAbuseQueue, () =>
        HttpResponse.json({
          items: [
            {
              signal_key: 'resolution:abc:self',
              signal_type: 'invite_self_redemption',
              severity: 'danger',
              code_type: 'invite',
              reason_code: 'invite_self_redemption_blocked',
              count: 3,
              unique_users: 1,
              latest_event_at: '2026-04-21T11:00:00Z',
              review_hint: 'Check the cluster before escalation.',
              growth_code_id: null,
              reward_allocation_id: null,
              beneficiary_user_id: null,
              source_redemption_id: null,
            },
          ],
          total: 1,
        }),
      ),
    );

    const response = await growthApi.listGrowthAbuseSignals({ limit: 10 });

    expect(response.status).toBe(200);
    expect(response.data.total).toBe(1);
    expect(response.data.items[0]?.reason_code).toBe('invite_self_redemption_blocked');
  });

  it('lists growth notification deliveries', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.growthNotificationDeliveries, () =>
        HttpResponse.json({
          items: [
            {
              id: 'delivery_001',
              mobile_user_id: 'user_001',
              user: {
                id: 'user_001',
                email: 'growth@example.com',
                username: null,
                telegram_username: null,
                referral_code: null,
                is_partner: false,
              },
              notification_key: 'admin_manual_notification:delivery_001',
              notification_kind: 'admin_manual_update',
              delivery_channel: 'email',
              delivery_status: 'planned',
              status_reason: null,
              title: 'Account review update',
              message: 'Support issued a manual growth notice.',
              route_slug: '/referral',
              notes: ['Ticket: SUP-42'],
              source_kind: 'admin_manual_notification',
              source_id: 'delivery_001',
              notification_queue_id: null,
              queue_status: null,
              queue_error_message: null,
              created_by_admin_user_id: 'admin_001',
              planned_at: '2026-04-22T12:00:00Z',
              delivered_at: null,
              created_at: '2026-04-22T12:00:00Z',
              updated_at: '2026-04-22T12:00:00Z',
              can_resend: true,
              can_pause: true,
              can_revoke: true,
              can_resolve: false,
            },
          ],
          total: 1,
          offset: 0,
          limit: 10,
        }),
      ),
    );

    const response = await growthApi.listGrowthNotificationDeliveries({
      mobile_user_id: 'user_001',
      limit: 10,
    });

    expect(response.status).toBe(200);
    expect(response.data.total).toBe(1);
    expect(response.data.items[0]?.notification_kind).toBe('admin_manual_update');
  });

  it('creates a manual growth notification and manages delivery actions', async () => {
    let capturedManualBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.growthNotificationDeliveriesManual, async ({ request }) => {
        capturedManualBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            deliveries: [
              {
                id: 'delivery_email',
                mobile_user_id: 'user_001',
                user: null,
                notification_key: 'admin_manual_notification:delivery_email',
                notification_kind: 'admin_manual_update',
                delivery_channel: 'email',
                delivery_status: 'planned',
                status_reason: null,
                title: 'Account review update',
                message: 'Support issued a manual growth notice.',
                route_slug: '/referral',
                notes: ['Ticket: SUP-42'],
                source_kind: 'admin_manual_notification',
                source_id: 'notice_001',
                notification_queue_id: null,
                queue_status: null,
                queue_error_message: null,
                created_by_admin_user_id: 'admin_001',
                planned_at: '2026-04-22T12:00:00Z',
                delivered_at: null,
                created_at: '2026-04-22T12:00:00Z',
                updated_at: '2026-04-22T12:00:00Z',
                can_resend: true,
                can_pause: true,
                can_revoke: true,
                can_resolve: false,
              },
            ],
          },
          { status: 201 },
        );
      }),
      http.post(MATCH_ANY_API_ORIGIN.growthNotificationDeliveryResend, () =>
        HttpResponse.json({
          id: 'delivery_email',
          mobile_user_id: 'user_001',
          user: null,
          notification_key: 'admin_manual_notification:delivery_email',
          notification_kind: 'admin_manual_update',
          delivery_channel: 'email',
          delivery_status: 'planned',
          status_reason: 'retry_after_pause',
          title: 'Account review update',
          message: 'Support issued a manual growth notice.',
          route_slug: '/referral',
          notes: ['Ticket: SUP-42'],
          source_kind: 'admin_manual_notification',
          source_id: 'notice_001',
          notification_queue_id: null,
          queue_status: null,
          queue_error_message: null,
          created_by_admin_user_id: 'admin_001',
          planned_at: '2026-04-22T12:05:00Z',
          delivered_at: null,
          created_at: '2026-04-22T12:00:00Z',
          updated_at: '2026-04-22T12:05:00Z',
          can_resend: true,
          can_pause: true,
          can_revoke: true,
          can_resolve: true,
        }),
      ),
      http.post(MATCH_ANY_API_ORIGIN.growthNotificationDeliveryPause, () =>
        HttpResponse.json({
          id: 'delivery_email',
          mobile_user_id: 'user_001',
          user: null,
          notification_key: 'admin_manual_notification:delivery_email',
          notification_kind: 'admin_manual_update',
          delivery_channel: 'email',
          delivery_status: 'paused',
          status_reason: 'ops_pause',
          title: 'Account review update',
          message: 'Support issued a manual growth notice.',
          route_slug: '/referral',
          notes: ['Ticket: SUP-42'],
          source_kind: 'admin_manual_notification',
          source_id: 'notice_001',
          notification_queue_id: null,
          queue_status: null,
          queue_error_message: null,
          created_by_admin_user_id: 'admin_001',
          planned_at: '2026-04-22T12:00:00Z',
          delivered_at: null,
          created_at: '2026-04-22T12:00:00Z',
          updated_at: '2026-04-22T12:04:00Z',
          can_resend: true,
          can_pause: false,
          can_revoke: true,
          can_resolve: true,
        }),
      ),
      http.post(MATCH_ANY_API_ORIGIN.growthNotificationDeliveryRevoke, () =>
        HttpResponse.json({
          id: 'delivery_email',
          mobile_user_id: 'user_001',
          user: null,
          notification_key: 'admin_manual_notification:delivery_email',
          notification_kind: 'admin_manual_update',
          delivery_channel: 'email',
          delivery_status: 'revoked',
          status_reason: 'ops_revoke',
          title: 'Account review update',
          message: 'Support issued a manual growth notice.',
          route_slug: '/referral',
          notes: ['Ticket: SUP-42'],
          source_kind: 'admin_manual_notification',
          source_id: 'notice_001',
          notification_queue_id: null,
          queue_status: null,
          queue_error_message: null,
          created_by_admin_user_id: 'admin_001',
          planned_at: '2026-04-22T12:00:00Z',
          delivered_at: null,
          created_at: '2026-04-22T12:00:00Z',
          updated_at: '2026-04-22T12:06:00Z',
          can_resend: false,
          can_pause: false,
          can_revoke: false,
          can_resolve: true,
        }),
      ),
      http.post(MATCH_ANY_API_ORIGIN.growthNotificationDeliveryResolve, () =>
        HttpResponse.json({
          id: 'delivery_email',
          mobile_user_id: 'user_001',
          user: null,
          notification_key: 'admin_manual_notification:delivery_email',
          notification_kind: 'admin_manual_update',
          delivery_channel: 'email',
          delivery_status: 'planned',
          status_reason: 'support_resolved',
          title: 'Account review update',
          message: 'Support issued a manual growth notice.',
          route_slug: '/referral',
          notes: ['Ticket: SUP-42'],
          source_kind: 'growth_notification_closure',
          source_id: 'delivery_email',
          notification_queue_id: null,
          queue_status: null,
          queue_error_message: null,
          created_by_admin_user_id: 'admin_001',
          planned_at: '2026-04-22T12:07:00Z',
          delivered_at: null,
          created_at: '2026-04-22T12:00:00Z',
          updated_at: '2026-04-22T12:07:00Z',
          can_resend: true,
          can_pause: true,
          can_revoke: true,
          can_resolve: false,
        }),
      ),
    );

    const createResponse = await growthApi.createManualGrowthNotification({
      mobile_user_id: 'user_001',
      title: 'Account review update',
      message: 'Support issued a manual growth notice.',
      route_slug: '/referral',
      locale: 'en-EN',
      notes: ['Ticket: SUP-42'],
      channels: ['in_app', 'email'],
    });
    const pauseResponse = await growthApi.pauseGrowthNotificationDelivery('delivery_email', {
      reason_code: 'ops_pause',
    });
    const resendResponse = await growthApi.resendGrowthNotificationDelivery('delivery_email', {
      reason_code: 'retry_after_pause',
    });
    const revokeResponse = await growthApi.revokeGrowthNotificationDelivery('delivery_email', {
      reason_code: 'ops_revoke',
    });
    const resolveResponse = await growthApi.resolveGrowthNotificationDelivery('delivery_email', {
      reason_code: 'support_resolved',
    });

    expect(createResponse.status).toBe(201);
    expect(createResponse.data.deliveries[0]?.delivery_status).toBe('planned');
    expect(pauseResponse.data.delivery_status).toBe('paused');
    expect(resendResponse.data.status_reason).toBe('retry_after_pause');
    expect(revokeResponse.data.delivery_status).toBe('revoked');
    expect(resolveResponse.data.status_reason).toBe('support_resolved');
    expect(capturedManualBody).toMatchObject({
      mobile_user_id: 'user_001',
      title: 'Account review update',
      channels: ['in_app', 'email'],
    });
  });

  it('loads and exports growth notification delivery forensics', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.growthNotificationDeliveryDetail, () =>
        HttpResponse.json({
          delivery: {
            id: 'delivery_email',
            mobile_user_id: 'user_001',
            user: {
              id: 'user_001',
              email: 'growth@example.com',
              username: null,
              telegram_username: null,
              referral_code: null,
              is_partner: false,
            },
            notification_key: 'admin_manual_notification:delivery_email',
            notification_kind: 'admin_manual_update',
            delivery_channel: 'email',
            delivery_status: 'failed',
            status_reason: 'timeout',
            title: 'Account review update',
            message: 'Support issued a manual growth notice.',
            route_slug: '/referral',
            notes: ['Ticket: SUP-42'],
            source_kind: 'admin_manual_notification',
            source_id: 'notice_001',
            notification_queue_id: null,
            queue_status: null,
            queue_error_message: null,
            created_by_admin_user_id: 'admin_001',
            planned_at: '2026-04-22T12:00:00Z',
            delivered_at: null,
            created_at: '2026-04-22T12:00:00Z',
            updated_at: '2026-04-22T12:10:00Z',
            can_resend: true,
            can_pause: true,
            can_revoke: true,
            can_resolve: true,
          },
          sibling_deliveries: [
            {
              id: 'delivery_in_app',
              mobile_user_id: 'user_001',
              user: null,
              notification_key: 'admin_manual_notification:delivery_email',
              notification_kind: 'admin_manual_update',
              delivery_channel: 'in_app',
              delivery_status: 'delivered',
              status_reason: null,
              title: 'Account review update',
              message: 'Support issued a manual growth notice.',
              route_slug: '/referral',
              notes: [],
              source_kind: 'admin_manual_notification',
              source_id: 'notice_001',
              notification_queue_id: null,
              queue_status: null,
              queue_error_message: null,
              created_by_admin_user_id: 'admin_001',
              planned_at: '2026-04-22T12:00:00Z',
              delivered_at: '2026-04-22T12:00:00Z',
              created_at: '2026-04-22T12:00:00Z',
              updated_at: '2026-04-22T12:00:00Z',
              can_resend: false,
              can_pause: false,
              can_revoke: false,
              can_resolve: false,
            },
          ],
          event_timeline: [
            {
              id: 'evt_001',
              event_type: 'admin_resend_requested',
              delivery_status: 'planned',
              reason_code: 'manual_retry',
              event_payload: { channel: 'email' },
              event_note: null,
              notification_queue_id: null,
              created_by_admin_user_id: 'admin_001',
              occurred_at: '2026-04-22T12:10:00Z',
              created_at: '2026-04-22T12:10:00Z',
            },
          ],
          queue_snapshot: null,
          source_summary: {
            source_kind: 'admin_manual_notification',
            source_id: 'notice_001',
            source_label: 'admin manual notification',
            source_status: null,
            owner_user_id: null,
            beneficiary_user_id: null,
            metadata: {},
          },
          lifecycle_events: [],
          troubleshooting_state: 'actionable_retry',
          customer_message_key: 'growth_notifications.delivery.retry_available',
          support_summary: 'Delivery failed and can be retried.',
        }),
      ),
      http.get(MATCH_ANY_API_ORIGIN.growthNotificationDeliveryExport, () =>
        new HttpResponse(JSON.stringify({ export_kind: 'growth_notification_delivery_forensics' }), {
          headers: {
            'Content-Type': 'application/json',
            'Content-Disposition': 'attachment; filename=\"growth-notification-delivery-delivery_email.json\"',
          },
        }),
      ),
    );

    const detailResponse = await growthApi.getGrowthNotificationDeliveryDetail('delivery_email');
    const exportResponse = await growthApi.exportGrowthNotificationDeliveryDetail('delivery_email');

    expect(detailResponse.status).toBe(200);
    expect(detailResponse.data.troubleshooting_state).toBe('actionable_retry');
    expect(detailResponse.data.event_timeline[0]?.event_type).toBe('admin_resend_requested');
    expect(exportResponse.status).toBe(200);
    expect(exportResponse.headers['content-disposition']).toContain('attachment; filename=');
    expect(exportResponse.data).toBeInstanceOf(Blob);
  });

  it('looks up growth codes with operator context', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.growthCodeLookup, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          accepted: false,
          code_type: 'invite',
          action_context: 'checkout',
          result: 'rejected',
          reject_reason: 'code_wrong_context',
          conflict_code: null,
          wrong_context_target: 'redeem',
          issuer_type: 'admin',
          owner_type: 'customer',
          resolved_code_id: 'invite_001',
          growth_code_id: 'growth_001',
          promo_code_id: null,
          partner_code_id: null,
          user_message_key: 'growth_codes.invite.redeem_required',
        });
      }),
    );

    const response = await growthApi.lookupGrowthCode({
      code: 'INVITE-AAA',
      action_context: 'checkout',
      lookup_user_id: 'c6ef42b0-1cc0-4ea2-a3dd-c4f689dc0d50',
      storefront_key: 'cybervpn-web',
      plan_id: 'plan_001',
      amount: 79,
      channel: 'web',
    });

    expect(response.status).toBe(200);
    expect(response.data.reject_reason).toBe('code_wrong_context');
    expect(response.data.wrong_context_target).toBe('redeem');
    expect(capturedBody).toMatchObject({
      code: 'INVITE-AAA',
      action_context: 'checkout',
      storefront_key: 'cybervpn-web',
      amount: 79,
    });
  });

  it('lists admin promo codes with operational fields', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.promoCodes, () =>
        HttpResponse.json([
          {
            id: 'promo_001',
            code: 'SPRING25',
            discount_type: 'percent',
            discount_value: 25,
            currency: 'USD',
            max_uses: 100,
            current_uses: 10,
            is_single_use: false,
            is_active: true,
            expires_at: '2026-05-01T00:00:00Z',
            created_at: '2026-04-10T11:00:00Z',
          },
        ]),
      ),
    );

    const response = await growthApi.listPromos({ offset: 0, limit: 20 });

    expect(response.status).toBe(200);
    expect(response.data[0]?.code).toBe('SPRING25');
    expect(response.data[0]?.current_uses).toBe(10);
  });

  it('creates a promo code with advanced admin fields', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.promoCodes, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json(
          {
            id: 'promo_002',
            code: 'VIPFIXED',
            discount_type: 'fixed',
            discount_value: 15,
            currency: 'USD',
            max_uses: 50,
            current_uses: 0,
            is_single_use: true,
            is_active: true,
            expires_at: '2026-06-01T00:00:00Z',
            created_at: '2026-04-10T12:00:00Z',
          },
          { status: 201 },
        );
      }),
    );

    const response = await growthApi.createPromo({
      code: 'VIPFIXED',
      discount_type: 'fixed',
      discount_value: 15,
      max_uses: 50,
      is_single_use: true,
      plan_ids: ['plan_001'],
      min_amount: 25,
      expires_at: '2026-06-01T00:00:00Z',
      description: 'High-value segment',
      currency: 'USD',
    });

    expect(response.status).toBe(201);
    expect(response.data.code).toBe('VIPFIXED');
    expect(capturedBody).toMatchObject({
      code: 'VIPFIXED',
      discount_type: 'fixed',
      discount_value: 15,
      min_amount: 25,
      currency: 'USD',
    });
  });

  it('loads a single promo code detail', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.promoCodeById, ({ request }) => {
        const promoId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          id: promoId,
          code: 'FLASH50',
          discount_type: 'percent',
          discount_value: 50,
          currency: 'USD',
          max_uses: 10,
          current_uses: 3,
          is_single_use: false,
          is_active: true,
          expires_at: '2026-04-30T00:00:00Z',
          created_at: '2026-04-10T12:30:00Z',
        });
      }),
    );

    const response = await growthApi.getPromo('promo_003');

    expect(response.status).toBe(200);
    expect(response.data.id).toBe('promo_003');
    expect(response.data.code).toBe('FLASH50');
  });

  it('updates a promo code by id', async () => {
    let updatedId = '';
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.put(MATCH_ANY_API_ORIGIN.promoCodeById, async ({ request }) => {
        updatedId = new URL(request.url).pathname.split('/').at(-1) ?? '';
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          id: updatedId,
          code: 'SPRING25',
          discount_type: 'percent',
          discount_value: capturedBody.discount_value ?? 20,
          currency: 'USD',
          max_uses: capturedBody.max_uses ?? 100,
          current_uses: 15,
          is_single_use: false,
          is_active: capturedBody.is_active ?? true,
          expires_at: capturedBody.expires_at ?? null,
          created_at: '2026-04-10T12:40:00Z',
        });
      }),
    );

    const response = await growthApi.updatePromo('promo_004', {
      discount_value: 30,
      max_uses: 250,
      expires_at: '2026-07-01T00:00:00Z',
      description: 'Extended campaign',
      is_active: true,
    });

    expect(response.status).toBe(200);
    expect(updatedId).toBe('promo_004');
    expect(capturedBody).toMatchObject({
      discount_value: 30,
      max_uses: 250,
      is_active: true,
    });
  });

  it('deactivates a promo code by id', async () => {
    let deactivatedId = '';

    server.use(
      http.delete(MATCH_ANY_API_ORIGIN.promoCodeById, ({ request }) => {
        deactivatedId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          id: deactivatedId,
          code: 'LEGACY10',
          discount_type: 'percent',
          discount_value: 10,
          currency: 'USD',
          max_uses: null,
          current_uses: 99,
          is_single_use: false,
          is_active: false,
          expires_at: null,
          created_at: '2026-04-10T13:00:00Z',
        });
      }),
    );

    const response = await growthApi.deactivatePromo('promo_005');

    expect(response.status).toBe(200);
    expect(deactivatedId).toBe('promo_005');
    expect(response.data.is_active).toBe(false);
  });
});

describe('growthApi invite and partner operations', () => {
  it('lists admin gift codes with pagination and owner filters', async () => {
    let capturedQuery = '';

    server.use(
      http.get(MATCH_ANY_API_ORIGIN.giftCodes, ({ request }) => {
        capturedQuery = new URL(request.url).search;
        return HttpResponse.json({
          items: [
            {
              id: 'gift_001',
              masked_code: 'ABCD••••',
              raw_code: 'GIFT-AAA',
              status: 'active',
              issuer_type: 'admin',
              source_type: 'admin_manual_gift',
              owner_user_id: 'user_001',
              plan_family: 'max',
              duration_days: 365,
              recipient_hint: 'friend@example.com',
              created_at: '2026-04-21T10:00:00Z',
              redeemed_at: null,
            },
          ],
          total: 12,
          offset: 0,
          limit: 20,
        });
      }),
    );

    const response = await growthApi.listGiftCodes({
      owner_user_id: 'user_001',
      offset: 0,
      limit: 20,
    });

    expect(response.status).toBe(200);
    expect(response.data.total).toBe(12);
    expect(response.data.items[0]?.raw_code).toBe('GIFT-AAA');
    expect(capturedQuery).toContain('owner_user_id=user_001');
  });

  it('issues an admin gift code with recipient context', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.giftCodesIssue, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            gift_code: {
              id: 'gift_002',
              masked_code: 'EFGH••••',
              raw_code: 'GIFT-BBB',
              status: 'active',
              issuer_type: 'admin',
              source_type: 'admin_manual_gift',
              owner_user_id: 'user_002',
              plan_family: 'pro',
              duration_days: 180,
              recipient_hint: 'ops@example.com',
              gift_message: 'Support recovery',
              created_at: '2026-04-21T12:00:00Z',
            },
          },
          { status: 201 },
        );
      }),
    );

    const response = await growthApi.issueGiftCode({
      owner_user_id: 'user_002',
      plan_id: 'plan_002',
      recipient_hint: 'ops@example.com',
      gift_message: 'Support recovery',
      reason_code: 'support_compensation',
      admin_note: 'Issued after service incident',
    });

    expect(response.status).toBe(201);
    expect(response.data.gift_code.raw_code).toBe('GIFT-BBB');
    expect(capturedBody).toMatchObject({
      owner_user_id: 'user_002',
      plan_id: 'plan_002',
      reason_code: 'support_compensation',
    });
  });

  it('issues an admin gift code batch with shared owner context', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.giftCodeBatchesIssue, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            batch_id: 'batch_001',
            issued_count: 2,
            gift_codes: [
              {
                id: 'gift_003',
                masked_code: 'BATCH••••',
                raw_code: 'GIFT-BATCH-1',
                batch_id: 'batch_001',
                status: 'active',
                issuer_type: 'admin',
                source_type: 'admin_gift_batch',
                owner_user_id: 'user_003',
                plan_family: 'max',
                duration_days: 365,
                created_at: '2026-04-21T13:00:00Z',
              },
              {
                id: 'gift_004',
                masked_code: 'BATCH••••',
                raw_code: 'GIFT-BATCH-2',
                batch_id: 'batch_001',
                status: 'active',
                issuer_type: 'admin',
                source_type: 'admin_gift_batch',
                owner_user_id: 'user_003',
                plan_family: 'max',
                duration_days: 365,
                created_at: '2026-04-21T13:00:00Z',
              },
            ],
          },
          { status: 201 },
        );
      }),
    );

    const response = await growthApi.issueGiftCodeBatch({
      owner_user_id: 'user_003',
      plan_id: 'plan_003',
      count: 2,
      recipient_hint: 'batch@example.com',
      reason_code: 'campaign_batch',
    });

    expect(response.status).toBe(201);
    expect(response.data.issued_count).toBe(2);
    expect(response.data.batch_id).toBe('batch_001');
    expect(response.data.gift_codes[0]?.batch_id).toBe('batch_001');
    expect(capturedBody).toMatchObject({
      owner_user_id: 'user_003',
      plan_id: 'plan_003',
      count: 2,
      reason_code: 'campaign_batch',
    });
  });

  it('creates a batch of invite codes for a target user', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.inviteCodes, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json(
          [
            {
              id: 'invite_001',
              code: 'INVITE-AAA',
              free_days: 14,
              is_used: false,
              expires_at: '2026-05-10T00:00:00Z',
              created_at: '2026-04-10T13:30:00Z',
            },
            {
              id: 'invite_002',
              code: 'INVITE-BBB',
              free_days: 14,
              is_used: false,
              expires_at: '2026-05-10T00:00:00Z',
              created_at: '2026-04-10T13:30:00Z',
            },
          ],
          { status: 201 },
        );
      }),
    );

    const response = await growthApi.createInviteCodes({
      user_id: 'c6ef42b0-1cc0-4ea2-a3dd-c4f689dc0d50',
      free_days: 14,
      count: 2,
      plan_id: 'plan_001',
    });

    expect(response.status).toBe(201);
    expect(response.data).toHaveLength(2);
    expect(capturedBody).toMatchObject({
      free_days: 14,
      count: 2,
      plan_id: 'plan_001',
    });
  });

  it('promotes a mobile user to partner status', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.partnerPromote, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          status: 'promoted',
          user_id: capturedBody.user_id,
        });
      }),
    );

    const response = await growthApi.promotePartner({
      user_id: 'd57c2fb8-25f0-4411-9c17-045a7ab7bb10',
    });

    expect(response.status).toBe(200);
    expect(response.data).toMatchObject({
      status: 'promoted',
      user_id: 'd57c2fb8-25f0-4411-9c17-045a7ab7bb10',
    });
    expect(capturedBody).toMatchObject({
      user_id: 'd57c2fb8-25f0-4411-9c17-045a7ab7bb10',
    });
  });

  it('creates a partner workspace from the admin growth surface', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.partnerWorkspaces, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json(
          {
            id: 'workspace_001',
            account_key: 'nebula-partners',
            display_name: 'Nebula Partners',
            status: 'active',
            legacy_owner_user_id: null,
            created_by_admin_user_id: 'admin_001',
            code_count: 0,
            active_code_count: 0,
            total_clients: 0,
            total_earned: 0,
            last_activity_at: null,
            current_role_key: null,
            current_permission_keys: [],
            members: [],
          },
          { status: 201 },
        );
      }),
    );

    const response = await growthApi.createPartnerWorkspace({
      display_name: 'Nebula Partners',
      owner_admin_user_id: '0d2f4a94-72a2-4b84-91f9-f7814d11b201',
    });

    expect(response.status).toBe(201);
    expect(response.data.account_key).toBe('nebula-partners');
    expect(capturedBody).toMatchObject({
      display_name: 'Nebula Partners',
      owner_admin_user_id: '0d2f4a94-72a2-4b84-91f9-f7814d11b201',
    });
  });

  it('loads a single partner workspace detail', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.partnerWorkspaceDetail, ({ request }) => {
        const workspaceId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          id: workspaceId,
          account_key: 'aurora-ops',
          display_name: 'Aurora Ops',
          status: 'active',
          legacy_owner_user_id: null,
          created_by_admin_user_id: 'admin_001',
          code_count: 4,
          active_code_count: 3,
          total_clients: 28,
          total_earned: 1240.5,
          last_activity_at: '2026-04-17T18:45:00Z',
          current_role_key: null,
          current_permission_keys: [],
          members: [
            {
              id: 'membership_001',
              admin_user_id: 'admin_partner_001',
              role_id: 'role_owner',
              role_key: 'owner',
              role_display_name: 'Owner',
              membership_status: 'active',
              permission_keys: ['workspace_read', 'membership_write'],
              invited_by_admin_user_id: 'admin_001',
              created_at: '2026-04-17T18:00:00Z',
              updated_at: '2026-04-17T18:00:00Z',
            },
          ],
        });
      }),
    );

    const response = await growthApi.getPartnerWorkspace('workspace_002');

    expect(response.status).toBe(200);
    expect(response.data.id).toBe('workspace_002');
    expect(response.data.members[0]?.role_key).toBe('owner');
    expect(response.data.total_clients).toBe(28);
  });

  it('loads referral overview metrics for admin analytics', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.referralOverview, () =>
        HttpResponse.json({
          total_commissions: 42,
          total_earned: 1350.5,
          unique_referrers: 12,
          unique_referred_users: 31,
          recent_commissions: [],
          top_referrers: [],
        }),
      ),
    );

    const response = await growthApi.getReferralOverview();

    expect(response.status).toBe(200);
    expect(response.data.total_commissions).toBe(42);
    expect(response.data.unique_referrers).toBe(12);
  });

  it('loads referral detail for a specific mobile user', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.referralUserDetail, ({ request }) => {
        const userId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          user: {
            id: userId,
            email: 'referrer@example.com',
            username: 'referrer',
            telegram_username: 'referrer_tg',
            referral_code: 'REF-001',
            is_partner: false,
          },
          referred_by_user_id: null,
          commission_count: 3,
          referred_users: 2,
          total_earned: 18.75,
          recent_commissions: [],
        });
      }),
    );

    const response = await growthApi.getReferralUserDetail('d57c2fb8-25f0-4411-9c17-045a7ab7bb10');

    expect(response.status).toBe(200);
    expect(response.data.user.email).toBe('referrer@example.com');
    expect(response.data.commission_count).toBe(3);
  });

  it('lists partners from the admin directory', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.partners, () =>
        HttpResponse.json({
          items: [
            {
              user: {
                id: '6bf366e0-5c78-4472-b0f2-3f1f577d1122',
                email: 'partner@example.com',
                username: 'partner',
                telegram_username: 'partner_tg',
                referral_code: 'PARTNER-01',
                is_partner: true,
              },
              promoted_at: '2026-04-10T13:00:00Z',
              code_count: 4,
              active_code_count: 3,
              total_clients: 7,
              total_earned: 250.25,
              last_activity_at: '2026-04-10T14:00:00Z',
            },
          ],
          total: 1,
          offset: 0,
          limit: 50,
        }),
      ),
    );

    const response = await growthApi.listPartners({ offset: 0, limit: 50 });

    expect(response.status).toBe(200);
    expect(response.data.total).toBe(1);
    expect(response.data.items[0]?.user.email).toBe('partner@example.com');
  });

  it('loads partner drill-down data with codes and recent earnings', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.partnerDetail, ({ request }) => {
        const userId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          user: {
            id: userId,
            email: 'partner@example.com',
            username: 'partner',
            telegram_username: 'partner_tg',
            referral_code: 'PARTNER-01',
            is_partner: true,
          },
          promoted_at: '2026-04-10T13:00:00Z',
          code_count: 4,
          active_code_count: 3,
          total_clients: 7,
          total_earned: 250.25,
          last_activity_at: '2026-04-10T14:00:00Z',
          codes: [
            {
              id: '7c6bdb40-4b63-42dc-a59a-e8e8440abf2d',
              code: 'PARTNER-CODE',
              markup_pct: 15,
              is_active: true,
              created_at: '2026-04-10T13:00:00Z',
              updated_at: '2026-04-10T13:00:00Z',
            },
          ],
          recent_earnings: [],
        });
      }),
    );

    const response = await growthApi.getPartnerDetail('6bf366e0-5c78-4472-b0f2-3f1f577d1122');

    expect(response.status).toBe(200);
    expect(response.data.codes[0]?.code).toBe('PARTNER-CODE');
    expect(response.data.total_earned).toBe(250.25);
  });
});
