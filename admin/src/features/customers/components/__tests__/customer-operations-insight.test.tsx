import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CustomerOperationsInsight } from '../customer-operations-insight';
import type { AdminCustomerOperationsInsightResponse } from '@/lib/api/customers';

const {
  mockGetOperationsInsight,
  mockPerformOperationsAction,
  mockCreateDisputeCase,
  mockDownloadWorkspaceFinanceEvidence,
  mockDownloadPartnerStatementEvidence,
  mockDownloadPayoutInstructionEvidence,
  mockDownloadPayoutExecutionEvidence,
  mockDownloadBlobFile,
} = vi.hoisted(() => ({
  mockGetOperationsInsight: vi.fn(),
  mockPerformOperationsAction: vi.fn(),
  mockCreateDisputeCase: vi.fn(),
  mockDownloadWorkspaceFinanceEvidence: vi.fn(),
  mockDownloadPartnerStatementEvidence: vi.fn(),
  mockDownloadPayoutInstructionEvidence: vi.fn(),
  mockDownloadPayoutExecutionEvidence: vi.fn(),
  mockDownloadBlobFile: vi.fn(),
}));

vi.mock('@/lib/api/customers', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/customers')>('@/lib/api/customers');
  return {
    ...actual,
    customersApi: {
      ...actual.customersApi,
      getOperationsInsight: (...args: unknown[]) => mockGetOperationsInsight(...args),
      performOperationsAction: (...args: unknown[]) => mockPerformOperationsAction(...args),
      downloadWorkspaceFinanceEvidence: (...args: unknown[]) => mockDownloadWorkspaceFinanceEvidence(...args),
      downloadPartnerStatementEvidence: (...args: unknown[]) => mockDownloadPartnerStatementEvidence(...args),
      downloadPayoutInstructionEvidence: (...args: unknown[]) => mockDownloadPayoutInstructionEvidence(...args),
      downloadPayoutExecutionEvidence: (...args: unknown[]) => mockDownloadPayoutExecutionEvidence(...args),
    },
  };
});

vi.mock('@/lib/api/disputes', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/disputes')>('@/lib/api/disputes');
  return {
    ...actual,
    disputesApi: {
      ...actual.disputesApi,
      createDisputeCase: (...args: unknown[]) => mockCreateDisputeCase(...args),
    },
  };
});

vi.mock('@/shared/lib/download-file', () => ({
  downloadBlobFile: (...args: unknown[]) => mockDownloadBlobFile(...args),
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

function buildOperationsInsightResponse(
  overrides: Partial<AdminCustomerOperationsInsightResponse> = {},
): AdminCustomerOperationsInsightResponse {
  return {
    user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
    section_access: {
      explainability_visible: true,
      finance_visible: true,
      finance_actions_visible: true,
      risk_visible: true,
    },
    order_insights: [
      {
        order_explainability: {
          order: {
            id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
            settlement_status: 'paid',
            sale_channel: 'web',
            currency_code: 'USD',
            displayed_price: 99,
            commission_base_amount: 84,
            partner_code_id: '86cbb361-377e-4d3f-b6fd-319c52a74856',
            program_eligibility_policy_id: '9b1f69af-a8dd-4879-833f-7b7668b68f0c',
            created_at: '2026-04-18T12:00:00Z',
            updated_at: '2026-04-18T12:00:00Z',
          },
          commissionability_evaluation: {
            id: '9599d6f4-eaa6-4af7-b7df-363f75c53f4f',
            order_id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
            commissionability_status: 'eligible',
            reason_codes: ['phase6_admin_overlay'],
            partner_context_present: true,
            program_allows_commissionability: true,
            positive_commission_base: true,
            paid_status: true,
            fully_refunded: false,
            open_payment_dispute_present: false,
            risk_allowed: true,
            evaluation_snapshot: {},
            explainability_snapshot: {},
            evaluated_at: '2026-04-18T12:00:00Z',
            created_at: '2026-04-18T12:00:00Z',
            updated_at: '2026-04-18T12:00:00Z',
          },
          explainability: {
            commercial_resolution_summary: {
              resolved_partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
            },
          },
        },
        auth_realm_id: 'd6cc27a6-3560-4ca7-85f1-6c4f7ef39335',
        storefront_id: 'c3f4a9f0-9a7b-4dd6-8b32-48fa66014d23',
        attribution_result: {
          id: '4471ad54-10f8-4b7e-87e1-e4f5a470b61d',
          order_id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
          user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
          auth_realm_id: 'd6cc27a6-3560-4ca7-85f1-6c4f7ef39335',
          storefront_id: 'c3f4a9f0-9a7b-4dd6-8b32-48fa66014d23',
          owner_type: 'reseller',
          owner_source: 'persistent_reseller_binding',
          partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
          partner_code_id: '86cbb361-377e-4d3f-b6fd-319c52a74856',
          winning_touchpoint_id: null,
          winning_binding_id: null,
          rule_path: ['binding', 'workspace'],
          evidence_snapshot: {},
          explainability_snapshot: {},
          policy_snapshot: {},
          resolved_at: '2026-04-18T12:00:00Z',
          created_at: '2026-04-18T12:00:00Z',
        },
        payment_disputes: [],
        dispute_cases: [],
        resolved_partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
      },
    ],
    settlement_workspaces: [
      {
        partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
        payout_accounts: [
          {
            id: 'fa8f6898-ebf5-47ea-9ec0-304f825d8b2e',
            partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
            settlement_profile_id: null,
            payout_rail: 'bank_transfer',
            display_label: 'Primary USD Account',
            masked_destination: '****7890',
            destination_metadata: {},
            verification_status: 'verified',
            approval_status: 'approved',
            account_status: 'active',
            is_default: true,
            created_by_admin_user_id: null,
            verified_by_admin_user_id: null,
            verified_at: null,
            approved_by_admin_user_id: null,
            approved_at: null,
            suspended_by_admin_user_id: null,
            suspended_at: null,
            suspension_reason_code: null,
            archived_by_admin_user_id: null,
            archived_at: null,
            archive_reason_code: null,
            default_selected_by_admin_user_id: null,
            default_selected_at: null,
            created_at: '2026-04-18T12:00:00Z',
            updated_at: '2026-04-18T12:00:00Z',
          },
        ],
        payout_account_actions: {},
        payout_instruction_actions: {},
        partner_statements: [
          {
            id: '113bdbd9-8c12-46dd-a4d8-5fa54c9680cc',
            partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
            settlement_period_id: '15946f22-ccea-4c45-88d8-ab67a6ec6097',
            statement_key: 'stmt_customer_ops',
            statement_version: 1,
            statement_status: 'closed',
            reopened_from_statement_id: null,
            superseded_by_statement_id: null,
            currency_code: 'USD',
            accrual_amount: 25,
            on_hold_amount: 0,
            reserve_amount: 5,
            adjustment_net_amount: 0,
            available_amount: 20,
            source_event_count: 1,
            held_event_count: 0,
            active_reserve_count: 1,
            adjustment_count: 0,
            statement_snapshot: {},
            closed_at: '2026-04-18T12:00:00Z',
            closed_by_admin_user_id: null,
            created_at: '2026-04-18T12:00:00Z',
            updated_at: '2026-04-18T12:00:00Z',
          },
        ],
        payout_instructions: [],
        payout_executions: [
          {
            id: '98aa0f0d-fc06-4087-bd6e-36bb63f4cf1e',
            payout_instruction_id: '4df8b78c-e5ee-43ba-b6c4-ac2818c353b7',
            partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
            partner_statement_id: '113bdbd9-8c12-46dd-a4d8-5fa54c9680cc',
            partner_payout_account_id: 'fa8f6898-ebf5-47ea-9ec0-304f825d8b2e',
            execution_key: 'pe_customer_ops',
            execution_mode: 'dry_run',
            execution_status: 'reconciled',
            request_idempotency_key: 'ops-customer-payout',
            external_reference: 'external-customer-ops',
            execution_payload: {},
            result_payload: {},
            requested_by_admin_user_id: null,
            submitted_by_admin_user_id: null,
            submitted_at: null,
            completed_by_admin_user_id: null,
            completed_at: null,
            reconciled_by_admin_user_id: null,
            reconciled_at: null,
            failure_reason_code: null,
            created_at: '2026-04-18T12:00:00Z',
            updated_at: '2026-04-18T12:00:00Z',
          },
        ],
      },
    ],
    service_access_insights: [
      {
        service_identity: {
          id: '3c655303-a804-4234-b28b-9f0afe6958b4',
          service_key: 'svc_customer_ops',
          customer_account_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
          auth_realm_id: 'd6cc27a6-3560-4ca7-85f1-6c4f7ef39335',
          source_order_id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
          origin_storefront_id: 'c3f4a9f0-9a7b-4dd6-8b32-48fa66014d23',
          provider_name: 'remnawave',
          provider_subject_ref: 'remnawave-customer-ops',
          identity_status: 'active',
          service_context: {},
          created_at: '2026-04-18T12:00:00Z',
          updated_at: '2026-04-18T12:00:00Z',
        },
        service_state: {
          customer_account_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
          auth_realm_id: 'd6cc27a6-3560-4ca7-85f1-6c4f7ef39335',
          provider_name: 'remnawave',
          entitlement_snapshot: {
            status: 'active',
            has_access: true,
            grant_source: 'order',
            effective_from: '2026-04-18T12:00:00Z',
            expires_at: '2026-05-18T12:00:00Z',
          },
          service_identity: null,
          active_entitlement_grant: null,
          purchase_context: {
            source_type: 'order',
            source_order_id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
            source_order_sale_channel: 'web',
            source_order_status: 'committed',
            source_order_settlement_status: 'paid',
            source_order_storefront_id: 'c3f4a9f0-9a7b-4dd6-8b32-48fa66014d23',
            source_growth_reward_allocation_id: null,
            source_renewal_order_id: null,
            manual_source_key: null,
            origin_storefront_id: 'c3f4a9f0-9a7b-4dd6-8b32-48fa66014d23',
          },
          requested_context: {
            lookup_mode: 'service_identity',
            channel_type: null,
            channel_subject_ref: null,
            provisioning_profile_key: null,
            credential_type: null,
            credential_subject_key: null,
          },
          selected_provisioning_profile: null,
          selected_device_credential: null,
          selected_access_delivery_channel: null,
          provisioning_profiles: [
            {
              id: '14f6aa8b-eb10-4d9d-bf3a-e2c8338e791e',
              service_identity_id: '3c655303-a804-4234-b28b-9f0afe6958b4',
              profile_key: 'shared_client-default',
              target_channel: 'shared_client',
              delivery_method: 'shared_link',
              profile_status: 'active',
              provider_name: 'remnawave',
              provider_profile_ref: 'profile-customer-ops',
              provisioning_payload: {},
              created_at: '2026-04-18T12:00:00Z',
              updated_at: '2026-04-18T12:00:00Z',
            },
          ],
          device_credentials: [],
          access_delivery_channels: [],
        },
      },
    ],
    risk_subject_insights: [
      {
        risk_subject: {
          id: '309db37d-92fe-4df0-bc75-cae3b5d07135',
          principal_class: 'customer',
          principal_subject: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
          auth_realm_id: 'd6cc27a6-3560-4ca7-85f1-6c4f7ef39335',
          storefront_id: 'c3f4a9f0-9a7b-4dd6-8b32-48fa66014d23',
          status: 'active',
          risk_level: 'medium',
          metadata: {},
          created_at: '2026-04-18T12:00:00Z',
          updated_at: '2026-04-18T12:00:00Z',
        },
        reviews: [
          {
            id: 'c3ec8b59-e88f-469f-b2d7-c2d391adf05f',
            risk_subject_id: '309db37d-92fe-4df0-bc75-cae3b5d07135',
            review_type: 'manual_review',
            status: 'open',
            decision: 'pending',
            reason: 'Customer ops review',
            evidence: {},
            created_by_admin_user_id: null,
            resolved_by_admin_user_id: null,
            resolved_at: null,
            created_at: '2026-04-18T12:00:00Z',
            updated_at: '2026-04-18T12:00:00Z',
          },
        ],
      },
    ],
    ...overrides,
  } as AdminCustomerOperationsInsightResponse;
}

describe('CustomerOperationsInsight', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders order, service access, settlement, and risk sections from the canonical insight payload', async () => {
    mockGetOperationsInsight.mockResolvedValueOnce({
      data: buildOperationsInsightResponse(),
    });

    renderWithQueryClient(<CustomerOperationsInsight userId="9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0" />);

    await waitFor(() => {
      expect(screen.getByText('detail.operations.ordersTitle')).toBeInTheDocument();
    });

    expect(screen.getByText('detail.operations.serviceAccessTitle')).toBeInTheDocument();
    expect(screen.getByText('detail.operations.settlementTitle')).toBeInTheDocument();
    expect(screen.getByText('detail.operations.riskTitle')).toBeInTheDocument();
    expect(screen.getByText('remnawave')).toBeInTheDocument();
    expect(screen.queryByText('detail.operations.financeHidden')).not.toBeInTheDocument();
    expect(screen.queryByText('detail.operations.riskHidden')).not.toBeInTheDocument();
  });

  it('shows role-scoped hidden states when finance and risk overlays are unavailable', async () => {
    mockGetOperationsInsight.mockResolvedValueOnce({
      data: buildOperationsInsightResponse({
        section_access: {
          explainability_visible: true,
          finance_visible: false,
          finance_actions_visible: false,
          risk_visible: false,
        },
        settlement_workspaces: [],
        risk_subject_insights: [],
      }),
    });

    renderWithQueryClient(<CustomerOperationsInsight userId="9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0" />);

    await waitFor(() => {
      expect(screen.getByText('detail.operations.financeHidden')).toBeInTheDocument();
    });

    expect(screen.getByText('detail.operations.riskHidden')).toBeInTheDocument();
  });

  it('submits consolidated finance actions through the canonical operations rail', async () => {
    const payoutAccountId = 'fa8f6898-ebf5-47ea-9ec0-304f825d8b2f';
    mockGetOperationsInsight.mockResolvedValue({
      data: buildOperationsInsightResponse({
        settlement_workspaces: [
          {
            partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
            payout_accounts: [
              {
                id: payoutAccountId,
                partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
                settlement_profile_id: null,
                payout_rail: 'bank_transfer',
                display_label: 'Secondary USD Account',
                masked_destination: 'US00...4433',
                destination_metadata: {},
                verification_status: 'pending',
                approval_status: 'pending',
                account_status: 'active',
                is_default: false,
                created_by_admin_user_id: null,
                verified_by_admin_user_id: null,
                verified_at: null,
                approved_by_admin_user_id: null,
                approved_at: null,
                suspended_by_admin_user_id: null,
                suspended_at: null,
                suspension_reason_code: null,
                archived_by_admin_user_id: null,
                archived_at: null,
                archive_reason_code: null,
                default_selected_by_admin_user_id: null,
                default_selected_at: null,
                created_at: '2026-04-18T12:00:00Z',
                updated_at: '2026-04-18T12:00:00Z',
              },
            ],
            payout_account_actions: {
              [payoutAccountId]: ['verify_payout_account'],
            },
            payout_instruction_actions: {},
            partner_statements: [],
            payout_instructions: [],
            payout_executions: [],
          },
        ],
      }),
    });
    mockPerformOperationsAction.mockResolvedValueOnce({
      data: {
        action_kind: 'verify_payout_account',
        target_kind: 'payout_account',
        target_id: payoutAccountId,
        payout_account: {
          id: payoutAccountId,
          partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
          settlement_profile_id: null,
          payout_rail: 'bank_transfer',
          display_label: 'Secondary USD Account',
          masked_destination: 'US00...4433',
          destination_metadata: {},
          verification_status: 'verified',
          approval_status: 'approved',
          account_status: 'active',
          is_default: false,
          created_by_admin_user_id: null,
          verified_by_admin_user_id: null,
          verified_at: null,
          approved_by_admin_user_id: null,
          approved_at: null,
          suspended_by_admin_user_id: null,
          suspended_at: null,
          suspension_reason_code: null,
          archived_by_admin_user_id: null,
          archived_at: null,
          archive_reason_code: null,
          default_selected_by_admin_user_id: null,
          default_selected_at: null,
          created_at: '2026-04-18T12:00:00Z',
          updated_at: '2026-04-18T12:00:00Z',
        },
        payout_instruction: null,
      },
    });

    renderWithQueryClient(<CustomerOperationsInsight userId="9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0" />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'detail.operations.actions.verifyPayoutAccount' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'detail.operations.actions.verifyPayoutAccount' }));

    await waitFor(() => {
      expect(screen.getByText('detail.operations.dialogs.verifyPayoutAccountDescription')).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole('button', { name: 'detail.operations.actions.verifyPayoutAccount' }).at(-1)!);

    await waitFor(() => {
      expect(mockPerformOperationsAction).toHaveBeenCalledWith(
        '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
        {
          action_kind: 'verify_payout_account',
          payout_account_id: payoutAccountId,
        },
      );
    });

    await waitFor(() => {
      expect(screen.getByText('detail.operations.dialogs.verifyPayoutAccountSuccess')).toBeInTheDocument();
    });
  });

  it('opens a canonical dispute case from the payment dispute workflow rail', async () => {
    const paymentDisputeId = '88dfdf63-dfa2-4827-b55d-64c318fefb07';
    mockGetOperationsInsight.mockResolvedValue({
      data: buildOperationsInsightResponse({
        order_insights: [
          {
            ...buildOperationsInsightResponse().order_insights[0],
            payment_disputes: [
              {
                id: paymentDisputeId,
                order_id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
                payment_attempt_id: null,
                payment_id: null,
                provider: 'stripe',
                external_reference: 'pi_123',
                subtype: 'chargeback',
                outcome_class: 'open',
                lifecycle_status: 'needs_response',
                disputed_amount: 99,
                fee_amount: 15,
                fee_status: 'assessed',
                currency_code: 'USD',
                reason_code: 'fraudulent',
                evidence_snapshot: {},
                provider_snapshot: {},
                opened_at: '2026-04-18T12:00:00Z',
                closed_at: null,
                created_at: '2026-04-18T12:00:00Z',
                updated_at: '2026-04-18T12:00:00Z',
              },
            ],
            dispute_cases: [
              {
                id: '4ef796e8-aa1c-406c-9cc8-6b01f64f503e',
                partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
                payment_dispute_id: paymentDisputeId,
                order_id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
                case_kind: 'evidence_collection',
                case_status: 'waiting_on_ops',
                summary: 'Collect provider evidence',
                payload: {},
                notes: ['initial-note'],
                opened_by_admin_user_id: null,
                assigned_to_admin_user_id: null,
                closed_by_admin_user_id: null,
                closed_at: null,
                created_at: '2026-04-18T12:00:00Z',
                updated_at: '2026-04-18T12:00:00Z',
              },
            ],
          },
        ],
      }),
    });
    mockCreateDisputeCase.mockResolvedValueOnce({
      data: {
        id: '26b727ff-f2ba-4b67-a353-62c75448f4fb',
        partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
        payment_dispute_id: paymentDisputeId,
        order_id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
        case_kind: 'evidence_collection',
        case_status: 'waiting_on_ops',
        summary: 'Stripe needs response dispute evidence collection',
        payload: {},
        notes: ['chargeback / open'],
        opened_by_admin_user_id: null,
        assigned_to_admin_user_id: null,
        closed_by_admin_user_id: null,
        closed_at: null,
        created_at: '2026-04-18T12:00:00Z',
        updated_at: '2026-04-18T12:00:00Z',
      },
    });

    renderWithQueryClient(<CustomerOperationsInsight userId="9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0" />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'detail.operations.actions.openDisputeCase' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'detail.operations.actions.openDisputeCase' }));

    await waitFor(() => {
      expect(screen.getByText('detail.operations.dialogs.disputeCaseDescription')).toBeInTheDocument();
    });

    fireEvent.change(
      screen.getByPlaceholderText('detail.operations.dialogs.disputeCaseSummaryPlaceholder'),
      {
        target: { value: 'Stripe dispute evidence escalation' },
      },
    );

    fireEvent.change(
      screen.getByPlaceholderText('detail.operations.dialogs.disputeCaseNotesPlaceholder'),
      {
        target: { value: 'Need issuer timeline and receipt payload.' },
      },
    );

    fireEvent.click(screen.getAllByRole('button', { name: 'detail.operations.actions.openDisputeCase' }).at(-1)!);

    await waitFor(() => {
      expect(mockCreateDisputeCase).toHaveBeenCalledWith({
        partner_account_id: '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
        payment_dispute_id: paymentDisputeId,
        order_id: '3f26804f-fc9c-4df1-b571-20f06fd3340d',
        case_kind: 'evidence_collection',
        case_status: 'waiting_on_ops',
        summary: 'Stripe dispute evidence escalation',
        case_payload: {
          provider: 'stripe',
          external_reference: 'pi_123',
          lifecycle_status: 'needs_response',
        },
        notes: ['Need issuer timeline and receipt payload.'],
      });
    });

    await waitFor(() => {
      expect(screen.getByText('detail.operations.dialogs.disputeCaseSuccess')).toBeInTheDocument();
    });
  });

  it('downloads canonical settlement evidence from the customer operations settlement rail', async () => {
    mockGetOperationsInsight.mockResolvedValueOnce({
      data: buildOperationsInsightResponse(),
    });
    mockDownloadWorkspaceFinanceEvidence.mockResolvedValueOnce({
      blob: new Blob(['workspace'], { type: 'application/json' }),
      filename: 'workspace-evidence.json',
    });

    renderWithQueryClient(<CustomerOperationsInsight userId="9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0" />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'detail.operations.actions.downloadWorkspaceEvidence' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'detail.operations.actions.downloadWorkspaceEvidence' }));

    await waitFor(() => {
      expect(mockDownloadWorkspaceFinanceEvidence).toHaveBeenCalledWith(
        '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
        '5d4c6d90-32aa-4a81-b430-b390f5684d7d',
      );
    });

    expect(mockDownloadBlobFile).toHaveBeenCalledWith(expect.any(Blob), 'workspace-evidence.json');
    expect(screen.getByText('detail.operations.dialogs.exportEvidenceSuccess')).toBeInTheDocument();
  });
});
