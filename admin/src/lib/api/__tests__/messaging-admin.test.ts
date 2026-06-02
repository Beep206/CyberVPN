import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { messagingApi } from '../messaging';

const API_BASE = '*/api/v1';

const MATCH_ANY_API_ORIGIN = {
  notificationBroadcasts: `${API_BASE}/admin/notifications/broadcasts`,
  notificationBroadcastCancel: `${API_BASE}/admin/notifications/broadcasts/:campaignRef/cancel`,
};

function buildBroadcastCampaign(overrides: Record<string, unknown> = {}) {
  return {
    action_url: '/status',
    audience_filter: {
      customer_account_ids: ['8ef69814-83a8-4591-b3d4-9f749cbd0001'],
      estimated_recipient_count: 1,
    },
    audience_type: 'explicit_customers',
    body: 'Synthetic maintenance notice.',
    created_at: '2026-06-01T10:00:00Z',
    created_by_admin_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
    id: '8ef69814-83a8-4591-b3d4-9f749cbd0101',
    name: 'Maintenance notice',
    public_id: 'broadcast_20260601_0001',
    scheduled_at: null,
    status: 'draft',
    title: 'Maintenance',
    updated_at: '2026-06-01T10:00:00Z',
    ...overrides,
  };
}

describe('messagingApi notification broadcast operations', () => {
  it('creates and cancels an admin notification broadcast campaign', async () => {
    let capturedCreateBody: Record<string, unknown> | null = null;
    let capturedCancelRef = '';

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.notificationBroadcasts, async ({ request }) => {
        capturedCreateBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(buildBroadcastCampaign(), { status: 201 });
      }),
      http.post(MATCH_ANY_API_ORIGIN.notificationBroadcastCancel, ({ params }) => {
        capturedCancelRef = String(params.campaignRef);
        return HttpResponse.json(buildBroadcastCampaign({ status: 'cancelled' }));
      }),
    );

    const createResponse = await messagingApi.createAdminNotificationBroadcast({
      action_url: '/status',
      audience_filter: {
        customer_account_ids: ['8ef69814-83a8-4591-b3d4-9f749cbd0001'],
        estimated_recipient_count: 1,
      },
      audience_type: 'explicit_customers',
      body: 'Synthetic maintenance notice.',
      name: 'Maintenance notice',
      scheduled_at: null,
      title: 'Maintenance',
    });
    const cancelResponse = await messagingApi.cancelAdminNotificationBroadcast(
      createResponse.data.public_id,
    );

    expect(createResponse.status).toBe(201);
    expect(createResponse.data.status).toBe('draft');
    expect(cancelResponse.data.status).toBe('cancelled');
    expect(capturedCancelRef).toBe('broadcast_20260601_0001');
    expect(capturedCreateBody).toMatchObject({
      audience_filter: {
        customer_account_ids: ['8ef69814-83a8-4591-b3d4-9f749cbd0001'],
        estimated_recipient_count: 1,
      },
      audience_type: 'explicit_customers',
      title: 'Maintenance',
    });
  });
});
