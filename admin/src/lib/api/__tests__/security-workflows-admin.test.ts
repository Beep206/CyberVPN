import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { securityApi } from '../security';

const API_BASE = '*/api/v1';

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('securityApi review queue workflows', () => {
  it('lists the canonical risk review queue', async () => {
    server.use(
      http.get(`${API_BASE}/security/risk-reviews/queue`, () =>
        HttpResponse.json([
          {
            review: {
              id: 'review-1',
              risk_subject_id: 'subject-1',
              review_type: 'payout_review',
              status: 'open',
              decision: 'hold',
              reason: 'Investigate payout',
              evidence: {},
              created_by_admin_user_id: null,
              resolved_by_admin_user_id: null,
              resolved_at: null,
              created_at: '2026-04-19T08:00:00Z',
              updated_at: '2026-04-19T08:00:00Z',
            },
            subject: {
              id: 'subject-1',
              principal_class: 'customer',
              principal_subject: 'customer-001',
              auth_realm_id: null,
              storefront_id: null,
              status: 'active',
              risk_level: 'high',
              metadata: {},
              created_at: '2026-04-18T08:00:00Z',
              updated_at: '2026-04-19T08:00:00Z',
            },
            attachment_count: 1,
            governance_action_count: 2,
          },
        ]),
      ),
    );

    const response = await securityApi.listRiskReviewQueue({ status: 'open', limit: 10, offset: 0 });

    expect(response.status).toBe(200);
    expect(response.data[0]?.review.review_type).toBe('payout_review');
    expect(response.data[0]?.governance_action_count).toBe(2);
  });

  it('loads, annotates, and resolves a selected review', async () => {
    let attachmentBody: Record<string, unknown> | null = null;
    let resolveBody: Record<string, unknown> | null = null;

    server.use(
      http.get(`${API_BASE}/security/risk-reviews/:reviewId`, ({ params }) =>
        HttpResponse.json({
          review: {
            id: params.reviewId,
            risk_subject_id: 'subject-1',
            review_type: 'payout_review',
            status: 'open',
            decision: 'hold',
            reason: 'Investigate payout',
            evidence: {},
            created_by_admin_user_id: null,
            resolved_by_admin_user_id: null,
            resolved_at: null,
            created_at: '2026-04-19T08:00:00Z',
            updated_at: '2026-04-19T08:00:00Z',
          },
          subject: {
            id: 'subject-1',
            principal_class: 'customer',
            principal_subject: 'customer-001',
            auth_realm_id: null,
            storefront_id: null,
            status: 'active',
            risk_level: 'high',
            metadata: {},
            created_at: '2026-04-18T08:00:00Z',
            updated_at: '2026-04-19T08:00:00Z',
          },
          attachments: [],
          governance_actions: [],
        }),
      ),
      http.post(`${API_BASE}/security/risk-reviews/:reviewId/attachments`, async ({ request }) => {
        attachmentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'attachment-1',
          risk_review_id: 'review-1',
          attachment_type: 'document',
          storage_key: 'risk/reviews/evidence/file.pdf',
          file_name: 'file.pdf',
          metadata: { content_type: 'application/pdf' },
          created_by_admin_user_id: null,
          created_at: '2026-04-19T08:10:00Z',
        }, { status: 201 });
      }),
      http.post(`${API_BASE}/security/risk-reviews/:reviewId/resolve`, async ({ request }) => {
        resolveBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'review-1',
          risk_subject_id: 'subject-1',
          review_type: 'payout_review',
          status: 'resolved',
          decision: 'block',
          reason: 'Investigate payout',
          evidence: {},
          created_by_admin_user_id: null,
          resolved_by_admin_user_id: null,
          resolved_at: '2026-04-19T08:11:00Z',
          created_at: '2026-04-19T08:00:00Z',
          updated_at: '2026-04-19T08:11:00Z',
        });
      }),
    );

    const detailResponse = await securityApi.getRiskReview('review-1');
    const attachmentResponse = await securityApi.attachRiskReviewAttachment('review-1', {
      attachment_type: 'document',
      storage_key: 'risk/reviews/evidence/file.pdf',
      file_name: 'file.pdf',
      metadata: { content_type: 'application/pdf' },
    });
    const resolveResponse = await securityApi.resolveRiskReview('review-1', {
      decision: 'block',
      resolution_status: 'resolved',
      resolution_reason: 'Block payout',
      resolution_evidence: { source: 'ops' },
    });

    expect(detailResponse.status).toBe(200);
    expect(detailResponse.data.subject.id).toBe('subject-1');
    expect(attachmentResponse.status).toBe(201);
    expect(attachmentBody).toMatchObject({
      attachment_type: 'document',
      storage_key: 'risk/reviews/evidence/file.pdf',
    });
    expect(resolveResponse.status).toBe(200);
    expect(resolveBody).toMatchObject({
      decision: 'block',
      resolution_status: 'resolved',
      resolution_reason: 'Block payout',
    });
  });

  it('records governance actions for the selected review subject', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`${API_BASE}/security/governance-actions`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'action-1',
          risk_subject_id: 'subject-1',
          risk_review_id: 'review-1',
          action_type: 'payout_freeze',
          status: 'applied',
          target_type: 'partner_payout_account',
          target_ref: 'ppa_001',
          reason: 'Freeze during investigation',
          payload: { scope: 'review' },
          created_by_admin_user_id: null,
          applied_by_admin_user_id: null,
          applied_at: null,
          created_at: '2026-04-19T08:10:00Z',
          updated_at: '2026-04-19T08:10:00Z',
        }, { status: 201 });
      }),
    );

    const response = await securityApi.createGovernanceAction({
      risk_subject_id: 'subject-1',
      risk_review_id: 'review-1',
      action_type: 'payout_freeze',
      reason: 'Freeze during investigation',
      target_type: 'partner_payout_account',
      target_ref: 'ppa_001',
      payload: { scope: 'review' },
      apply_now: true,
    });

    expect(response.status).toBe(201);
    expect(response.data.action_type).toBe('payout_freeze');
    expect(capturedBody).toMatchObject({
      risk_subject_id: 'subject-1',
      risk_review_id: 'review-1',
      apply_now: true,
    });
  });
});
