'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Cable, CircleAlert, CreditCard, Download, Shield } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  customersApi,
  type AdminCustomerOperationsActionRequest,
  type AdminCustomerOperationsInsightResponse,
} from '@/lib/api/customers';
import {
  disputesApi,
  type CreateDisputeCaseRequest,
} from '@/lib/api/disputes';
import { CustomerStatusChip } from '@/features/customers/components/customer-status-chip';
import {
  formatCurrencyAmount,
  formatDateTime,
  getErrorMessage,
  humanizeToken,
  shortId,
} from '@/features/customers/lib/formatting';
import { AdminActionDialog } from '@/shared/ui/admin-action-dialog';
import { downloadBlobFile } from '@/shared/lib/download-file';
import { Modal } from '@/shared/ui/modal';

interface CustomerOperationsInsightProps {
  userId: string;
}

type CustomerTranslate = (key: string, values?: Record<string, string | number>) => string;
type AdminCustomerOrderInsight = NonNullable<AdminCustomerOperationsInsightResponse['order_insights']>[number];
type AdminCustomerServiceAccessInsight = NonNullable<AdminCustomerOperationsInsightResponse['service_access_insights']>[number];
type AdminCustomerSettlementWorkspaceInsight =
  NonNullable<AdminCustomerOperationsInsightResponse['settlement_workspaces']>[number];
type AdminCustomerRiskSubjectInsight = NonNullable<AdminCustomerOperationsInsightResponse['risk_subject_insights']>[number];
type AdminCustomerOperationsActionKind = AdminCustomerOperationsActionRequest['action_kind'];
type AdminCustomerPaymentDispute = NonNullable<AdminCustomerOrderInsight['payment_disputes']>[number];

interface PendingOperationsAction {
  actionKind: AdminCustomerOperationsActionKind;
  targetKind: 'payout_account' | 'payout_instruction';
  targetId: string;
  subject: string;
}

interface PendingDisputeCaseAction {
  partnerAccountId: string;
  paymentDispute: AdminCustomerPaymentDispute;
  orderId: string;
}

type SettlementEvidenceExportKind =
  | 'workspace'
  | 'partner_statement'
  | 'payout_instruction'
  | 'payout_execution';

function renderEmptyState(message: string) {
  return (
    <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-6 text-sm font-mono text-muted-foreground">
      {message}
    </div>
  );
}

function getOperationsActionMeta(t: CustomerTranslate, actionKind: AdminCustomerOperationsActionKind) {
  switch (actionKind) {
    case 'verify_payout_account':
      return {
        label: t('detail.operations.actions.verifyPayoutAccount'),
        title: t('detail.operations.dialogs.verifyPayoutAccountTitle'),
        description: t('detail.operations.dialogs.verifyPayoutAccountDescription'),
        successMessage: t('detail.operations.dialogs.verifyPayoutAccountSuccess'),
        tone: 'warning' as const,
        confirmVariant: 'default' as const,
        reasonRequired: false,
      };
    case 'suspend_payout_account':
      return {
        label: t('detail.operations.actions.suspendPayoutAccount'),
        title: t('detail.operations.dialogs.suspendPayoutAccountTitle'),
        description: t('detail.operations.dialogs.suspendPayoutAccountDescription'),
        successMessage: t('detail.operations.dialogs.suspendPayoutAccountSuccess'),
        tone: 'danger' as const,
        confirmVariant: 'destructive' as const,
        reasonRequired: true,
      };
    case 'approve_payout_instruction':
      return {
        label: t('detail.operations.actions.approvePayoutInstruction'),
        title: t('detail.operations.dialogs.approvePayoutInstructionTitle'),
        description: t('detail.operations.dialogs.approvePayoutInstructionDescription'),
        successMessage: t('detail.operations.dialogs.approvePayoutInstructionSuccess'),
        tone: 'warning' as const,
        confirmVariant: 'default' as const,
        reasonRequired: false,
      };
    case 'reject_payout_instruction':
      return {
        label: t('detail.operations.actions.rejectPayoutInstruction'),
        title: t('detail.operations.dialogs.rejectPayoutInstructionTitle'),
        description: t('detail.operations.dialogs.rejectPayoutInstructionDescription'),
        successMessage: t('detail.operations.dialogs.rejectPayoutInstructionSuccess'),
        tone: 'danger' as const,
        confirmVariant: 'destructive' as const,
        reasonRequired: true,
      };
  }
}

function DisputeCaseDialog({
  disputeAction,
  isPending,
  t,
  onClose,
  onSubmit,
}: {
  disputeAction: PendingDisputeCaseAction;
  isPending: boolean;
  t: CustomerTranslate;
  onClose: () => void;
  onSubmit: (payload: CreateDisputeCaseRequest) => Promise<void>;
}) {
  const [caseKind, setCaseKind] = useState<CreateDisputeCaseRequest['case_kind']>('evidence_collection');
  const [summary, setSummary] = useState(
    `${humanizeToken(disputeAction.paymentDispute.provider)} ${humanizeToken(disputeAction.paymentDispute.lifecycle_status)} dispute evidence collection`,
  );
  const [notes, setNotes] = useState(
    `${humanizeToken(disputeAction.paymentDispute.subtype)} / ${humanizeToken(disputeAction.paymentDispute.outcome_class)}`,
  );
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!summary.trim()) {
      setLocalError(t('detail.operations.dialogs.disputeCaseSummaryValidation'));
      return;
    }

    setLocalError(null);
    await onSubmit({
      partner_account_id: disputeAction.partnerAccountId,
      payment_dispute_id: disputeAction.paymentDispute.id,
      order_id: disputeAction.orderId,
      case_kind: caseKind,
      case_status: 'waiting_on_ops',
      summary: summary.trim(),
      case_payload: {
        provider: disputeAction.paymentDispute.provider,
        external_reference: disputeAction.paymentDispute.external_reference,
        lifecycle_status: disputeAction.paymentDispute.lifecycle_status,
      },
      notes: notes.trim() ? [notes.trim()] : [],
    });
  }

  return (
    <Modal isOpen onClose={onClose} title={t('detail.operations.dialogs.disputeCaseTitle')}>
      <div className="space-y-5">
        <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm font-mono text-amber-200">
          <p className="leading-6">
            {t('detail.operations.dialogs.disputeCaseDescription')}
          </p>
          <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-white">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t('detail.operations.labels.disputeCaseSubject')}
            </p>
            <p className="mt-2 break-all text-sm font-mono">
              #{shortId(disputeAction.paymentDispute.id)} • {humanizeToken(disputeAction.paymentDispute.provider)} • {humanizeToken(disputeAction.paymentDispute.lifecycle_status)}
            </p>
          </div>
        </div>

        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.disputeCaseKind')}
          </span>
          <select
            value={caseKind}
            onChange={(event) => setCaseKind(event.target.value as CreateDisputeCaseRequest['case_kind'])}
            className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
          >
            <option value="evidence_collection">{t('detail.operations.caseKinds.evidenceCollection')}</option>
            <option value="chargeback_review">{t('detail.operations.caseKinds.chargebackReview')}</option>
            <option value="payout_dispute">{t('detail.operations.caseKinds.payoutDispute')}</option>
            <option value="reserve_review">{t('detail.operations.caseKinds.reserveReview')}</option>
          </select>
        </label>

        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.disputeCaseSummary')}
          </span>
          <Input
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            placeholder={t('detail.operations.dialogs.disputeCaseSummaryPlaceholder')}
          />
        </label>

        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.disputeCaseNotes')}
          </span>
          <textarea
            rows={4}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
            placeholder={t('detail.operations.dialogs.disputeCaseNotesPlaceholder')}
          />
        </label>

        {localError ? (
          <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
            {localError}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-end gap-3">
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            onClick={onClose}
            disabled={isPending}
          >
            {t('common.cancel')}
          </Button>
          <Button
            type="button"
            magnetic={false}
            disabled={isPending}
            onClick={() => {
              void handleSubmit();
            }}
          >
            {t('detail.operations.actions.openDisputeCase')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function OrderInsightCard({
  insight,
  locale,
  t,
  canCreateDisputeCases,
  onOpenDisputeCase,
  disputeCasePending,
}: {
  insight: AdminCustomerOrderInsight;
  locale: string;
  t: CustomerTranslate;
  canCreateDisputeCases: boolean;
  onOpenDisputeCase: (payload: PendingDisputeCaseAction) => void;
  disputeCasePending: boolean;
}) {
  const order = insight.order_explainability.order;
  const evaluation = insight.order_explainability.commissionability_evaluation;
  const attribution = insight.attribution_result;
  const paymentDisputes = insight.payment_disputes ?? [];
  const evaluationReasonCodes = evaluation.reason_codes ?? [];
  const disputeCases = insight.dispute_cases ?? [];
  const canOpenDisputeCases = canCreateDisputeCases && Boolean(insight.resolved_partner_account_id);

  return (
    <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
            #{shortId(order.id)}
          </p>
          <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {formatDateTime(order.created_at, locale)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <CustomerStatusChip
            label={humanizeToken(order.settlement_status)}
            tone="info"
          />
          <CustomerStatusChip
            label={humanizeToken(evaluation.commissionability_status)}
            tone={evaluation.commissionability_status === 'eligible' ? 'success' : 'warning'}
          />
          {attribution ? (
            <CustomerStatusChip
              label={humanizeToken(attribution.owner_type)}
              tone="warning"
            />
          ) : null}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.saleChannel')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {humanizeToken(order.sale_channel)}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.displayedPrice')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {formatCurrencyAmount(order.displayed_price, order.currency_code, locale)}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.owner')}
          </p>
          <p className="mt-2 break-all text-sm font-mono text-white">
            {attribution?.partner_account_id ?? t('common.none')}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.disputes')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {String(paymentDisputes.length)}
          </p>
        </div>
      </div>

      {evaluationReasonCodes.length ? (
        <div className="mt-4">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.reasonCodes')}
          </p>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {evaluationReasonCodes.map((item) => humanizeToken(item)).join(' • ')}
          </p>
        </div>
      ) : null}

      {paymentDisputes.length ? (
        <div className="mt-5 space-y-3 border-t border-grid-line/20 pt-4">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.paymentDisputeWorkflow')}
          </p>
          {paymentDisputes.map((paymentDispute) => {
            const linkedDisputeCases = disputeCases.filter(
              (disputeCase) => disputeCase.payment_dispute_id === paymentDispute.id,
            );

            return (
              <div
                key={paymentDispute.id}
                className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-mono text-white">
                      #{shortId(paymentDispute.id)} • {humanizeToken(paymentDispute.provider)}
                    </p>
                    <p className="mt-1 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                      {humanizeToken(paymentDispute.lifecycle_status)} • {humanizeToken(paymentDispute.outcome_class)}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <CustomerStatusChip
                      label={humanizeToken(paymentDispute.subtype)}
                      tone="warning"
                    />
                    <CustomerStatusChip
                      label={humanizeToken(paymentDispute.lifecycle_status)}
                      tone="info"
                    />
                    {canOpenDisputeCases ? (
                      <Button
                        type="button"
                        size="sm"
                        magnetic={false}
                        disabled={disputeCasePending}
                        onClick={() => {
                          onOpenDisputeCase({
                            partnerAccountId: insight.resolved_partner_account_id!,
                            paymentDispute,
                            orderId: order.id,
                          });
                        }}
                      >
                        {t('detail.operations.actions.openDisputeCase')}
                      </Button>
                    ) : null}
                  </div>
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('detail.operations.labels.disputedAmount')}
                    </p>
                    <p className="mt-2 text-sm font-mono text-white">
                      {formatCurrencyAmount(paymentDispute.disputed_amount, paymentDispute.currency_code, locale)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('detail.operations.labels.linkedDisputeCases')}
                    </p>
                    <p className="mt-2 text-sm font-mono text-white">
                      {String(linkedDisputeCases.length)}
                    </p>
                  </div>
                </div>

                {linkedDisputeCases.length ? (
                  <div className="mt-4 space-y-2">
                    {linkedDisputeCases.map((disputeCase) => (
                      <div
                        key={disputeCase.id}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/40 px-3 py-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="text-sm font-mono text-white">
                            #{shortId(disputeCase.id)} • {humanizeToken(disputeCase.case_kind)}
                          </p>
                          <CustomerStatusChip
                            label={humanizeToken(disputeCase.case_status)}
                            tone={disputeCase.case_status === 'closed' || disputeCase.case_status === 'resolved'
                              ? 'success'
                              : 'warning'}
                          />
                        </div>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {disputeCase.summary}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-4 text-sm font-mono leading-6 text-muted-foreground">
                    {t('detail.operations.disputeCasesEmpty')}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function ServiceAccessInsightCard({
  insight,
  locale,
  t,
}: {
  insight: AdminCustomerServiceAccessInsight;
  locale: string;
  t: CustomerTranslate;
}) {
  const state = insight.service_state;
  const accessDeliveryChannels = state.access_delivery_channels ?? [];
  const provisioningProfiles = state.provisioning_profiles ?? [];

  return (
    <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
            {insight.service_identity.provider_name}
          </p>
          <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {shortId(insight.service_identity.auth_realm_id)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <CustomerStatusChip
            label={humanizeToken(state.entitlement_snapshot.status ?? 'unknown')}
            tone="success"
          />
          <CustomerStatusChip
            label={humanizeToken(insight.service_identity.identity_status)}
            tone="info"
          />
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.sourceType')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {humanizeToken(state.purchase_context.source_type ?? 'none')}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.deliveryChannels')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {String(accessDeliveryChannels.length)}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.provisioningProfiles')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {String(provisioningProfiles.length)}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.updatedAt')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {formatDateTime(insight.service_identity.updated_at, locale)}
          </p>
        </div>
      </div>
    </div>
  );
}

function SettlementWorkspaceCard({
  insight,
  locale,
  t,
  canRenderActions,
  onActionClick,
  actionsPending,
  onExportClick,
  exportPending,
}: {
  insight: AdminCustomerSettlementWorkspaceInsight;
  locale: string;
  t: CustomerTranslate;
  canRenderActions: boolean;
  onActionClick: (action: PendingOperationsAction) => void;
  actionsPending: boolean;
  onExportClick: (kind: SettlementEvidenceExportKind, resourceId: string) => void;
  exportPending: boolean;
}) {
  const partnerStatements = insight.partner_statements ?? [];
  const payoutInstructions = insight.payout_instructions ?? [];
  const payoutExecutions = insight.payout_executions ?? [];
  const payoutAccounts = insight.payout_accounts ?? [];
  const payoutAccountActions = insight.payout_account_actions ?? {};
  const payoutInstructionActions = insight.payout_instruction_actions ?? {};
  const latestStatement = partnerStatements[0];
  const latestInstruction = payoutInstructions[0];
  const latestExecution = payoutExecutions[0];
  const defaultPayoutAccount = payoutAccounts.find((item) => item.is_default) ?? payoutAccounts[0];
  const actionablePayoutAccounts = payoutAccounts.filter(
    (item) => (payoutAccountActions[item.id] ?? []).length > 0,
  );
  const actionableInstructions = payoutInstructions.filter(
    (item) => (payoutInstructionActions[item.id] ?? []).length > 0,
  );

  return (
    <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
            {shortId(insight.partner_account_id)}
          </p>
          <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.payoutAccountsCount', { count: payoutAccounts.length })}
          </p>
        </div>
        {latestExecution ? (
          <CustomerStatusChip
            label={humanizeToken(latestExecution.execution_status)}
            tone="warning"
          />
        ) : null}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.availableAmount')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {latestStatement
              ? formatCurrencyAmount(latestStatement.available_amount, latestStatement.currency_code, locale)
              : t('common.none')}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.payoutRail')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {defaultPayoutAccount ? humanizeToken(defaultPayoutAccount.payout_rail) : t('common.none')}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.latestStatement')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {latestStatement ? humanizeToken(latestStatement.statement_status) : t('common.none')}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.latestExecution')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {latestExecution ? humanizeToken(latestExecution.execution_status) : t('common.none')}
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2 border-t border-grid-line/20 pt-4">
        <Button
          type="button"
          size="sm"
          magnetic={false}
          variant="outline"
          disabled={exportPending}
          onClick={() => {
            onExportClick('workspace', insight.partner_account_id);
          }}
        >
          <Download className="mr-2 h-3.5 w-3.5" />
          {t('detail.operations.actions.downloadWorkspaceEvidence')}
        </Button>

        {latestStatement ? (
          <Button
            type="button"
            size="sm"
            magnetic={false}
            variant="outline"
            disabled={exportPending}
            onClick={() => {
              onExportClick('partner_statement', latestStatement.id);
            }}
          >
            <Download className="mr-2 h-3.5 w-3.5" />
            {t('detail.operations.actions.downloadStatementEvidence')}
          </Button>
        ) : null}

        {latestExecution ? (
          <Button
            type="button"
            size="sm"
            magnetic={false}
            variant="outline"
            disabled={exportPending}
            onClick={() => {
              onExportClick('payout_execution', latestExecution.id);
            }}
          >
            <Download className="mr-2 h-3.5 w-3.5" />
            {t('detail.operations.actions.downloadPayoutExecutionEvidence')}
          </Button>
        ) : null}

        {latestInstruction ? (
          <Button
            type="button"
            size="sm"
            magnetic={false}
            variant="outline"
            disabled={exportPending}
            onClick={() => {
              onExportClick('payout_instruction', latestInstruction.id);
            }}
          >
            <Download className="mr-2 h-3.5 w-3.5" />
            {t('detail.operations.actions.downloadPayoutInstructionEvidence')}
          </Button>
        ) : null}
      </div>

      {canRenderActions && (actionablePayoutAccounts.length || actionableInstructions.length) ? (
        <div className="mt-5 space-y-4 border-t border-grid-line/20 pt-4">
          {actionablePayoutAccounts.length ? (
            <div className="space-y-3">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('detail.operations.labels.actionablePayoutAccounts')}
              </p>
              {actionablePayoutAccounts.map((account) => (
                <div
                  key={account.id}
                  className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-mono text-white">
                        {account.display_label}
                      </p>
                      <p className="mt-1 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                        {account.masked_destination}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(payoutAccountActions[account.id] ?? []).map((actionKind) => {
                        const meta = getOperationsActionMeta(t, actionKind);
                        return (
                          <Button
                            key={`${account.id}-${actionKind}`}
                            type="button"
                            size="sm"
                            magnetic={false}
                            variant={meta.confirmVariant}
                            disabled={actionsPending}
                            onClick={() => {
                              onActionClick({
                                actionKind,
                                targetKind: 'payout_account',
                                targetId: account.id,
                                subject: `${account.display_label} • ${account.masked_destination}`,
                              });
                            }}
                          >
                            {meta.label}
                          </Button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          {actionableInstructions.length ? (
            <div className="space-y-3">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('detail.operations.labels.actionablePayoutInstructions')}
              </p>
              {actionableInstructions.map((instruction) => (
                <div
                  key={instruction.id}
                  className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-mono text-white">
                        #{shortId(instruction.id)}
                      </p>
                      <p className="mt-1 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                        {formatCurrencyAmount(instruction.payout_amount, instruction.currency_code, locale)}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(payoutInstructionActions[instruction.id] ?? []).map((actionKind) => {
                        const meta = getOperationsActionMeta(t, actionKind);
                        return (
                          <Button
                            key={`${instruction.id}-${actionKind}`}
                            type="button"
                            size="sm"
                            magnetic={false}
                            variant={meta.confirmVariant}
                            disabled={actionsPending}
                            onClick={() => {
                              onActionClick({
                                actionKind,
                                targetKind: 'payout_instruction',
                                targetId: instruction.id,
                                subject: `#${shortId(instruction.id)} • ${formatCurrencyAmount(instruction.payout_amount, instruction.currency_code, locale)}`,
                              });
                            }}
                          >
                            {meta.label}
                          </Button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function RiskInsightCard({
  insight,
  locale,
  t,
}: {
  insight: AdminCustomerRiskSubjectInsight;
  locale: string;
  t: CustomerTranslate;
}) {
  const reviews = insight.reviews ?? [];
  const latestReview = reviews[0];
  const openReviewCount = reviews.filter((item) => item.status === 'open').length;

  return (
    <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
            {shortId(insight.risk_subject.id)}
          </p>
          <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {formatDateTime(insight.risk_subject.updated_at, locale)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <CustomerStatusChip
            label={humanizeToken(insight.risk_subject.risk_level)}
            tone="warning"
          />
          <CustomerStatusChip
            label={humanizeToken(insight.risk_subject.status)}
            tone="info"
          />
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.openReviews')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {String(openReviewCount)}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('detail.operations.labels.latestDecision')}
          </p>
          <p className="mt-2 text-sm font-mono text-white">
            {latestReview ? humanizeToken(latestReview.decision) : t('common.none')}
          </p>
        </div>
      </div>
    </div>
  );
}

export function CustomerOperationsInsight({ userId }: CustomerOperationsInsightProps) {
  const t = useTranslations('Customers');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [pendingAction, setPendingAction] = useState<PendingOperationsAction | null>(null);
  const [pendingDisputeCase, setPendingDisputeCase] = useState<PendingDisputeCaseAction | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const operationsQuery = useQuery({
    queryKey: ['customers', 'detail', userId, 'operations-insight'],
    queryFn: async () => {
      const response = await customersApi.getOperationsInsight(userId);
      return response.data;
    },
    staleTime: 15_000,
  });

  const actionMutation = useMutation({
    mutationFn: async (payload: AdminCustomerOperationsActionRequest) => {
      const response = await customersApi.performOperationsAction(userId, payload);
      return response.data;
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'operations-insight'] });
      setFeedback(getOperationsActionMeta(t, result.action_kind).successMessage);
      setPendingAction(null);
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const exportMutation = useMutation({
    mutationFn: async ({
      kind,
      resourceId,
    }: {
      kind: SettlementEvidenceExportKind;
      resourceId: string;
    }) => {
      switch (kind) {
        case 'workspace':
          return customersApi.downloadWorkspaceFinanceEvidence(userId, resourceId);
        case 'partner_statement':
          return customersApi.downloadPartnerStatementEvidence(userId, resourceId);
        case 'payout_instruction':
          return customersApi.downloadPayoutInstructionEvidence(userId, resourceId);
        case 'payout_execution':
          return customersApi.downloadPayoutExecutionEvidence(userId, resourceId);
      }
    },
    onSuccess: (result) => {
      downloadBlobFile(result.blob, result.filename);
      setFeedback(t('detail.operations.dialogs.exportEvidenceSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const disputeCaseMutation = useMutation({
    mutationFn: async (payload: CreateDisputeCaseRequest) => {
      const response = await disputesApi.createDisputeCase(payload);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'operations-insight'] });
      setFeedback(t('detail.operations.dialogs.disputeCaseSuccess'));
      setPendingDisputeCase(null);
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const operations = operationsQuery.data;
  const orderInsights = operations?.order_insights ?? [];
  const serviceAccessInsights = operations?.service_access_insights ?? [];
  const settlementWorkspaces = operations?.settlement_workspaces ?? [];
  const riskSubjectInsights = operations?.risk_subject_insights ?? [];
  const pendingActionMeta = pendingAction ? getOperationsActionMeta(t, pendingAction.actionKind) : null;

  async function handleActionConfirm(reason?: string) {
    if (!pendingAction) {
      return;
    }
    const payload: AdminCustomerOperationsActionRequest = {
      action_kind: pendingAction.actionKind,
    };
    if (pendingAction.targetKind === 'payout_account') {
      payload.payout_account_id = pendingAction.targetId;
    } else {
      payload.payout_instruction_id = pendingAction.targetId;
    }
    if (reason) {
      payload.reason_code = reason;
    }
    await actionMutation.mutateAsync(payload);
  }

  return (
    <section
      className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur"
      data-testid="customer-operations-insight"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('detail.operations.title')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('detail.operations.description')}
          </p>
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-grid-line/20 bg-terminal-bg/45 text-neon-cyan">
          <CircleAlert className="h-4 w-4" />
        </div>
      </div>

      {feedback ? (
        <div className="mt-5 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
          {feedback}
        </div>
      ) : null}

      {operationsQuery.isLoading ? (
        <div className="mt-5 grid gap-3 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-40 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
            />
          ))}
        </div>
      ) : operationsQuery.isError ? (
        <div className="mt-5 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
          {getErrorMessage(operationsQuery.error, t('detail.operations.loadError'))}
        </div>
      ) : operations ? (
        <div className="mt-5 grid gap-6 xl:grid-cols-2">
          <article className="space-y-3">
            <div className="flex items-center gap-2 text-neon-cyan">
              <CircleAlert className="h-4 w-4" />
              <h3 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                {t('detail.operations.ordersTitle')}
              </h3>
            </div>
            {orderInsights.length
                ? orderInsights.map((item) => (
                <OrderInsightCard
                  key={item.order_explainability.order.id}
                  insight={item}
                  locale={locale}
                  t={t}
                  canCreateDisputeCases={operations.section_access.finance_visible}
                  onOpenDisputeCase={(payload) => {
                    setFeedback(null);
                    setPendingDisputeCase(payload);
                  }}
                  disputeCasePending={disputeCaseMutation.isPending}
                />
              ))
              : renderEmptyState(t('detail.operations.ordersEmpty'))}
          </article>

          <article className="space-y-3">
            <div className="flex items-center gap-2 text-neon-cyan">
              <Cable className="h-4 w-4" />
              <h3 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                {t('detail.operations.serviceAccessTitle')}
              </h3>
            </div>
            {serviceAccessInsights.length
              ? serviceAccessInsights.map((item) => (
                <ServiceAccessInsightCard
                  key={item.service_identity.id}
                  insight={item}
                  locale={locale}
                  t={t}
                />
              ))
              : renderEmptyState(t('detail.operations.serviceAccessEmpty'))}
          </article>

          <article className="space-y-3">
            <div className="flex items-center gap-2 text-neon-cyan">
              <CreditCard className="h-4 w-4" />
              <h3 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                {t('detail.operations.settlementTitle')}
              </h3>
            </div>
            {operations.section_access.finance_visible
              ? settlementWorkspaces.length
                ? settlementWorkspaces.map((item) => (
                  <SettlementWorkspaceCard
                    key={item.partner_account_id}
                    insight={item}
                    locale={locale}
                    t={t}
                    canRenderActions={operations.section_access.finance_actions_visible}
                  onActionClick={(action) => {
                      setFeedback(null);
                      setPendingAction(action);
                    }}
                    actionsPending={actionMutation.isPending}
                    onExportClick={(kind, resourceId) => {
                      setFeedback(null);
                      void exportMutation.mutateAsync({ kind, resourceId });
                    }}
                    exportPending={exportMutation.isPending}
                  />
                ))
                : renderEmptyState(t('detail.operations.settlementEmpty'))
              : renderEmptyState(t('detail.operations.financeHidden'))}
          </article>

          <article className="space-y-3">
            <div className="flex items-center gap-2 text-neon-cyan">
              <Shield className="h-4 w-4" />
              <h3 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                {t('detail.operations.riskTitle')}
              </h3>
            </div>
            {operations.section_access.risk_visible
              ? riskSubjectInsights.length
                ? riskSubjectInsights.map((item) => (
                  <RiskInsightCard
                    key={item.risk_subject.id}
                    insight={item}
                    locale={locale}
                    t={t}
                  />
                ))
                : renderEmptyState(t('detail.operations.riskEmpty'))
              : renderEmptyState(t('detail.operations.riskHidden'))}
          </article>
        </div>
      ) : (
        <div className="mt-5 rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-6 text-sm font-mono text-muted-foreground">
          {t('detail.operations.empty')}
        </div>
      )}

      {pendingAction && pendingActionMeta ? (
        <AdminActionDialog
          isOpen
          isPending={actionMutation.isPending}
          title={pendingActionMeta.title}
          description={pendingActionMeta.description}
          confirmLabel={pendingActionMeta.label}
          cancelLabel={t('common.cancel')}
          onClose={() => {
            if (!actionMutation.isPending) {
              setPendingAction(null);
            }
          }}
          onConfirm={handleActionConfirm}
          confirmVariant={pendingActionMeta.confirmVariant}
          tone={pendingActionMeta.tone}
          subject={pendingAction.subject}
          subjectLabel={pendingAction.targetKind === 'payout_account'
            ? t('detail.operations.labels.payoutAccount')
            : t('detail.operations.labels.payoutInstruction')}
          reasonLabel={pendingActionMeta.reasonRequired ? t('detail.dialogs.reasonLabel') : undefined}
          reasonPlaceholder={pendingActionMeta.reasonRequired ? t('detail.dialogs.reasonPlaceholder') : undefined}
          reasonRequired={pendingActionMeta.reasonRequired}
          reasonValidationMessage={t('detail.dialogs.reasonValidation')}
        />
      ) : null}

      {pendingDisputeCase ? (
        <DisputeCaseDialog
          disputeAction={pendingDisputeCase}
          isPending={disputeCaseMutation.isPending}
          t={t}
          onClose={() => {
            if (!disputeCaseMutation.isPending) {
              setPendingDisputeCase(null);
            }
          }}
          onSubmit={async (payload) => {
            await disputeCaseMutation.mutateAsync(payload);
          }}
        />
      ) : null}
    </section>
  );
}
