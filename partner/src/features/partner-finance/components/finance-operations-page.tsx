'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowUpRight,
  BadgeCheck,
  Clock3,
  Landmark,
  ShieldAlert,
  Wallet,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import {
  getPartnerFinanceCapabilities,
  getPartnerFinanceSurfaceMode,
} from '@/features/partner-operations/lib/reporting-finance-capabilities';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  buildPartnerFinancePayoutAccountNotes,
  getPartnerFinancePayoutAccountCurrency,
  getPartnerFinancePayoutHistoryTone,
} from '@/features/partner-finance/lib/finance-contract';

const ACCOUNT_BADGE_STYLES = {
  blocked: 'text-neon-pink',
  missing: 'text-muted-foreground',
  pending_review: 'text-neon-cyan',
  ready: 'text-matrix-green',
} as const;

const HISTORY_BADGE_STYLES = {
  blocked: 'text-neon-pink',
  failed: 'text-neon-pink',
  in_flight: 'text-neon-cyan',
  paid: 'text-matrix-green',
  pending_review: 'text-neon-cyan',
  queued: 'text-neon-purple',
} as const;

const PAYOUT_RAIL_OPTIONS = [
  { value: 'bank_wire', labelKey: 'bankWire' },
  { value: 'crypto_usdt', labelKey: 'cryptoUsdt' },
  { value: 'manual', labelKey: 'manualInvoice' },
] as const;

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(parsed);
}

export function FinanceOperationsPage() {
  const t = useTranslations('Partner.finance');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const {
    state,
    activeWorkspace,
    blockedReasons,
    queries: {
      payoutAccountsQuery,
    },
  } = usePartnerPortalRuntimeState();
  const mode = getPartnerFinanceSurfaceMode(state);
  const capabilities = getPartnerFinanceCapabilities(state);

  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [formState, setFormState] = useState({
    payoutRail: 'bank_wire',
    displayLabel: '',
    destinationReference: '',
    currency: state.financeSnapshot.currency || 'USD',
    makeDefault: true,
  });

  const capabilityAvailability = useMemo(
    () => new Map(capabilities.map((item) => [item.key, item.availability])),
    [capabilities],
  );

  const blockedFinanceReasons = useMemo(
    () => blockedReasons.filter((item) => item.route_slug === 'finance'),
    [blockedReasons],
  );

  const workspaceId = activeWorkspace?.id ?? state.activeWorkspaceId ?? null;
  const payoutAccounts = useMemo(
    () => payoutAccountsQuery.data ?? [],
    [payoutAccountsQuery.data],
  );
  const selectedAccount = useMemo(() => {
    const effectiveId = selectedAccountId ?? payoutAccounts[0]?.id ?? null;
    return payoutAccounts.find((item) => item.id === effectiveId) ?? null;
  }, [payoutAccounts, selectedAccountId]);

  const selectedAccountEligibilityQuery = useQuery({
    queryKey: [
      'partner-portal',
      'workspace-payout-account-eligibility',
      workspaceId,
      selectedAccount?.id ?? null,
    ],
    queryFn: async () => {
      if (!workspaceId || !selectedAccount?.id) {
        return null;
      }
      const response = await partnerPortalApi.getWorkspacePayoutAccountEligibility(
        workspaceId,
        selectedAccount.id,
      );
      return response.data;
    },
    enabled: Boolean(workspaceId && selectedAccount?.id),
    staleTime: 30_000,
    retry: false,
  });

  const payoutHistoryQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-payout-history', workspaceId],
    queryFn: async () => {
      if (!workspaceId) {
        return null;
      }
      const response = await partnerPortalApi.listWorkspacePayoutHistory(workspaceId, {
        limit: 50,
        offset: 0,
      });
      return response.data;
    },
    enabled: Boolean(workspaceId),
    staleTime: 30_000,
    retry: false,
  });

  const createPayoutAccountMutation = useMutation({
    mutationFn: async () => {
      if (!workspaceId) {
        throw new Error('Workspace is required before creating a payout account.');
      }

      return partnerPortalApi.createWorkspacePayoutAccount(workspaceId, {
        payout_rail: formState.payoutRail,
        display_label: formState.displayLabel.trim(),
        destination_reference: formState.destinationReference.trim(),
        destination_metadata: {
          currency: formState.currency.trim().toUpperCase(),
        },
        make_default: formState.makeDefault,
      });
    },
    onSuccess: async (response) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'workspace-payout-accounts', workspaceId],
        }),
        queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'workspace-payout-history', workspaceId],
        }),
        queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'workspace-notifications'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'session-bootstrap'],
        }),
      ]);

      setSelectedAccountId(response.data.id);
      setFormState((current) => ({
        ...current,
        displayLabel: '',
        destinationReference: '',
      }));
    },
  });

  const makeDefaultMutation = useMutation({
    mutationFn: async (payoutAccountId: string) => {
      if (!workspaceId) {
        throw new Error('Workspace is required before updating the default payout account.');
      }

      return partnerPortalApi.makeWorkspacePayoutAccountDefault(workspaceId, payoutAccountId);
    },
    onSuccess: async (response) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'workspace-payout-accounts', workspaceId],
        }),
        queryClient.invalidateQueries({
          queryKey: [
            'partner-portal',
            'workspace-payout-account-eligibility',
            workspaceId,
            response.data.id,
          ],
        }),
        queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'workspace-notifications'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'session-bootstrap'],
        }),
      ]);

      setSelectedAccountId(response.data.id);
    },
  });

  return (
    <PartnerRouteGuard route="finance" title={t('title')}>
      {(access) => {
        const canManageAccounts = (
          access === 'write'
          || access === 'admin'
        ) && capabilityAvailability.get('payout_accounts') !== 'blocked';
        const payoutHistory = payoutHistoryQuery.data ?? [];
        const selectedAccountNotes = selectedAccount
          ? buildPartnerFinancePayoutAccountNotes({
            account: selectedAccount,
            eligibility: selectedAccountEligibilityQuery.data,
          })
          : [];

        return (
          <section className="space-y-6">
            <header className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                    {t('eyebrow')}
                  </p>
                  <h1 className="mt-2 text-2xl font-display tracking-[0.16em] text-white md:text-3xl">
                    {t('title')}
                  </h1>
                  <p className="mt-3 max-w-4xl text-sm font-mono leading-6 text-muted-foreground">
                    {t('subtitle')}
                  </p>
                </div>

                <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[360px]">
                  <div className="flex items-center justify-between gap-3">
                    <span>{t('summary.routeAccess')}</span>
                    <span className="text-neon-cyan">
                      {portalT(`routeAccess.${access}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.financeReadiness')}</span>
                    <span className="text-foreground">
                      {portalT(`financeStates.${state.financeReadiness}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.surfaceMode')}</span>
                    <span className="text-foreground">
                      {portalT(`financeModes.${mode}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.accounts')}</span>
                    <span className="text-foreground">{payoutAccounts.length}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.history')}</span>
                    <span className="text-foreground">{payoutHistory.length}</span>
                  </div>
                </div>
              </div>
            </header>

            {blockedFinanceReasons.length > 0 ? (
              <article className="rounded-[1.5rem] border border-neon-pink/25 bg-neon-pink/10 p-5 shadow-[0_0_24px_rgba(255,0,255,0.12)]">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="mt-0.5 h-5 w-5 text-neon-pink" />
                  <div className="space-y-2">
                    <h2 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {t('blocked.title')}
                    </h2>
                    <p className="text-sm font-mono leading-6 text-muted-foreground">
                      {t('blocked.description')}
                    </p>
                    <ul className="space-y-2 text-sm font-mono text-foreground/90">
                      {blockedFinanceReasons.map((item) => (
                        <li key={`${item.code}:${item.route_slug ?? 'route'}`}>
                          {item.code}
                          {(item.notes?.length ?? 0) > 0 ? ` — ${item.notes?.join(' ')}` : ''}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </article>
            ) : null}

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  {t('snapshot.available')}
                </p>
                <p className="mt-3 text-2xl font-display tracking-[0.14em] text-white">
                  {state.financeSnapshot.availableEarnings}
                </p>
              </article>
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  {t('snapshot.onHold')}
                </p>
                <p className="mt-3 text-2xl font-display tracking-[0.14em] text-white">
                  {state.financeSnapshot.onHoldEarnings}
                </p>
              </article>
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  {t('snapshot.reserves')}
                </p>
                <p className="mt-3 text-2xl font-display tracking-[0.14em] text-white">
                  {state.financeSnapshot.reserves}
                </p>
              </article>
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  {t('snapshot.forecast')}
                </p>
                <p className="mt-3 text-2xl font-display tracking-[0.14em] text-white">
                  {state.financeSnapshot.nextPayoutForecast}
                </p>
              </article>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
                <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                  <Landmark className="h-5 w-5 text-neon-cyan" />
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('statements.title')}
                    </h2>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('statements.description')}
                    </p>
                  </div>
                </div>

                <div className="mt-5 space-y-3">
                  {state.financeStatements.length > 0 ? state.financeStatements.map((statement) => (
                    <article
                      key={statement.id}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                    >
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                            {statement.periodLabel}
                          </h3>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {statement.notes[0] ?? t('statements.emptyState')}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {portalT(`financeStatementStatuses.${statement.status}`)}
                          </p>
                          <p className="mt-2 text-sm font-mono text-muted-foreground">
                            {statement.currency}
                          </p>
                        </div>
                      </div>
                      <dl className="mt-4 grid gap-3 text-sm font-mono text-muted-foreground md:grid-cols-4">
                        <div>
                          <dt>{t('statements.gross')}</dt>
                          <dd className="mt-1 text-foreground">{statement.gross}</dd>
                        </div>
                        <div>
                          <dt>{t('statements.net')}</dt>
                          <dd className="mt-1 text-foreground">{statement.net}</dd>
                        </div>
                        <div>
                          <dt>{t('statements.available')}</dt>
                          <dd className="mt-1 text-foreground">{statement.available}</dd>
                        </div>
                        <div>
                          <dt>{t('statements.onHold')}</dt>
                          <dd className="mt-1 text-foreground">{statement.onHold}</dd>
                        </div>
                      </dl>
                    </article>
                  )) : (
                    <div className="rounded-2xl border border-dashed border-grid-line/20 bg-terminal-surface/20 p-5 text-sm font-mono text-muted-foreground">
                      {t('statements.emptyState')}
                    </div>
                  )}
                </div>
              </article>

              <div className="space-y-6">
                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <Wallet className="h-5 w-5 text-neon-purple" />
                    <div>
                      <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                        {t('accounts.title')}
                      </h2>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {t('accounts.description')}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    {payoutAccounts.length > 0 ? payoutAccounts.map((account) => {
                      const portalStateAccount = state.payoutAccounts.find((item) => item.id === account.id);
                      const badgeState = portalStateAccount?.status ?? 'pending_review';
                      const badgeClass = ACCOUNT_BADGE_STYLES[badgeState];
                      const isSelected = selectedAccount?.id === account.id;

                      return (
                        <button
                          key={account.id}
                          type="button"
                          onClick={() => setSelectedAccountId(account.id)}
                          className={`w-full rounded-xl border p-4 text-left transition ${
                            isSelected
                              ? 'border-neon-cyan/40 bg-terminal-bg/80 shadow-[0_0_20px_rgba(0,255,255,0.1)]'
                              : 'border-grid-line/20 bg-terminal-bg/55 hover:border-neon-cyan/25'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {account.display_label}
                            </p>
                            <span className={`text-[11px] font-mono uppercase tracking-[0.18em] ${badgeClass}`}>
                              {portalT(`payoutAccountStatuses.${badgeState}`)}
                            </span>
                          </div>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {account.payout_rail} · {getPartnerFinancePayoutAccountCurrency(account)}
                          </p>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {account.masked_destination}
                          </p>
                        </button>
                      );
                    }) : (
                      <div className="rounded-xl border border-dashed border-grid-line/20 bg-terminal-bg/40 p-4 text-sm font-mono text-muted-foreground">
                        {t('accounts.emptyState')}
                      </div>
                    )}
                  </div>

                  {selectedAccount ? (
                    <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-bg/70 p-4">
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                            {selectedAccount.display_label}
                          </h3>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {t('accounts.detail.currency', {
                              value: getPartnerFinancePayoutAccountCurrency(selectedAccount),
                            })}
                          </p>
                        </div>

                        {canManageAccounts && !selectedAccount.is_default ? (
                          <button
                            type="button"
                            onClick={() => makeDefaultMutation.mutate(selectedAccount.id)}
                            disabled={makeDefaultMutation.isPending}
                            className="inline-flex items-center justify-center rounded-full border border-neon-cyan/30 px-3 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition hover:border-neon-cyan/60 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {makeDefaultMutation.isPending
                              ? t('accounts.actions.settingDefault')
                              : t('accounts.actions.makeDefault')}
                          </button>
                        ) : null}
                      </div>

                      <dl className="mt-4 grid gap-3 text-sm font-mono text-muted-foreground md:grid-cols-2">
                        <div>
                          <dt>{t('accounts.review.verification')}</dt>
                          <dd className="mt-1 text-foreground">{selectedAccount.verification_status}</dd>
                        </div>
                        <div>
                          <dt>{t('accounts.review.approval')}</dt>
                          <dd className="mt-1 text-foreground">{selectedAccount.approval_status}</dd>
                        </div>
                        <div>
                          <dt>{t('accounts.review.verifiedAt')}</dt>
                          <dd className="mt-1 text-foreground">{formatTimestamp(selectedAccount.verified_at)}</dd>
                        </div>
                        <div>
                          <dt>{t('accounts.review.approvedAt')}</dt>
                          <dd className="mt-1 text-foreground">{formatTimestamp(selectedAccount.approved_at)}</dd>
                        </div>
                      </dl>

                      <div className="mt-4 space-y-2">
                        {selectedAccountNotes.map((note) => (
                          <p
                            key={note}
                            className="text-sm font-mono leading-6 text-muted-foreground"
                          >
                            {note}
                          </p>
                        ))}
                      </div>

                      <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                        <div className="flex items-center gap-3">
                          {selectedAccountEligibilityQuery.data?.eligible ? (
                            <BadgeCheck className="h-4 w-4 text-matrix-green" />
                          ) : (
                            <AlertTriangle className="h-4 w-4 text-neon-pink" />
                          )}
                          <div>
                            <h4 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {t('eligibility.title')}
                            </h4>
                            <p className="mt-1 text-sm font-mono leading-6 text-muted-foreground">
                              {t('eligibility.description')}
                            </p>
                          </div>
                        </div>

                        <div className="mt-4">
                          {selectedAccountEligibilityQuery.isPending ? (
                            <p className="text-sm font-mono text-muted-foreground">
                              {t('eligibility.loading')}
                            </p>
                          ) : selectedAccountEligibilityQuery.isError ? (
                            <p className="text-sm font-mono text-neon-pink">
                              {t('eligibility.error')}
                            </p>
                          ) : selectedAccountEligibilityQuery.data ? (
                            <>
                              <p className={`text-sm font-mono ${
                                selectedAccountEligibilityQuery.data.eligible
                                  ? 'text-matrix-green'
                                  : 'text-neon-pink'
                              }`}>
                                {selectedAccountEligibilityQuery.data.eligible
                                  ? t('eligibility.eligible')
                                  : t('eligibility.ineligible')}
                              </p>
                              <p className="mt-2 text-sm font-mono text-muted-foreground">
                                {t('eligibility.checkedAt', {
                                  value: formatTimestamp(selectedAccountEligibilityQuery.data.checked_at),
                                })}
                              </p>
                              <ul className="mt-3 space-y-2 text-sm font-mono text-muted-foreground">
                                {(selectedAccountEligibilityQuery.data.reason_codes.length > 0
                                  ? selectedAccountEligibilityQuery.data.reason_codes
                                  : [t('eligibility.noBlockers')]).map((reason) => (
                                  <li key={reason}>{reason}</li>
                                ))}
                              </ul>
                            </>
                          ) : (
                            <p className="text-sm font-mono text-muted-foreground">
                              {t('eligibility.emptyState')}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {canManageAccounts ? (
                    <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-bg/70 p-4">
                      <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {t('accountForm.title')}
                      </h3>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {t('accountForm.description')}
                      </p>

                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <label className="space-y-2">
                          <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {t('accountForm.fields.payoutRail')}
                          </span>
                          <select
                            value={formState.payoutRail}
                            onChange={(event) => {
                              const nextRail = event.target.value;
                              setFormState((current) => ({
                                ...current,
                                payoutRail: nextRail,
                              }));
                            }}
                            className="w-full rounded-2xl border border-grid-line/20 bg-terminal-surface/40 px-4 py-3 text-sm font-mono text-foreground outline-none transition focus:border-neon-cyan/40"
                          >
                            {PAYOUT_RAIL_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {t(`accountForm.rails.${option.labelKey}`)}
                              </option>
                            ))}
                          </select>
                        </label>

                        <label className="space-y-2">
                          <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {t('accountForm.fields.currency')}
                          </span>
                          <input
                            value={formState.currency}
                            onChange={(event) => {
                              setFormState((current) => ({
                                ...current,
                                currency: event.target.value.toUpperCase(),
                              }));
                            }}
                            placeholder={t('accountForm.placeholders.currency')}
                            className="w-full rounded-2xl border border-grid-line/20 bg-terminal-surface/40 px-4 py-3 text-sm font-mono text-foreground outline-none transition placeholder:text-muted-foreground/60 focus:border-neon-cyan/40"
                          />
                        </label>

                        <label className="space-y-2 md:col-span-2">
                          <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {t('accountForm.fields.displayLabel')}
                          </span>
                          <input
                            value={formState.displayLabel}
                            onChange={(event) => {
                              setFormState((current) => ({
                                ...current,
                                displayLabel: event.target.value,
                              }));
                            }}
                            placeholder={t('accountForm.placeholders.displayLabel')}
                            className="w-full rounded-2xl border border-grid-line/20 bg-terminal-surface/40 px-4 py-3 text-sm font-mono text-foreground outline-none transition placeholder:text-muted-foreground/60 focus:border-neon-cyan/40"
                          />
                        </label>

                        <label className="space-y-2 md:col-span-2">
                          <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {t('accountForm.fields.destinationReference')}
                          </span>
                          <input
                            value={formState.destinationReference}
                            onChange={(event) => {
                              setFormState((current) => ({
                                ...current,
                                destinationReference: event.target.value,
                              }));
                            }}
                            placeholder={t('accountForm.placeholders.destinationReference')}
                            className="w-full rounded-2xl border border-grid-line/20 bg-terminal-surface/40 px-4 py-3 text-sm font-mono text-foreground outline-none transition placeholder:text-muted-foreground/60 focus:border-neon-cyan/40"
                          />
                        </label>
                      </div>

                      <label className="mt-4 flex items-center gap-3 text-sm font-mono text-muted-foreground">
                        <input
                          type="checkbox"
                          checked={formState.makeDefault}
                          onChange={(event) => {
                            setFormState((current) => ({
                              ...current,
                              makeDefault: event.target.checked,
                            }));
                          }}
                          className="h-4 w-4 rounded border-grid-line/20 bg-terminal-surface/40"
                        />
                        <span>{t('accountForm.fields.makeDefault')}</span>
                      </label>

                      {createPayoutAccountMutation.isError ? (
                        <p className="mt-4 text-sm font-mono text-neon-pink">
                          {t('accountForm.error')}
                        </p>
                      ) : null}
                      {createPayoutAccountMutation.isSuccess ? (
                        <p className="mt-4 text-sm font-mono text-matrix-green">
                          {t('accountForm.success')}
                        </p>
                      ) : null}

                      <div className="mt-5">
                        <button
                          type="button"
                          onClick={() => createPayoutAccountMutation.mutate()}
                          disabled={
                            createPayoutAccountMutation.isPending
                            || formState.displayLabel.trim().length === 0
                            || formState.destinationReference.trim().length === 0
                          }
                          className="inline-flex items-center justify-center rounded-full border border-neon-cyan/30 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition hover:border-neon-cyan/60 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {createPayoutAccountMutation.isPending
                            ? t('accountForm.actions.submitting')
                            : t('accountForm.actions.submit')}
                        </button>
                      </div>
                    </div>
                  ) : null}
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <Clock3 className="h-5 w-5 text-neon-cyan" />
                    <div>
                      <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                        {t('history.title')}
                      </h2>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {t('history.description')}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    {payoutHistoryQuery.isPending ? (
                      <div className="rounded-xl border border-dashed border-grid-line/20 bg-terminal-bg/40 p-4 text-sm font-mono text-muted-foreground">
                        {t('history.loading')}
                      </div>
                    ) : payoutHistoryQuery.isError ? (
                      <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
                        {t('history.error')}
                      </div>
                    ) : payoutHistory.length > 0 ? payoutHistory.map((item) => {
                      const tone = getPartnerFinancePayoutHistoryTone(item);

                      return (
                        <article
                          key={item.id}
                          className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                        >
                          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div>
                              <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                                {item.statement_key}
                              </h3>
                              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                                {item.payout_account_label ?? t('history.labels.noAccountLabel')}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className={`text-[11px] font-mono uppercase tracking-[0.18em] ${HISTORY_BADGE_STYLES[tone]}`}>
                                {t(`history.lifecycle.${tone}`)}
                              </p>
                              <p className="mt-2 text-sm font-mono text-foreground">
                                {item.amount.toFixed(2)} {item.currency_code}
                              </p>
                            </div>
                          </div>

                          <dl className="mt-4 grid gap-3 text-sm font-mono text-muted-foreground md:grid-cols-2">
                            <div>
                              <dt>{t('history.labels.instructionStatus')}</dt>
                              <dd className="mt-1 text-foreground">{item.instruction_status}</dd>
                            </div>
                            <div>
                              <dt>{t('history.labels.executionStatus')}</dt>
                              <dd className="mt-1 text-foreground">{item.execution_status ?? '—'}</dd>
                            </div>
                            <div>
                              <dt>{t('history.labels.createdAt')}</dt>
                              <dd className="mt-1 text-foreground">{formatTimestamp(item.created_at)}</dd>
                            </div>
                            <div>
                              <dt>{t('history.labels.updatedAt')}</dt>
                              <dd className="mt-1 text-foreground">{formatTimestamp(item.updated_at)}</dd>
                            </div>
                            <div>
                              <dt>{t('history.labels.executionMode')}</dt>
                              <dd className="mt-1 text-foreground">{item.execution_mode ?? '—'}</dd>
                            </div>
                            <div>
                              <dt>{t('history.labels.externalReference')}</dt>
                              <dd className="mt-1 text-foreground">{item.external_reference ?? '—'}</dd>
                            </div>
                          </dl>

                          {item.notes.length > 0 ? (
                            <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                              {item.notes.map((note) => (
                                <li key={note}>{note}</li>
                              ))}
                            </ul>
                          ) : null}
                        </article>
                      );
                    }) : (
                      <div className="rounded-xl border border-dashed border-grid-line/20 bg-terminal-bg/40 p-4 text-sm font-mono text-muted-foreground">
                        {t('history.emptyState')}
                      </div>
                    )}
                  </div>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('capabilities.title')}
                  </h2>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t(`modes.${mode}`)}
                  </p>
                  <ul className="mt-4 space-y-3">
                    {capabilities.map((capability) => (
                      <li
                        key={capability.key}
                        className="flex items-center justify-between gap-3 rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3"
                      >
                        <span className="text-sm font-mono text-foreground/90">
                          {t(`capabilities.items.${capability.key}`)}
                        </span>
                        <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                          {portalT(`operationalCapabilityAvailability.${capability.availability}`)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('links.title')}
                  </h2>
                  <div className="mt-4 flex flex-col gap-3">
                    <Link href="/analytics" className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4">
                      <span>{t('links.analytics')}</span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                    <Link href="/cases" className="inline-flex items-center gap-2 text-sm font-mono text-neon-purple underline underline-offset-4">
                      <span>{t('links.cases')}</span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                    <Link href="/legal" className="inline-flex items-center gap-2 text-sm font-mono text-matrix-green underline underline-offset-4">
                      <span>{t('links.legal')}</span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </article>
              </div>
            </div>
          </section>
        );
      }}
    </PartnerRouteGuard>
  );
}
