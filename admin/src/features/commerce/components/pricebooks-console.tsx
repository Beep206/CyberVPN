'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CalendarClock,
  ClipboardCheck,
  History,
  Landmark,
  Plus,
  RotateCcw,
  Rocket,
  ScrollText,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { offersApi } from '@/lib/api/offers';
import {
  pricebooksApi,
  type AdminCommercialPricebookRecord,
  type AdminPricebookAuditResponse,
  type AdminPricebookHistoryResponse,
  type AdminPricebookValidationResponse,
  type CreatePricebookRequest,
} from '@/lib/api/pricebooks';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  formatDateTime,
  humanizeToken,
  shortId,
} from '@/features/commerce/lib/formatting';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { PricebookEditorModal } from '@/features/commerce/components/pricebook-editor-modal';
import { StatusChip } from '@/features/commerce/components/status-chip';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';
import { Modal } from '@/shared/ui/modal';

type LifecycleAction = 'publish' | 'schedule' | 'rollback';

type LifecycleActionTarget = {
  action: LifecycleAction;
  pricebook: AdminCommercialPricebookRecord;
};

type LifecycleActionPayload = {
  effectiveFrom?: string;
  reason?: string;
  scheduledFor?: string;
  targetPricebookId?: string;
};

const ACTIONABLE_LIFECYCLE_STATUSES = ['draft', 'scheduled'] as const;
const ROLLBACK_LIFECYCLE_STATUSES = ['active', 'published', 'scheduled'] as const;
const MAX_CHANGE_REASON_LENGTH = 500;

function lifecycleStatus(pricebook: AdminCommercialPricebookRecord) {
  return (pricebook.lifecycle_status || pricebook.version_status).toLowerCase();
}

function canRunLifecycleAction(
  action: LifecycleAction,
  pricebook: AdminCommercialPricebookRecord,
) {
  const status = lifecycleStatus(pricebook);

  if (action === 'rollback') {
    return ROLLBACK_LIFECYCLE_STATUSES.includes(
      status as (typeof ROLLBACK_LIFECYCLE_STATUSES)[number],
    );
  }

  return ACTIONABLE_LIFECYCLE_STATUSES.includes(
    status as (typeof ACTIONABLE_LIFECYCLE_STATUSES)[number],
  );
}

function pricebookTone(pricebook: AdminCommercialPricebookRecord) {
  const normalized = lifecycleStatus(pricebook);

  if (normalized === 'active' || normalized === 'published') {
    return 'success' as const;
  }

  if (normalized === 'archived' || normalized === 'rolled_back') {
    return 'danger' as const;
  }

  if (normalized === 'draft' || normalized === 'scheduled') {
    return 'warning' as const;
  }

  return 'info' as const;
}

function issueTone(severity: string) {
  return severity === 'error' ? 'danger' as const : 'warning' as const;
}

function pricebookEntryTotal(pricebook: AdminCommercialPricebookRecord) {
  return pricebook.entries.reduce(
    (total, entry) => total + entry.visible_price,
    0,
  );
}

function normalizeLifecycleDateTime(value: string | undefined) {
  const trimmed = value?.trim();

  if (!trimmed) {
    return null;
  }

  const parsed = new Date(trimmed);

  return Number.isNaN(parsed.getTime()) ? trimmed : parsed.toISOString();
}

export function PricebooksConsole() {
  const t = useTranslations('Commerce');
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedPricebookId, setSelectedPricebookId] = useState<string | null>(
    null,
  );
  const [actionTarget, setActionTarget] =
    useState<LifecycleActionTarget | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const pricebooksQuery = useQuery({
    queryKey: ['commerce', 'pricebooks', 'admin', 'lifecycle'],
    queryFn: async () => {
      const response = await pricebooksApi.listCommercialAdmin({
        include_inactive: true,
      });
      return response.data.sort((left, right) =>
        left.pricebook_key.localeCompare(right.pricebook_key),
      );
    },
    staleTime: 60_000,
  });

  const offersQuery = useQuery({
    queryKey: ['commerce', 'offers', 'admin'],
    queryFn: async () => {
      const response = await offersApi.listAdmin({ include_inactive: true });
      return response.data.sort((left, right) =>
        left.offer_key.localeCompare(right.offer_key),
      );
    },
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreatePricebookRequest) => pricebooksApi.create(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['commerce', 'pricebooks'],
      });
      setIsCreateOpen(false);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(
        error instanceof Error ? error.message : t('common.actionFailed'),
      );
    },
  });

  const lifecycleMutation = useMutation({
    mutationFn: async ({
      payload,
      target,
    }: {
      payload: LifecycleActionPayload;
      target: LifecycleActionTarget;
    }) => {
      if (target.action === 'publish') {
        return pricebooksApi.publishCommercialAdmin(target.pricebook.id, {
          change_reason: payload.reason ?? null,
          effective_from: normalizeLifecycleDateTime(payload.effectiveFrom),
        });
      }

      if (target.action === 'schedule') {
        const scheduledFor = normalizeLifecycleDateTime(payload.scheduledFor);

        if (!scheduledFor) {
          throw new Error(t('pricebooks.lifecycle.scheduleRequired'));
        }

        return pricebooksApi.scheduleCommercialAdmin(target.pricebook.id, {
          change_reason: payload.reason ?? null,
          scheduled_for: scheduledFor,
        });
      }

      return pricebooksApi.rollbackCommercialAdmin(target.pricebook.id, {
        change_reason: payload.reason ?? null,
        target_pricebook_id: payload.targetPricebookId || null,
      });
    },
    onSuccess: async (response) => {
      setActionTarget(null);
      setSelectedPricebookId(response.data.pricebook.id);
      setErrorMessage(null);
      await queryClient.invalidateQueries({
        queryKey: ['commerce', 'pricebooks'],
      });
    },
    onError: (error) => {
      setErrorMessage(
        error instanceof Error ? error.message : t('common.actionFailed'),
      );
    },
  });

  const pricebooks = pricebooksQuery.data ?? [];
  const offers = offersQuery.data ?? [];
  const selectedPricebook =
    pricebooks.find((pricebook) => pricebook.id === selectedPricebookId)
    ?? pricebooks[0]
    ?? null;
  const activePricebooks = pricebooks.filter(
    (pricebook) => pricebook.lifecycle_status.toLowerCase() === 'active',
  ).length;
  const currencies = new Set(
    pricebooks.map((pricebook) => pricebook.currency_code),
  ).size;
  const entries = pricebooks.reduce(
    (total, pricebook) => total + pricebook.entries.length,
    0,
  );

  const historyQuery = useQuery({
    queryKey: [
      'commerce',
      'pricebooks',
      'history',
      selectedPricebook?.pricebook_key,
    ],
    queryFn: async () => {
      if (!selectedPricebook) {
        return null;
      }

      const response = await pricebooksApi.getCommercialHistory(
        selectedPricebook.pricebook_key,
      );
      return response.data;
    },
    enabled: Boolean(selectedPricebook),
    staleTime: 30_000,
  });

  const auditQuery = useQuery({
    queryKey: ['commerce', 'pricebooks', 'audit', selectedPricebook?.id],
    queryFn: async () => {
      if (!selectedPricebook) {
        return [];
      }

      const response = await pricebooksApi.getCommercialAudit(
        selectedPricebook.id,
        { limit: 8 },
      );
      return response.data;
    },
    enabled: Boolean(selectedPricebook),
    staleTime: 30_000,
  });

  const validationQuery = useQuery({
    queryKey: ['commerce', 'pricebooks', 'validation', selectedPricebook?.id],
    queryFn: async () => {
      if (!selectedPricebook) {
        return null;
      }

      const response = await pricebooksApi.validateCommercialAdmin(
        selectedPricebook.id,
      );
      return response.data;
    },
    enabled: false,
    retry: false,
  });

  function handleValidateSelected() {
    if (!selectedPricebook) {
      return;
    }

    void validationQuery.refetch();
  }

  return (
    <>
      <CommercePageShell
        eyebrow={t('pricebooks.eyebrow')}
        title={t('pricebooks.title')}
        description={t('pricebooks.description')}
        icon={Landmark}
        actions={
          <Button
            magnetic={false}
            onClick={() => setIsCreateOpen(true)}
            aria-label={t('pricebooks.createAction')}
          >
            <Plus className="mr-2 h-4 w-4" />
            {t('pricebooks.createAction')}
          </Button>
        }
        metrics={[
          {
            label: t('pricebooks.metrics.total'),
            value: formatCompactNumber(pricebooks.length),
            hint: t('pricebooks.metrics.totalHint'),
            tone: 'info',
          },
          {
            label: t('pricebooks.metrics.active'),
            value: formatCompactNumber(activePricebooks),
            hint: t('pricebooks.metrics.activeHint'),
            tone: 'success',
          },
          {
            label: t('pricebooks.metrics.currencies'),
            value: formatCompactNumber(currencies),
            hint: t('pricebooks.metrics.currenciesHint'),
            tone: 'neutral',
          },
          {
            label: t('pricebooks.metrics.entries'),
            value: formatCompactNumber(entries),
            hint: t('pricebooks.metrics.entriesHint'),
            tone: 'warning',
          },
        ]}
      >
        <div className="grid min-w-0 max-w-full gap-6 2xl:grid-cols-[minmax(0,1fr)_28rem]">
          <div className="min-w-0 space-y-6">
            <div className="min-w-0 overflow-hidden rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              {errorMessage ? (
                <div
                  className="mb-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
                  role="alert"
                  aria-live="assertive"
                >
                  {errorMessage}
                </div>
              ) : null}

              {pricebooksQuery.isLoading ? (
                <div className="grid gap-3">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <div
                      key={index}
                      className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                    />
                  ))}
                </div>
              ) : pricebooks.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                  {t('pricebooks.empty')}
                </div>
              ) : (
                <Table>
                  <caption className="sr-only">
                    {t('pricebooks.tableCaption')}
                  </caption>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('pricebooks.fields.pricebookKey')}</TableHead>
                      <TableHead>{t('pricebooks.fields.currencyCode')}</TableHead>
                      <TableHead>{t('pricebooks.fields.regionCode')}</TableHead>
                      <TableHead>{t('pricebooks.fields.entries')}</TableHead>
                      <TableHead>{t('pricebooks.fields.entryValue')}</TableHead>
                      <TableHead>{t('pricebooks.fields.effectiveWindow')}</TableHead>
                      <TableHead>{t('common.status')}</TableHead>
                      <TableHead>{t('common.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pricebooks.map((pricebook) => {
                      const isSelected = pricebook.id === selectedPricebook?.id;
                      const canPublish = canRunLifecycleAction(
                        'publish',
                        pricebook,
                      );

                      return (
                        <TableRow
                          key={pricebook.id}
                          className={
                            isSelected
                              ? 'border-l-2 border-l-neon-cyan bg-neon-cyan/5'
                              : undefined
                          }
                        >
                          <TableCell>
                            <div className="space-y-1">
                              <p className="font-display uppercase tracking-[0.14em] text-white">
                                {pricebook.display_name}
                              </p>
                              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                                {pricebook.pricebook_key} / #{shortId(pricebook.id)}
                              </p>
                            </div>
                          </TableCell>
                          <TableCell>{pricebook.currency_code}</TableCell>
                          <TableCell>
                            {pricebook.region_code ?? t('common.emptyShort')}
                          </TableCell>
                          <TableCell>{formatCompactNumber(pricebook.entries.length)}</TableCell>
                          <TableCell>
                            {formatCurrencyAmount(
                              pricebookEntryTotal(pricebook),
                              pricebook.currency_code,
                            )}
                          </TableCell>
                          <TableCell>
                            <span className="text-xs font-mono text-muted-foreground">
                              {formatDateTime(pricebook.effective_from)} /{' '}
                              {formatDateTime(pricebook.effective_to)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <StatusChip
                              label={humanizeToken(pricebook.lifecycle_status)}
                              tone={pricebookTone(pricebook)}
                            />
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-2">
                              <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                magnetic={false}
                                onClick={() => setSelectedPricebookId(pricebook.id)}
                                aria-label={t('pricebooks.selectAction', {
                                  name: pricebook.display_name,
                                })}
                              >
                                <ScrollText className="mr-2 h-4 w-4" />
                                {t('pricebooks.detailsAction')}
                              </Button>
                              {canPublish ? (
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  magnetic={false}
                                  onClick={() =>
                                    setActionTarget({
                                      action: 'publish',
                                      pricebook,
                                    })
                                  }
                                  aria-label={t('pricebooks.lifecycle.publishAction')}
                                >
                                  <Rocket className="mr-2 h-4 w-4" />
                                  {t('pricebooks.lifecycle.publishAction')}
                                </Button>
                              ) : null}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </div>

            <OffersReferencePanel
              isLoading={offersQuery.isLoading}
              offers={offers}
            />
          </div>

          <PricebookDetailPanel
            pricebook={selectedPricebook}
            history={historyQuery.data}
            isHistoryLoading={historyQuery.isLoading}
            historyError={historyQuery.error}
            audit={auditQuery.data}
            isAuditLoading={auditQuery.isLoading}
            auditError={auditQuery.error}
            validation={validationQuery.data}
            isValidationLoading={validationQuery.isFetching}
            validationError={validationQuery.error}
            onValidate={handleValidateSelected}
            onOpenAction={(action, pricebook) =>
              setActionTarget({ action, pricebook })
            }
          />
        </div>
      </CommercePageShell>

      <PricebookEditorModal
        isOpen={isCreateOpen}
        isSubmitting={createMutation.isPending}
        onClose={() => setIsCreateOpen(false)}
        onSubmit={async (payload) => {
          await createMutation.mutateAsync(payload);
        }}
      />

      <PricebookLifecycleDialog
        key={
          actionTarget
            ? `${actionTarget.action}-${actionTarget.pricebook.id}`
            : 'closed'
        }
        isPending={lifecycleMutation.isPending}
        pricebooks={pricebooks}
        target={actionTarget}
        onClose={() => setActionTarget(null)}
        onConfirm={async (payload) => {
          if (!actionTarget) {
            return;
          }

          await lifecycleMutation.mutateAsync({
            payload,
            target: actionTarget,
          });
        }}
      />
    </>
  );
}

function OffersReferencePanel({
  isLoading,
  offers,
}: {
  isLoading: boolean;
  offers: Awaited<ReturnType<typeof offersApi.listAdmin>>['data'];
}) {
  const t = useTranslations('Commerce');

  return (
    <aside className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
        {t('pricebooks.offersTitle')}
      </h2>
      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
        {t('pricebooks.offersDescription')}
      </p>

      <div className="mt-5 grid min-w-0 gap-3 lg:grid-cols-2 2xl:grid-cols-1">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
            />
          ))
        ) : offers.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
            {t('pricebooks.offersEmpty')}
          </div>
        ) : (
          offers.slice(0, 6).map((offer) => (
            <div
              key={offer.id}
              className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                    {offer.display_name}
                  </p>
                  <p className="mt-2 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {offer.offer_key} / #{shortId(offer.id)}
                  </p>
                </div>
                <StatusChip
                  label={humanizeToken(offer.version_status)}
                  tone={offer.is_active ? 'success' : 'warning'}
                />
              </div>
              <p className="mt-3 text-xs font-mono leading-5 text-muted-foreground">
                {offer.sale_channels.join(', ') || t('common.emptyShort')}
              </p>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}

function PricebookDetailPanel({
  audit,
  auditError,
  history,
  historyError,
  isAuditLoading,
  isHistoryLoading,
  isValidationLoading,
  onOpenAction,
  onValidate,
  pricebook,
  validation,
  validationError,
}: {
  audit: AdminPricebookAuditResponse | undefined;
  auditError: Error | null;
  history: AdminPricebookHistoryResponse | null | undefined;
  historyError: Error | null;
  isAuditLoading: boolean;
  isHistoryLoading: boolean;
  isValidationLoading: boolean;
  onOpenAction: (
    action: LifecycleAction,
    pricebook: AdminCommercialPricebookRecord,
  ) => void;
  onValidate: () => void;
  pricebook: AdminCommercialPricebookRecord | null;
  validation: AdminPricebookValidationResponse | null | undefined;
  validationError: Error | null;
}) {
  const t = useTranslations('Commerce');

  if (!pricebook) {
    return (
      <aside className="min-w-0 rounded-2xl border border-dashed border-grid-line/30 bg-terminal-surface/35 p-5 text-center text-sm font-mono text-muted-foreground backdrop-blur">
        {t('pricebooks.detailsEmpty')}
      </aside>
    );
  }

  const canPublish = canRunLifecycleAction('publish', pricebook);
  const canSchedule = canRunLifecycleAction('schedule', pricebook);
  const canRollback = canRunLifecycleAction('rollback', pricebook);
  const lifecycleUnavailable = t('pricebooks.lifecycle.unavailableForStatus', {
    status: humanizeToken(pricebook.lifecycle_status),
  });

  return (
    <aside className="min-w-0 space-y-6">
      <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('pricebooks.detailsTitle')}
            </h2>
            <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {pricebook.pricebook_key} / #{shortId(pricebook.id)}
            </p>
          </div>
          <StatusChip
            label={humanizeToken(pricebook.lifecycle_status)}
            tone={pricebookTone(pricebook)}
          />
        </div>

        <div className="mt-5 grid gap-3">
          <InfoLine
            label={t('pricebooks.fields.displayName')}
            value={pricebook.display_name}
          />
          <InfoLine
            label={t('pricebooks.fields.storefrontId')}
            value={pricebook.storefront_id}
          />
          <InfoLine
            label={t('pricebooks.fields.currencyCode')}
            value={pricebook.currency_code}
          />
          <InfoLine
            label={t('pricebooks.fields.regionCode')}
            value={pricebook.region_code ?? t('common.emptyShort')}
          />
        </div>

        <div className="mt-5 grid gap-2">
          <Button
            type="button"
            magnetic={false}
            onClick={onValidate}
            disabled={isValidationLoading}
            aria-label={t('pricebooks.validation.validateAction')}
          >
            <ClipboardCheck className="mr-2 h-4 w-4" />
            {isValidationLoading
              ? t('pricebooks.validation.validating')
              : t('pricebooks.validation.validateAction')}
          </Button>
          <div className="grid gap-2 sm:grid-cols-3">
            <Button
              type="button"
              variant="ghost"
              magnetic={false}
              disabled={!canPublish}
              title={canPublish ? undefined : lifecycleUnavailable}
              onClick={() => onOpenAction('publish', pricebook)}
              aria-label={
                canPublish
                  ? t('pricebooks.lifecycle.publishAction')
                  : lifecycleUnavailable
              }
            >
              <Rocket className="mr-2 h-4 w-4" />
              {t('pricebooks.lifecycle.publishAction')}
            </Button>
            <Button
              type="button"
              variant="ghost"
              magnetic={false}
              disabled={!canSchedule}
              title={canSchedule ? undefined : lifecycleUnavailable}
              onClick={() => onOpenAction('schedule', pricebook)}
              aria-label={
                canSchedule
                  ? t('pricebooks.lifecycle.scheduleAction')
                  : lifecycleUnavailable
              }
            >
              <CalendarClock className="mr-2 h-4 w-4" />
              {t('pricebooks.lifecycle.scheduleAction')}
            </Button>
            <Button
              type="button"
              variant="destructive"
              magnetic={false}
              disabled={!canRollback}
              title={canRollback ? undefined : lifecycleUnavailable}
              onClick={() => onOpenAction('rollback', pricebook)}
              aria-label={
                canRollback
                  ? t('pricebooks.lifecycle.rollbackAction')
                  : lifecycleUnavailable
              }
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              {t('pricebooks.lifecycle.rollbackAction')}
            </Button>
          </div>
        </div>
      </section>

      <ValidationPanel
        error={validationError}
        isLoading={isValidationLoading}
        validation={validation}
      />

      <HistoryPanel
        error={historyError}
        history={history}
        isLoading={isHistoryLoading}
      />

      <AuditPanel
        audit={audit}
        error={auditError}
        isLoading={isAuditLoading}
      />
    </aside>
  );
}

function ValidationPanel({
  error,
  isLoading,
  validation,
}: {
  error: Error | null;
  isLoading: boolean;
  validation: AdminPricebookValidationResponse | null | undefined;
}) {
  const t = useTranslations('Commerce');

  return (
    <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
        {t('pricebooks.validation.title')}
      </h2>

      {error ? (
        <div
          className="mt-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
          role="alert"
          aria-live="assertive"
        >
          {error.message}
        </div>
      ) : null}

      {isLoading ? (
        <div className="mt-4 h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      ) : validation ? (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <StatusChip
              label={
                validation.valid
                  ? t('pricebooks.validation.valid')
                  : t('pricebooks.validation.invalid')
              }
              tone={validation.valid ? 'success' : 'danger'}
            />
            <span className="text-xs font-mono text-muted-foreground">
              {formatDateTime(validation.checked_at)}
            </span>
          </div>
          {validation.issues.length === 0 ? (
            <div className="min-w-0 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-muted-foreground">
              {t('pricebooks.validation.noIssues')}
            </div>
          ) : (
            validation.issues.map((issue, index) => (
              <div
                key={`${issue.code}-${issue.field ?? index}`}
                className="min-w-0 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <StatusChip
                    label={humanizeToken(issue.code)}
                    tone={issueTone(issue.severity)}
                  />
                  <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {issue.field ?? t('common.emptyShort')}
                  </span>
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-white">
                  {issue.message}
                </p>
                {issue.remediation ? (
                  <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                    {issue.remediation}
                  </p>
                ) : null}
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-5 text-sm font-mono text-muted-foreground">
          {t('pricebooks.validation.idle')}
        </div>
      )}
    </section>
  );
}

function HistoryPanel({
  error,
  history,
  isLoading,
}: {
  error: Error | null;
  history: AdminPricebookHistoryResponse | null | undefined;
  isLoading: boolean;
}) {
  const t = useTranslations('Commerce');
  const versions = history?.versions ?? [];

  return (
    <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex items-center gap-3">
        <History className="h-4 w-4 text-neon-cyan" />
        <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
          {t('pricebooks.historyTitle')}
        </h2>
      </div>

      {error ? (
        <div
          className="mt-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
          role="alert"
          aria-live="assertive"
        >
          {error.message}
        </div>
      ) : null}

      {isLoading ? (
        <div className="mt-4 h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      ) : versions.length === 0 ? (
        <div className="mt-4 rounded-xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-5 text-sm font-mono text-muted-foreground">
          {t('pricebooks.historyEmpty')}
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {versions.slice(0, 6).map((version) => (
            <div
              key={version.id}
              className="min-w-0 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-sm font-mono text-white">
                  #{shortId(version.id)}
                </span>
                <StatusChip
                  label={humanizeToken(version.lifecycle_status)}
                  tone={pricebookTone(version)}
                />
              </div>
              <p className="mt-2 text-xs font-mono text-muted-foreground">
                {formatDateTime(version.effective_from)} /{' '}
                {formatDateTime(version.effective_to)}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function AuditPanel({
  audit,
  error,
  isLoading,
}: {
  audit: AdminPricebookAuditResponse | undefined;
  error: Error | null;
  isLoading: boolean;
}) {
  const t = useTranslations('Commerce');
  const entries = audit ?? [];

  return (
    <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
        {t('pricebooks.auditTitle')}
      </h2>

      {error ? (
        <div
          className="mt-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
          role="alert"
          aria-live="assertive"
        >
          {error.message}
        </div>
      ) : null}

      {isLoading ? (
        <div className="mt-4 h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      ) : entries.length === 0 ? (
        <div className="mt-4 rounded-xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-5 text-sm font-mono text-muted-foreground">
          {t('pricebooks.auditEmpty')}
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="min-w-0 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3"
            >
              <p className="text-sm font-mono text-white">
                {humanizeToken(entry.action)}
              </p>
              <p className="mt-2 text-xs font-mono text-muted-foreground">
                {formatDateTime(entry.created_at)} / #{shortId(entry.id)}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function PricebookLifecycleDialog({
  isPending,
  onClose,
  onConfirm,
  pricebooks,
  target,
}: {
  isPending: boolean;
  onClose: () => void;
  onConfirm: (payload: LifecycleActionPayload) => Promise<void> | void;
  pricebooks: AdminCommercialPricebookRecord[];
  target: LifecycleActionTarget | null;
}) {
  const t = useTranslations('Commerce');
  const [effectiveFrom, setEffectiveFrom] = useState('');
  const [scheduledFor, setScheduledFor] = useState('');
  const [reason, setReason] = useState('');
  const [targetPricebookId, setTargetPricebookId] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  if (!target) {
    return null;
  }

  const rollbackCandidates = pricebooks.filter(
    (pricebook) =>
      pricebook.pricebook_key === target.pricebook.pricebook_key
      && pricebook.id !== target.pricebook.id,
  );
  const isPublish = target.action === 'publish';
  const isSchedule = target.action === 'schedule';
  const isRollback = target.action === 'rollback';
  const dialogToneClassName = isRollback
    ? 'border-neon-pink/30 bg-neon-pink/10 text-neon-pink'
    : 'border-amber-400/30 bg-amber-400/10 text-amber-200';
  const targetVersion = targetPricebookId
    ? pricebooks.find((pricebook) => pricebook.id === targetPricebookId)
    : null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);

    if (isSchedule && !scheduledFor.trim()) {
      setLocalError(t('pricebooks.lifecycle.scheduleRequired'));
      return;
    }

    if (isRollback && !reason.trim()) {
      setLocalError(t('pricebooks.lifecycle.rollbackReasonRequired'));
      return;
    }

    if (reason.length > MAX_CHANGE_REASON_LENGTH) {
      setLocalError(t('pricebooks.lifecycle.reasonTooLong'));
      return;
    }

    await onConfirm({
      effectiveFrom,
      reason: reason.trim() || undefined,
      scheduledFor,
      targetPricebookId,
    });
  }

  return (
    <Modal
      isOpen={Boolean(target)}
      onClose={onClose}
      title={t(`pricebooks.lifecycle.${target.action}Title`)}
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className={`rounded-2xl border p-4 text-sm font-mono leading-6 ${dialogToneClassName}`}>
          <p>{t(`pricebooks.lifecycle.${target.action}Description`)}</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <InfoLine
              label={t('pricebooks.lifecycle.currentVersion')}
              value={`${target.pricebook.pricebook_key} / #${shortId(target.pricebook.id)}`}
            />
            <InfoLine
              label={t('common.status')}
              value={humanizeToken(target.pricebook.lifecycle_status)}
            />
          </div>
        </div>

        {isPublish ? (
          <label className="block space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('pricebooks.lifecycle.effectiveFrom')}
            </span>
            <Input
              type="datetime-local"
              value={effectiveFrom}
              onChange={(event) => setEffectiveFrom(event.target.value)}
            />
          </label>
        ) : null}

        {isSchedule ? (
          <label className="block space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('pricebooks.lifecycle.scheduledFor')}
            </span>
            <Input
              type="datetime-local"
              value={scheduledFor}
              onChange={(event) => setScheduledFor(event.target.value)}
              required
            />
          </label>
        ) : null}

        {isRollback ? (
          <>
            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('pricebooks.lifecycle.rollbackTarget')}
              </span>
              <select
                value={targetPricebookId}
                onChange={(event) => setTargetPricebookId(event.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="">
                  {t('pricebooks.lifecycle.rollbackLatest')}
                </option>
                {rollbackCandidates.map((pricebook) => (
                  <option key={pricebook.id} value={pricebook.id}>
                    {shortId(pricebook.id)} / {humanizeToken(pricebook.lifecycle_status)}
                  </option>
                ))}
              </select>
            </label>

            <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('pricebooks.lifecycle.targetVersion')}
              </p>
              <p className="mt-2 break-words text-sm font-mono text-white">
                {targetVersion
                  ? `${targetVersion.pricebook_key} / #${shortId(targetVersion.id)} / ${humanizeToken(targetVersion.lifecycle_status)}`
                  : t('pricebooks.lifecycle.rollbackLatestSummary')}
              </p>
            </div>
          </>
        ) : null}

        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {isRollback
              ? t('pricebooks.lifecycle.reasonRequiredLabel')
              : t('pricebooks.lifecycle.reasonOptionalLabel')}
          </span>
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={4}
            placeholder={t('pricebooks.lifecycle.reasonPlaceholder')}
            required={isRollback}
            maxLength={MAX_CHANGE_REASON_LENGTH}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
          <span className="block text-xs font-mono leading-5 text-muted-foreground">
            {isRollback
              ? t('pricebooks.lifecycle.reasonRequiredHelp')
              : t('pricebooks.lifecycle.reasonOptionalHelp')}
          </span>
        </label>

        {localError ? (
          <div
            className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
            role="alert"
            aria-live="assertive"
          >
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
            aria-label={t('common.cancel')}
          >
            {t('common.cancel')}
          </Button>
          <Button
            type="submit"
            variant={isRollback ? 'destructive' : 'default'}
            magnetic={false}
            disabled={isPending}
            aria-label={
              isPending
                ? t('common.saving')
                : t(`pricebooks.lifecycle.${target.action}Action`)
            }
          >
            {isPending
              ? t('common.saving')
              : t(`pricebooks.lifecycle.${target.action}Action`)}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 break-words text-sm font-mono text-white">{value}</p>
    </div>
  );
}
