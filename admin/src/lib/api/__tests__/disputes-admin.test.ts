import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { disputesApi } from '../disputes';

const API_BASE = '*/api/v1';

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('disputesApi canonical dispute case workflows', () => {
  it('lists dispute cases scoped to a payment dispute', async () => {
    server.use(
      http.get(`${API_BASE}/dispute-cases`, () =>
        HttpResponse.json([
          {
            id: 'case-1',
            partner_account_id: 'workspace-1',
            payment_dispute_id: 'dispute-1',
            order_id: 'order-1',
            case_kind: 'evidence_collection',
            case_status: 'waiting_on_ops',
            summary: 'Collect issuer evidence',
            payload: {},
            notes: ['initial note'],
            opened_by_admin_user_id: null,
            assigned_to_admin_user_id: null,
            closed_by_admin_user_id: null,
            closed_at: null,
            created_at: '2026-04-19T08:00:00Z',
            updated_at: '2026-04-19T08:00:00Z',
          },
        ]),
      ),
    );

    const response = await disputesApi.listDisputeCases({ payment_dispute_id: 'dispute-1' });

    expect(response.status).toBe(200);
    expect(response.data[0]?.case_status).toBe('waiting_on_ops');
  });

  it('creates a canonical dispute case overlay', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`${API_BASE}/dispute-cases`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          id: 'case-2',
          partner_account_id: 'workspace-1',
          payment_dispute_id: 'dispute-1',
          order_id: 'order-1',
          case_kind: 'evidence_collection',
          case_status: 'waiting_on_ops',
          summary: 'Collect issuer evidence',
          payload: { provider: 'stripe' },
          notes: ['Need receipt'],
          opened_by_admin_user_id: null,
          assigned_to_admin_user_id: null,
          closed_by_admin_user_id: null,
          closed_at: null,
          created_at: '2026-04-19T08:00:00Z',
          updated_at: '2026-04-19T08:00:00Z',
        }, { status: 201 });
      }),
    );

    const response = await disputesApi.createDisputeCase({
      partner_account_id: 'workspace-1',
      payment_dispute_id: 'dispute-1',
      order_id: 'order-1',
      case_kind: 'evidence_collection',
      case_status: 'waiting_on_ops',
      summary: 'Collect issuer evidence',
      case_payload: { provider: 'stripe' },
      notes: ['Need receipt'],
      assigned_to_admin_user_id: null,
    });

    expect(response.status).toBe(201);
    expect(response.data.id).toBe('case-2');
    expect(capturedBody).toMatchObject({
      partner_account_id: 'workspace-1',
      payment_dispute_id: 'dispute-1',
      case_kind: 'evidence_collection',
      case_status: 'waiting_on_ops',
    });
  });
});
