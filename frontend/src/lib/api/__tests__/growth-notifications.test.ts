import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { growthNotificationsApi } from '../growth-notifications';

const API_BASE = '*/api/v1';

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('growthNotificationsApi', () => {
  it('lists active growth notifications for the current user', async () => {
    server.use(
      http.get(`${API_BASE}/growth-notifications`, () =>
        HttpResponse.json([
          {
            id: 'invite-issued:invite-1',
            kind: 'invite_issued',
            tone: 'info',
            route_slug: '/referral',
            title: 'Invite ready to share',
            message: 'Your account received an invite code for 14 free days.',
            notes: ['Source: plan purchase.'],
            action_required: true,
            unread: true,
            created_at: '2026-04-22T09:00:00Z',
          },
        ]),
      ),
    );

    const response = await growthNotificationsApi.list();

    expect(response.status).toBe(200);
    expect(response.data[0]?.kind).toBe('invite_issued');
    expect(response.data[0]?.unread).toBe(true);
  });

  it('loads growth notification counters', async () => {
    server.use(
      http.get(`${API_BASE}/growth-notifications/counters`, () =>
        HttpResponse.json({
          total_notifications: 3,
          unread_notifications: 2,
          action_required_notifications: 1,
        }),
      ),
    );

    const response = await growthNotificationsApi.getCounters();

    expect(response.status).toBe(200);
    expect(response.data).toEqual({
      total_notifications: 3,
      unread_notifications: 2,
      action_required_notifications: 1,
    });
  });

  it('marks a notification as read', async () => {
    server.use(
      http.post(`${API_BASE}/growth-notifications/invite-issued:invite-1/read`, () =>
        HttpResponse.json({
          notification_id: 'invite-issued:invite-1',
          read_at: '2026-04-22T10:00:00Z',
          archived_at: null,
        }),
      ),
    );

    const response = await growthNotificationsApi.markRead('invite-issued:invite-1');

    expect(response.status).toBe(200);
    expect(response.data.notification_id).toBe('invite-issued:invite-1');
    expect(response.data.read_at).toBe('2026-04-22T10:00:00Z');
  });

  it('archives a notification', async () => {
    server.use(
      http.post(`${API_BASE}/growth-notifications/gift-issued:gift-1/archive`, () =>
        HttpResponse.json({
          notification_id: 'gift-issued:gift-1',
          read_at: '2026-04-22T10:00:00Z',
          archived_at: '2026-04-22T11:00:00Z',
        }),
      ),
    );

    const response = await growthNotificationsApi.archive('gift-issued:gift-1');

    expect(response.status).toBe(200);
    expect(response.data.notification_id).toBe('gift-issued:gift-1');
    expect(response.data.archived_at).toBe('2026-04-22T11:00:00Z');
  });

  it('loads customer troubleshooting detail and requests recovery', async () => {
    server.use(
      http.get(`${API_BASE}/growth-notifications/admin-manual:note-1`, () =>
        HttpResponse.json({
          notification: {
            id: 'admin-manual:note-1',
            kind: 'admin_manual_update',
            tone: 'info',
            route_slug: '/referral',
            title: 'Account review update',
            message: 'Support issued a manual growth notice.',
            notes: ['Ticket: SUP-42'],
            action_required: false,
            unread: false,
            created_at: '2026-04-22T09:00:00Z',
            archived_at: null,
          },
          deliveries: [
            {
              delivery_id: 'delivery-email-1',
              delivery_channel: 'email',
              delivery_status: 'failed',
              troubleshooting_state: 'actionable_retry',
              customer_message_key: 'growth_notifications.delivery.retry_available',
              customer_summary: 'Email delivery failed. You can request another send.',
              recovery_allowed: true,
              support_required: false,
              planned_at: '2026-04-22T09:00:00Z',
              delivered_at: null,
              events: [
                {
                  event_type: 'email_failed',
                  occurred_at: '2026-04-22T09:05:00Z',
                  summary: 'Email delivery failed.',
                },
              ],
            },
          ],
          support_handoff: {
            reference_code: 'GROWTH::admin-manual:note-1',
            troubleshooting_summary: 'Email: actionable_retry',
            copy_text: 'Reference: GROWTH::admin-manual:note-1',
          },
        }),
      ),
      http.post(`${API_BASE}/growth-notifications/admin-manual:note-1/recovery`, async ({ request }) => {
        const body = (await request.json()) as { delivery_channel: string };
        expect(body.delivery_channel).toBe('email');
        return HttpResponse.json({
          notification: {
            id: 'admin-manual:note-1',
            kind: 'admin_manual_update',
            tone: 'info',
            route_slug: '/referral',
            title: 'Account review update',
            message: 'Support issued a manual growth notice.',
            notes: [],
            action_required: false,
            unread: false,
            created_at: '2026-04-22T09:00:00Z',
            archived_at: null,
          },
          deliveries: [
            {
              delivery_id: 'delivery-email-1',
              delivery_channel: 'email',
              delivery_status: 'planned',
              troubleshooting_state: 'in_progress',
              customer_message_key: 'growth_notifications.delivery.pending',
              customer_summary: 'Email delivery is still in progress.',
              recovery_allowed: false,
              support_required: false,
              planned_at: '2026-04-22T09:10:00Z',
              delivered_at: null,
              events: [],
            },
          ],
          support_handoff: {
            reference_code: 'GROWTH::admin-manual:note-1',
            troubleshooting_summary: 'Email: in_progress',
            copy_text: 'Reference: GROWTH::admin-manual:note-1',
          },
        });
      }),
    );

    const detailResponse = await growthNotificationsApi.getDetail('admin-manual:note-1');
    expect(detailResponse.status).toBe(200);
    expect(detailResponse.data.deliveries[0]?.troubleshooting_state).toBe('actionable_retry');

    const recoveryResponse = await growthNotificationsApi.requestRecovery('admin-manual:note-1', {
      delivery_channel: 'email',
    });
    expect(recoveryResponse.status).toBe(200);
    expect(recoveryResponse.data.deliveries[0]?.delivery_status).toBe('planned');
  });

  it('requests structured support escalation for blocked delivery flows', async () => {
    server.use(
      http.post(
        `${API_BASE}/growth-notifications/admin-manual:note-1/support-escalation`,
        async ({ request }) => {
          const body = (await request.json()) as {
            delivery_channel: string | null;
            escalation_channel: string;
          };
          expect(body.delivery_channel).toBe('email');
          expect(body.escalation_channel).toBe('support_email');
          return HttpResponse.json({
            notification: {
              id: 'admin-manual:note-1',
              kind: 'admin_manual_update',
              tone: 'warning',
              route_slug: '/referral',
              title: 'Account review update',
              message: 'Support issued a manual growth notice.',
              notes: ['Ticket: SUP-42'],
              action_required: false,
              unread: false,
              created_at: '2026-04-22T09:00:00Z',
              archived_at: null,
            },
            deliveries: [
              {
                delivery_id: 'delivery-email-1',
                delivery_channel: 'email',
                delivery_status: 'paused',
                troubleshooting_state: 'paused_admin',
                customer_message_key: 'growth_notifications.delivery.support_review',
                customer_summary: 'Email delivery paused pending support review.',
                recovery_allowed: false,
                support_required: true,
                planned_at: '2026-04-22T09:00:00Z',
                delivered_at: null,
                repair_target: {
                  kind: 'support_contact',
                  summary: 'Support must review this delivery before it can be retried.',
                },
                events: [],
              },
            ],
            support_handoff: {
              reference_code: 'GROWTH::admin-manual:note-1',
              troubleshooting_summary: 'Email delivery paused pending review.',
              copy_text: 'Reference: GROWTH::admin-manual:note-1',
              suggested_escalation_channel: 'support_email',
              contact_subject: '[GROWTH::admin-manual:note-1] Growth delivery issue',
              contact_body: 'Reference: GROWTH::admin-manual:note-1',
            },
          });
        },
      ),
    );

    const response = await growthNotificationsApi.requestSupportEscalation(
      'admin-manual:note-1',
      {
        delivery_channel: 'email',
        escalation_channel: 'support_email',
      },
    );

    expect(response.status).toBe(200);
    expect(response.data.support_handoff.suggested_escalation_channel).toBe('support_email');
    expect(response.data.deliveries[0]?.support_required).toBe(true);
  });
});
