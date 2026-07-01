'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ClipboardCheck,
  FileSearch,
  Play,
  RefreshCw,
  ShieldAlert,
  SlidersHorizontal,
  XCircle,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import {
  type CreateVpnTesterRunRequest,
  type VpnTesterRun,
  vpnTesterApi,
} from '@/lib/api/infrastructure';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import { useAuthStore } from '@/stores/auth-store';
import {
  type AdminPermission,
  hasAdminPermission,
  isAdminRole,
} from '@/shared/lib/admin-rbac';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

type RunMode = CreateVpnTesterRunRequest['mode'];
type TabKey =
  | 'overview'
  | 'runs'
  | 'routeMatrix'
  | 'tariffs'
  | 'schedules'
  | 'releaseGate'
  | 'evidence'
  | 'balancer'
  | 'settings';

const RUN_MODES: RunMode[] = [
  'contract',
  'runtime',
  'all_tariffs',
  'balancer_preview',
];

const TABS: TabKey[] = [
  'overview',
  'runs',
  'routeMatrix',
  'tariffs',
  'schedules',
  'releaseGate',
  'evidence',
  'balancer',
  'settings',
];

function statusTone(status: string) {
  if (status === 'pass') return 'success' as const;
  if (status === 'queued' || status === 'running') return 'info' as const;
  if (status === 'degraded' || status === 'skipped') return 'warning' as const;
  return 'danger' as const;
}

function roleHas(role: string | null | undefined, permission: AdminPermission): boolean {
  return isAdminRole(role) && hasAdminPermission(role, permission);
}

function asNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function shortId(value: string | null | undefined): string {
  if (!value) return '—';
  return value.length > 12 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'short',
    timeStyle: 'medium',
  }).format(date);
}

function safeString(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.map((item) => safeString(item)).join(', ');
  return String(value);
}

function JsonPreview({ value }: { value: unknown }) {
  return (
    <pre className="max-h-72 overflow-auto rounded-lg border border-grid-line/20 bg-terminal-bg/70 p-3 text-xs leading-5 text-muted-foreground">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function VpnTesterConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const role = useAuthStore((state) => state.user?.role);
  const [suiteKey, setSuiteKey] = useState('premium_smart_ru_v1');
  const [mode, setMode] = useState<RunMode>('contract');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState('');
  const [dismissReason, setDismissReason] = useState('');

  const canMutateRuns = roleHas(role, 'server_update') || roleHas(role, 'manage_plans');
  const canMutateSchedules = roleHas(role, 'server_update') && roleHas(role, 'manage_plans');
  const canOverrideGate = role === 'super_admin' || role === 'owner/super_admin';
  const readOnlyReason = t('vpnTester.permission.readOnly');

  const overviewQuery = useQuery({
    queryKey: ['infrastructure', 'vpn-tester', 'overview'],
    queryFn: async () => (await vpnTesterApi.overview()).data,
    staleTime: 20_000,
  });

  const runsQuery = useQuery({
    queryKey: ['infrastructure', 'vpn-tester', 'runs'],
    queryFn: async () => (await vpnTesterApi.listRuns({ limit: 30 })).data,
    staleTime: 15_000,
  });

  const schedulesQuery = useQuery({
    queryKey: ['infrastructure', 'vpn-tester', 'schedules'],
    queryFn: async () => (await vpnTesterApi.listSchedules()).data,
    staleTime: 30_000,
  });

  const tariffsQuery = useQuery({
    queryKey: ['infrastructure', 'vpn-tester', 'tariffs'],
    queryFn: async () => (await vpnTesterApi.tariffMatrix()).data,
    staleTime: 30_000,
  });

  const routeMatrixQuery = useQuery({
    queryKey: ['infrastructure', 'vpn-tester', 'route-matrix'],
    queryFn: async () => (await vpnTesterApi.routeMatrix()).data,
    staleTime: 60_000,
  });

  const releaseGateQuery = useQuery({
    queryKey: ['infrastructure', 'vpn-tester', 'release-gate'],
    queryFn: async () => (await vpnTesterApi.releaseGate()).data,
    staleTime: 20_000,
  });

  const recommendationsQuery = useQuery({
    queryKey: ['infrastructure', 'vpn-tester', 'balancer', 'recommendations'],
    queryFn: async () => (await vpnTesterApi.listBalancerRecommendations({ limit: 25 })).data,
    staleTime: 30_000,
  });

  const selectedRunQuery = useQuery({
    queryKey: ['infrastructure', 'vpn-tester', 'run', selectedRunId],
    enabled: Boolean(selectedRunId),
    queryFn: async () => (await vpnTesterApi.getRun(selectedRunId ?? '')).data,
    staleTime: 10_000,
  });

  const invalidateAll = async () => {
    await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'vpn-tester'] });
  };

  const createRunMutation = useMutation({
    mutationFn: () => vpnTesterApi.createRun({
      suite_key: suiteKey,
      mode,
      context: { source: 'admin_console_v3' },
    }),
    onSuccess: async (response) => {
      setFeedback(t('vpnTester.feedback.runQueued'));
      setSelectedRunId(response.data.id);
      setActiveTab('runs');
      await invalidateAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const cancelRunMutation = useMutation({
    mutationFn: (runId: string) => vpnTesterApi.cancelRun(runId),
    onSuccess: async () => {
      setFeedback(t('vpnTester.feedback.runCancelled'));
      await invalidateAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const toggleScheduleMutation = useMutation({
    mutationFn: ({ enabled, scheduleKey }: { enabled: boolean; scheduleKey: string }) =>
      vpnTesterApi.updateSchedule(scheduleKey, { enabled }),
    onSuccess: async () => {
      setFeedback(t('vpnTester.feedback.scheduleUpdated'));
      await invalidateAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const overrideGateMutation = useMutation({
    mutationFn: () => vpnTesterApi.overrideReleaseGate({
      reason: overrideReason,
      ttl_minutes: 60,
    }),
    onSuccess: async () => {
      setFeedback(t('vpnTester.feedback.overrideRecorded'));
      setOverrideReason('');
      await invalidateAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const ackRecommendationMutation = useMutation({
    mutationFn: (recommendationId: string) =>
      vpnTesterApi.acknowledgeBalancerRecommendation(recommendationId),
    onSuccess: async () => {
      setFeedback(t('vpnTester.feedback.recommendationUpdated'));
      await invalidateAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const dismissRecommendationMutation = useMutation({
    mutationFn: (recommendationId: string) =>
      vpnTesterApi.dismissBalancerRecommendation(recommendationId, { reason: dismissReason || null }),
    onSuccess: async () => {
      setFeedback(t('vpnTester.feedback.recommendationUpdated'));
      setDismissReason('');
      await invalidateAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const overview = overviewQuery.data;
  const counts = overview?.counts ?? {};
  const runs = useMemo(
    () => runsQuery.data ?? overview?.latest_runs ?? [],
    [overview?.latest_runs, runsQuery.data],
  );
  const schedules = schedulesQuery.data ?? overview?.schedules ?? [];
  const tariffRows = tariffsQuery.data?.rows ?? [];
  const routeRows = routeMatrixQuery.data?.rows ?? [];
  const recommendations = recommendationsQuery.data ?? [];
  const selectedRun: VpnTesterRun | null = selectedRunQuery.data
    ?? runs.find((run) => run.id === selectedRunId)
    ?? null;

  const latestStatus = releaseGateQuery.data?.status ?? runs[0]?.status ?? 'queued';
  const totalFailures = useMemo(
    () => runs.reduce((sum, run) => sum + run.fail_count, 0),
    [runs],
  );

  return (
    <InfrastructurePageShell
      eyebrow={t('vpnTester.eyebrow')}
      title={t('vpnTester.title')}
      description={t('vpnTester.description')}
      icon={ClipboardCheck}
      actions={
        <Button
          magnetic={false}
          variant="ghost"
          onClick={() => {
            void invalidateAll();
          }}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          {t('vpnTester.actions.refresh')}
        </Button>
      }
      metrics={[
        {
          label: t('vpnTester.metrics.status'),
          value: t(`vpnTester.status.${latestStatus}`),
          hint: t('vpnTester.metrics.statusHint'),
          tone: releaseGateQuery.data?.blocking ? 'danger' : statusTone(latestStatus),
        },
        {
          label: t('vpnTester.metrics.runs'),
          value: String(counts.total ?? runs.length),
          hint: t('vpnTester.metrics.runsHint'),
          tone: 'info',
        },
        {
          label: t('vpnTester.metrics.failures'),
          value: String(totalFailures),
          hint: t('vpnTester.metrics.failuresHint'),
          tone: totalFailures > 0 ? 'danger' : 'success',
        },
        {
          label: t('vpnTester.metrics.routes'),
          value: String(routeMatrixQuery.data?.total ?? routeRows.length),
          hint: t('vpnTester.metrics.routesHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={
              activeTab === tab
                ? 'rounded-lg border border-neon-cyan/45 bg-neon-cyan/10 px-3 py-2 text-xs font-mono uppercase tracking-[0.12em] text-neon-cyan'
                : 'rounded-lg border border-grid-line/20 bg-terminal-bg/65 px-3 py-2 text-xs font-mono uppercase tracking-[0.12em] text-muted-foreground hover:border-grid-line/50 hover:text-white'
            }
          >
            {t(`vpnTester.tabs.${tab}`)}
          </button>
        ))}
      </div>

      {feedback ? (
        <p className="rounded-lg border border-grid-line/20 bg-terminal-bg/65 px-3 py-2 text-xs text-muted-foreground">
          {feedback}
        </p>
      ) : null}

      {activeTab === 'overview' ? (
        <div className="grid gap-6 xl:grid-cols-12">
          <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-display text-lg tracking-[0.14em] text-white">
                  {t('vpnTester.runBuilder.title')}
                </h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {canMutateRuns ? t('vpnTester.runBuilder.description') : readOnlyReason}
                </p>
              </div>
              <Play className="h-5 w-5 text-neon-cyan" />
            </div>

            <div className="mt-5 grid gap-4">
              <label className="grid gap-2 text-xs font-mono uppercase tracking-[0.14em] text-muted-foreground">
                {t('vpnTester.runBuilder.suite')}
                <select
                  value={suiteKey}
                  onChange={(event) => setSuiteKey(event.target.value)}
                  className="rounded-lg border border-grid-line/30 bg-terminal-bg/80 px-3 py-3 text-sm normal-case tracking-normal text-white outline-hidden focus:border-neon-cyan"
                >
                  <option value="premium_smart_ru_v1">{t('vpnTester.suites.premiumSmartRu')}</option>
                  <option value="all_tariffs_contract_v1">{t('vpnTester.suites.allTariffs')}</option>
                  <option value="default_subscription_smoke_v1">{t('vpnTester.suites.defaultSmoke')}</option>
                </select>
              </label>

              <div className="grid gap-2">
                <span className="text-xs font-mono uppercase tracking-[0.14em] text-muted-foreground">
                  {t('vpnTester.runBuilder.mode')}
                </span>
                <div className="grid gap-2 sm:grid-cols-4">
                  {RUN_MODES.map((candidate) => (
                    <button
                      key={candidate}
                      type="button"
                      onClick={() => setMode(candidate)}
                      className={
                        candidate === mode
                          ? 'rounded-lg border border-neon-cyan/45 bg-neon-cyan/10 px-3 py-2 text-xs font-mono uppercase tracking-[0.12em] text-neon-cyan'
                          : 'rounded-lg border border-grid-line/20 bg-terminal-bg/65 px-3 py-2 text-xs font-mono uppercase tracking-[0.12em] text-muted-foreground hover:border-grid-line/50 hover:text-white'
                      }
                    >
                      {t(`vpnTester.modes.${candidate}`)}
                    </button>
                  ))}
                </div>
              </div>

              <Button
                magnetic={false}
                onClick={() => createRunMutation.mutate()}
                disabled={!canMutateRuns || createRunMutation.isPending}
              >
                <Play className="mr-2 h-4 w-4" />
                {createRunMutation.isPending
                  ? t('vpnTester.actions.queueing')
                  : t('vpnTester.actions.queueRun')}
              </Button>
            </div>
          </section>

          <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-display text-lg tracking-[0.14em] text-white">
                  {t('vpnTester.releaseGate.title')}
                </h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {releaseGateQuery.data?.reason
                    ? t(`vpnTester.releaseGate.reasons.${releaseGateQuery.data.reason}`)
                    : t('vpnTester.releaseGate.description')}
                </p>
              </div>
              <InfrastructureStatusChip
                label={t(`vpnTester.status.${releaseGateQuery.data?.status ?? 'queued'}`)}
                tone={releaseGateQuery.data?.blocking ? 'danger' : statusTone(releaseGateQuery.data?.status ?? 'queued')}
              />
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                ['enabled', overview?.enabled],
                ['runtime', overview?.runtime_enabled],
                ['scheduled', overview?.scheduled_enabled],
                ['balancer', overview?.balancer_recommendations_enabled],
              ].map(([key, enabled]) => (
                <div
                  key={String(key)}
                  className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-3"
                >
                  <p className="text-[11px] font-mono uppercase tracking-[0.14em] text-muted-foreground">
                    {t(`vpnTester.flags.${key}`)}
                  </p>
                  <p className={enabled ? 'mt-2 text-sm text-matrix-green' : 'mt-2 text-sm text-amber-300'}>
                    {enabled ? t('common.enabled') : t('common.disabled')}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}

      {activeTab === 'runs' ? (
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-lg tracking-[0.14em] text-white">
                {t('vpnTester.runs.title')}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {t('vpnTester.runs.description')}
              </p>
            </div>
            <FileSearch className="h-5 w-5 text-neon-cyan" />
          </div>
          {runsQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-14 animate-pulse rounded-xl bg-terminal-bg/60" />
              ))}
            </div>
          ) : runs.length === 0 ? (
            <InfrastructureEmptyState label={t('vpnTester.runs.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('vpnTester.runs.run')}</TableHead>
                  <TableHead>{t('vpnTester.runs.suite')}</TableHead>
                  <TableHead>{t('vpnTester.runs.mode')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('vpnTester.runs.results')}</TableHead>
                  <TableHead>{t('common.updatedAt')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.id}>
                    <TableCell className="font-mono text-xs">{shortId(run.id)}</TableCell>
                    <TableCell>{run.suite_key}</TableCell>
                    <TableCell>{t(`vpnTester.modes.${run.mode}`)}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={t(`vpnTester.status.${run.status}`)}
                        tone={statusTone(run.status)}
                      />
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {run.pass_count}/{run.fail_count}/{run.degraded_count}
                    </TableCell>
                    <TableCell>{formatDate(run.updated_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          magnetic={false}
                          variant="ghost"
                          onClick={() => {
                            setSelectedRunId(run.id);
                            setActiveTab('evidence');
                          }}
                        >
                          <FileSearch className="mr-2 h-4 w-4" />
                          {t('vpnTester.actions.inspect')}
                        </Button>
                        {(run.status === 'queued' || run.status === 'running') && canMutateRuns ? (
                          <Button
                            magnetic={false}
                            variant="ghost"
                            onClick={() => cancelRunMutation.mutate(run.id)}
                          >
                            <XCircle className="mr-2 h-4 w-4" />
                            {t('common.cancel')}
                          </Button>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      ) : null}

      {activeTab === 'routeMatrix' ? (
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-lg tracking-[0.14em] text-white">
                {t('vpnTester.routeMatrix.title')}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {t('vpnTester.routeMatrix.description')}
              </p>
            </div>
            <InfrastructureStatusChip
              label={safeString(routeMatrixQuery.data?.registry_key)}
              tone={(routeMatrixQuery.data?.total ?? 0) >= 40 ? 'success' : 'danger'}
            />
          </div>
          {routeRows.length === 0 ? (
            <InfrastructureEmptyState label={t('vpnTester.routeMatrix.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('vpnTester.routeMatrix.route')}</TableHead>
                  <TableHead>{t('vpnTester.routeMatrix.group')}</TableHead>
                  <TableHead>{t('vpnTester.routeMatrix.policy')}</TableHead>
                  <TableHead>{t('vpnTester.routeMatrix.domain')}</TableHead>
                  <TableHead>{t('vpnTester.routeMatrix.severity')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {routeRows.slice(0, 60).map((row) => (
                  <TableRow key={String(row.route_key)}>
                    <TableCell className="font-mono text-xs">{safeString(row.route_key)}</TableCell>
                    <TableCell>{safeString(row.expected_group)}</TableCell>
                    <TableCell>{safeString(row.expected_policy)}</TableCell>
                    <TableCell>{safeString(row.domain)}</TableCell>
                    <TableCell>{safeString(row.severity)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      ) : null}

      {activeTab === 'tariffs' ? (
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-lg tracking-[0.14em] text-white">
                {t('vpnTester.tariffs.title')}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {t('vpnTester.tariffs.description')}
              </p>
            </div>
            <ShieldAlert className="h-5 w-5 text-neon-cyan" />
          </div>
          {tariffRows.length === 0 ? (
            <InfrastructureEmptyState label={t('vpnTester.tariffs.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('vpnTester.tariffs.plan')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('vpnTester.tariffs.visibility')}</TableHead>
                  <TableHead>{t('vpnTester.tariffs.devices')}</TableHead>
                  <TableHead>{t('vpnTester.tariffs.checks')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tariffRows.slice(0, 30).map((row) => (
                  <TableRow key={String(row.plan_code)}>
                    <TableCell>{safeString(row.plan_code)}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={t(`vpnTester.status.${String(row.status ?? 'degraded')}`)}
                        tone={statusTone(String(row.status ?? 'degraded'))}
                      />
                    </TableCell>
                    <TableCell>{safeString(row.visibility)}</TableCell>
                    <TableCell>{safeString(row.device_limit)}</TableCell>
                    <TableCell>{asNumber(Array.isArray(row.checks) ? row.checks.length : 0)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      ) : null}

      {activeTab === 'schedules' ? (
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-lg tracking-[0.14em] text-white">
                {t('vpnTester.schedules.title')}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {canMutateSchedules ? t('vpnTester.schedules.description') : readOnlyReason}
              </p>
            </div>
            <SlidersHorizontal className="h-5 w-5 text-neon-cyan" />
          </div>
          <div className="grid gap-3">
            {schedules.map((schedule) => (
              <div
                key={schedule.schedule_key}
                className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-xs uppercase tracking-[0.12em] text-white">
                      {schedule.schedule_key}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {schedule.cron} · {schedule.suite_key} · {t(`vpnTester.modes.${schedule.mode}`)}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {t('vpnTester.schedules.lastChecked')}: {formatDate(schedule.last_checked_at)}
                      {' · '}
                      {t('vpnTester.schedules.lastSkipped')}: {safeString(schedule.last_skipped_reason)}
                    </p>
                  </div>
                  <Button
                    magnetic={false}
                    variant="ghost"
                    onClick={() => toggleScheduleMutation.mutate({
                      enabled: !schedule.enabled,
                      scheduleKey: schedule.schedule_key,
                    })}
                    disabled={!canMutateSchedules || toggleScheduleMutation.isPending}
                  >
                    {schedule.enabled ? t('common.disabled') : t('common.enabled')}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {activeTab === 'releaseGate' ? (
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h2 className="font-display text-lg tracking-[0.14em] text-white">
                {t('vpnTester.releaseGate.title')}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {releaseGateQuery.data?.active_override
                  ? releaseGateQuery.data.active_override.reason
                  : t('vpnTester.releaseGate.description')}
              </p>
            </div>
            <InfrastructureStatusChip
              label={t(`vpnTester.status.${releaseGateQuery.data?.status ?? 'queued'}`)}
              tone={releaseGateQuery.data?.blocking ? 'danger' : statusTone(releaseGateQuery.data?.status ?? 'queued')}
            />
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            <JsonPreview value={releaseGateQuery.data ?? {}} />
            <div className="grid gap-3">
              <label className="grid gap-2 text-xs font-mono uppercase tracking-[0.14em] text-muted-foreground">
                {t('vpnTester.releaseGate.overrideReason')}
                <textarea
                  value={overrideReason}
                  onChange={(event) => setOverrideReason(event.target.value)}
                  className="min-h-28 rounded-lg border border-grid-line/30 bg-terminal-bg/80 px-3 py-3 text-sm normal-case tracking-normal text-white outline-hidden focus:border-neon-cyan"
                  disabled={!canOverrideGate}
                />
              </label>
              <Button
                magnetic={false}
                onClick={() => overrideGateMutation.mutate()}
                disabled={!canOverrideGate || overrideReason.trim().length < 20 || overrideGateMutation.isPending}
              >
                {t('vpnTester.actions.overrideGate')}
              </Button>
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === 'evidence' ? (
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          {selectedRun ? (
            <>
              <div className="mb-4 flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-display text-lg tracking-[0.14em] text-white">
                    {t('vpnTester.detail.title')}
                  </h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {selectedRun.suite_key} · {shortId(selectedRun.id)}
                  </p>
                </div>
                <InfrastructureStatusChip
                  label={t(`vpnTester.status.${selectedRun.status}`)}
                  tone={statusTone(selectedRun.status)}
                />
              </div>

              <div className="grid gap-6 xl:grid-cols-2">
                <div>
                  <h3 className="mb-3 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">
                    {t('vpnTester.detail.results')}
                  </h3>
                  <div className="grid gap-3">
                    {selectedRun.results.map((result) => (
                      <div
                        key={`${result.check_key}:${result.target}`}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm text-white">{result.check_name}</p>
                            <p className="mt-1 text-xs text-muted-foreground">{result.safe_summary}</p>
                          </div>
                          <InfrastructureStatusChip
                            label={t(`vpnTester.status.${result.status}`)}
                            tone={statusTone(result.status)}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="mb-3 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">
                    {t('vpnTester.detail.evidence')}
                  </h3>
                  {selectedRun.evidence_artifacts.length === 0 ? (
                    <InfrastructureEmptyState label={t('vpnTester.detail.noEvidence')} />
                  ) : (
                    <div className="grid gap-3">
                      {selectedRun.evidence_artifacts.map((artifact) => (
                        <div key={artifact.id} className="grid gap-3">
                          <p className="font-mono text-xs text-neon-cyan">
                            {artifact.artifact_key} · {shortId(artifact.sha256)}
                          </p>
                          <JsonPreview value={artifact.preview} />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <InfrastructureEmptyState label={t('vpnTester.detail.selectRun')} />
          )}
        </section>
      ) : null}

      {activeTab === 'balancer' ? (
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-lg tracking-[0.14em] text-white">
                {t('vpnTester.balancer.title')}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {t('vpnTester.balancer.description')}
              </p>
            </div>
            <InfrastructureStatusChip
              label={overview?.balancer_recommendations_enabled ? t('common.enabled') : t('common.disabled')}
              tone={overview?.balancer_recommendations_enabled ? 'success' : 'warning'}
            />
          </div>
          <label className="mb-4 grid gap-2 text-xs font-mono uppercase tracking-[0.14em] text-muted-foreground">
            {t('vpnTester.balancer.dismissReason')}
            <input
              value={dismissReason}
              onChange={(event) => setDismissReason(event.target.value)}
              className="rounded-lg border border-grid-line/30 bg-terminal-bg/80 px-3 py-3 text-sm normal-case tracking-normal text-white outline-hidden focus:border-neon-cyan"
            />
          </label>
          {recommendations.length === 0 ? (
            <InfrastructureEmptyState label={t('vpnTester.balancer.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('vpnTester.balancer.key')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('vpnTester.balancer.confidence')}</TableHead>
                  <TableHead>{t('vpnTester.balancer.summary')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recommendations.map((recommendation) => (
                  <TableRow key={recommendation.id}>
                    <TableCell className="font-mono text-xs">{shortId(recommendation.recommendation_key)}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={t(`vpnTester.recommendationStatus.${recommendation.status}`)}
                        tone={recommendation.status === 'open' ? 'warning' : 'info'}
                      />
                    </TableCell>
                    <TableCell>{Math.round(recommendation.confidence * 100)}%</TableCell>
                    <TableCell>{recommendation.safe_summary}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          magnetic={false}
                          variant="ghost"
                          onClick={() => ackRecommendationMutation.mutate(recommendation.id)}
                          disabled={!canMutateRuns || recommendation.status !== 'open'}
                        >
                          {t('vpnTester.actions.ack')}
                        </Button>
                        <Button
                          magnetic={false}
                          variant="ghost"
                          onClick={() => dismissRecommendationMutation.mutate(recommendation.id)}
                          disabled={!canMutateRuns || recommendation.status !== 'open'}
                        >
                          {t('vpnTester.actions.dismiss')}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      ) : null}

      {activeTab === 'settings' ? (
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="mb-4">
            <h2 className="font-display text-lg tracking-[0.14em] text-white">
              {t('vpnTester.settings.title')}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {t('vpnTester.settings.description')}
            </p>
          </div>
          <JsonPreview
            value={{
              role,
              canMutateRuns,
              canMutateSchedules,
              canOverrideGate,
              overview,
            }}
          />
        </section>
      ) : null}
    </InfrastructurePageShell>
  );
}
