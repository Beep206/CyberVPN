import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SecurityReviewQueueConsole } from '../security-review-queue-console';

const {
  mockSession,
  mockListRiskReviewQueue,
  mockGetRiskReview,
  mockAttachRiskReviewAttachment,
  mockCreateGovernanceAction,
  mockResolveRiskReview,
} = vi.hoisted(() => ({
  mockSession: vi.fn(),
  mockListRiskReviewQueue: vi.fn(),
  mockGetRiskReview: vi.fn(),
  mockAttachRiskReviewAttachment: vi.fn(),
  mockCreateGovernanceAction: vi.fn(),
  mockResolveRiskReview: vi.fn(),
}));

vi.mock('@/lib/api/auth', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/auth')>('@/lib/api/auth');
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      session: (...args: unknown[]) => mockSession(...args),
    },
  };
});

vi.mock('@/lib/api/security', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/security')>('@/lib/api/security');
  return {
    ...actual,
    securityApi: {
      ...actual.securityApi,
      listRiskReviewQueue: (...args: unknown[]) => mockListRiskReviewQueue(...args),
      getRiskReview: (...args: unknown[]) => mockGetRiskReview(...args),
      attachRiskReviewAttachment: (...args: unknown[]) => mockAttachRiskReviewAttachment(...args),
      createGovernanceAction: (...args: unknown[]) => mockCreateGovernanceAction(...args),
      resolveRiskReview: (...args: unknown[]) => mockResolveRiskReview(...args),
    },
  };
});

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

describe('SecurityReviewQueueConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSession.mockResolvedValue({
      data: {
        id: '62cf4dca-c181-4b12-9ab8-ef1d9da9085b',
        email: 'admin@example.com',
        role: 'admin',
        is_active: true,
        is_email_verified: true,
        created_at: '2026-04-19T08:00:00Z',
      },
    });
    mockListRiskReviewQueue.mockResolvedValue({
      data: [
        {
          review: {
            id: 'review-1',
            risk_subject_id: 'subject-1',
            review_type: 'payout_review',
            status: 'open',
            decision: 'hold',
            reason: 'Investigate payout before release',
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
          governance_action_count: 1,
        },
      ],
    });
    mockGetRiskReview.mockResolvedValue({
      data: {
        review: {
          id: 'review-1',
          risk_subject_id: 'subject-1',
          review_type: 'payout_review',
          status: 'open',
          decision: 'hold',
          reason: 'Investigate payout before release',
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
        attachments: [
          {
            id: 'attachment-1',
            risk_review_id: 'review-1',
            attachment_type: 'document',
            storage_key: 'risk/reviews/evidence/file.pdf',
            file_name: 'file.pdf',
            metadata: { content_type: 'application/pdf' },
            created_by_admin_user_id: null,
            created_at: '2026-04-19T08:05:00Z',
          },
        ],
        governance_actions: [
          {
            id: 'action-1',
            risk_subject_id: 'subject-1',
            risk_review_id: 'review-1',
            action_type: 'payout_freeze',
            status: 'applied',
            target_type: 'partner_payout_account',
            target_ref: 'ppa_001',
            reason: 'Keep payout frozen during investigation',
            payload: {},
            created_by_admin_user_id: null,
            applied_by_admin_user_id: null,
            applied_at: null,
            created_at: '2026-04-19T08:05:00Z',
            updated_at: '2026-04-19T08:05:00Z',
          },
        ],
      },
    });
    mockAttachRiskReviewAttachment.mockResolvedValue({
      data: {
        id: 'attachment-2',
        risk_review_id: 'review-1',
        attachment_type: 'document',
        storage_key: 'risk/reviews/evidence/new-file.pdf',
        file_name: 'new-file.pdf',
        metadata: { content_type: 'application/pdf' },
        created_by_admin_user_id: null,
        created_at: '2026-04-19T08:10:00Z',
      },
    });
    mockCreateGovernanceAction.mockResolvedValue({
      data: {
        id: 'action-2',
        risk_subject_id: 'subject-1',
        risk_review_id: 'review-1',
        action_type: 'manual_override',
        status: 'applied',
        target_type: null,
        target_ref: null,
        reason: 'Escalate to finance review',
        payload: {},
        created_by_admin_user_id: null,
        applied_by_admin_user_id: null,
        applied_at: null,
        created_at: '2026-04-19T08:10:00Z',
        updated_at: '2026-04-19T08:10:00Z',
      },
    });
    mockResolveRiskReview.mockResolvedValue({
      data: {
        id: 'review-1',
        risk_subject_id: 'subject-1',
        review_type: 'payout_review',
        status: 'resolved',
        decision: 'block',
        reason: 'Investigate payout before release',
        evidence: {},
        created_by_admin_user_id: null,
        resolved_by_admin_user_id: null,
        resolved_at: '2026-04-19T08:15:00Z',
        created_at: '2026-04-19T08:00:00Z',
        updated_at: '2026-04-19T08:15:00Z',
      },
    });
  });

  it('renders the queue and submits attachment, governance, and resolve workflows', async () => {
    renderWithQueryClient(<SecurityReviewQueueConsole />);

    await waitFor(() => {
      expect(screen.getByText('reviewQueue.queue.title')).toBeInTheDocument();
    });

    fireEvent.change(
      screen.getByPlaceholderText('reviewQueue.attachments.fields.storageKeyPlaceholder'),
      {
        target: { value: 'risk/reviews/evidence/new-file.pdf' },
      },
    );
    fireEvent.change(
      screen.getByPlaceholderText('reviewQueue.attachments.fields.fileNamePlaceholder'),
      {
        target: { value: 'new-file.pdf' },
      },
    );
    fireEvent.click(screen.getByRole('button', { name: 'reviewQueue.attachments.submit' }));

    await waitFor(() => {
      expect(mockAttachRiskReviewAttachment).toHaveBeenCalledWith('review-1', {
        attachment_type: 'document',
        storage_key: 'risk/reviews/evidence/new-file.pdf',
        file_name: 'new-file.pdf',
        metadata: { content_type: 'application/pdf' },
      });
    });

    fireEvent.change(
      screen.getByPlaceholderText('reviewQueue.governance.fields.reasonPlaceholder'),
      {
        target: { value: 'Escalate to finance review' },
      },
    );
    fireEvent.click(screen.getByRole('button', { name: 'reviewQueue.governance.submit' }));

    await waitFor(() => {
      expect(mockCreateGovernanceAction).toHaveBeenCalledWith({
        risk_subject_id: 'subject-1',
        risk_review_id: 'review-1',
        action_type: 'payout_freeze',
        reason: 'Escalate to finance review',
        target_type: null,
        target_ref: null,
        payload: { scope: 'review' },
        apply_now: true,
      });
    });

    fireEvent.change(
      screen.getByPlaceholderText('reviewQueue.resolve.fields.reasonPlaceholder'),
      {
        target: { value: 'Block payout until finance signs off.' },
      },
    );
    fireEvent.click(screen.getByRole('button', { name: 'reviewQueue.resolve.submit' }));

    await waitFor(() => {
      expect(mockResolveRiskReview).toHaveBeenCalledWith('review-1', {
        decision: 'monitor',
        resolution_status: 'resolved',
        resolution_reason: 'Block payout until finance signs off.',
        resolution_evidence: { source: 'admin_review_queue' },
      });
    });
  });
});
