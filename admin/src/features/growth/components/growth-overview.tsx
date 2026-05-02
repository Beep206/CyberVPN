'use client';

import { useState } from 'react';
import { Download, Gift, RefreshCw, ShieldAlert, TicketPlus, TrendingUp, UserRoundPlus } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { growthApi } from '@/lib/api/growth';
import type {
  AdminGrowthNotificationDelivery,
  AdminGrowthNotificationDeliveryDetail,
  AdminGrowthReportingDelivery,
  AdminGrowthReportingOverview,
  AdminGrowthReportingSubscription,
} from '@/lib/api/growth';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  formatDateTime,
  humanizeToken,
} from '@/features/growth/lib/formatting';
import { Modal } from '@/shared/ui/modal';

function downloadBlobResponse(response: { data: Blob; headers: Record<string, unknown> }, fallbackName: string) {
  const dispositionHeader = String(response.headers['content-disposition'] ?? '');
  const filenameMatch = dispositionHeader.match(/filename=\"?([^"]+)\"?/i);
  const filename = filenameMatch?.[1] ?? fallbackName;
  const objectUrl = window.URL.createObjectURL(response.data);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
}

function buildReportingTrendRows(reporting: AdminGrowthReportingOverview | undefined) {
  const grouped = new Map<
    string,
    {
      reportDate: string;
      inviteIssued: number;
      promoAccepted: number;
      giftRedeemed: number;
      referralAvailableUsd: number;
    }
  >();

  for (const point of reporting?.daily_points ?? []) {
    const bucket = grouped.get(point.report_date) ?? {
      reportDate: point.report_date,
      inviteIssued: 0,
      promoAccepted: 0,
      giftRedeemed: 0,
      referralAvailableUsd: 0,
    };
    if (point.family === 'invite') {
      bucket.inviteIssued += point.issued_total;
    }
    if (point.family === 'promo') {
      bucket.promoAccepted += point.resolution_accepted_total;
    }
    if (point.family === 'gift') {
      bucket.giftRedeemed += point.redemption_total;
    }
    if (point.family === 'referral') {
      bucket.referralAvailableUsd += point.reward_available_amount_usd;
    }
    grouped.set(point.report_date, bucket);
  }

  return Array.from(grouped.values())
    .sort((left, right) => right.reportDate.localeCompare(left.reportDate))
    .slice(0, 7);
}

function reportingHealthTone(status: string) {
  if (status === 'fresh') return 'success' as const;
  if (status === 'stale') return 'warning' as const;
  if (status === 'failed') return 'danger' as const;
  return 'neutral' as const;
}

function reportingSubscriptionTone(subscription: AdminGrowthReportingSubscription) {
  if (subscription.subscription_status !== 'active') return 'neutral' as const;
  if (subscription.health_status === 'failed' || subscription.health_status === 'overdue') {
    return 'danger' as const;
  }
  if (subscription.health_status === 'healthy') return 'success' as const;
  return 'warning' as const;
}

function reportingDeliveryTone(delivery: AdminGrowthReportingDelivery) {
  if (delivery.delivery_status === 'delivered') return 'success' as const;
  if (delivery.delivery_status === 'failed') return 'danger' as const;
  if (delivery.delivery_status === 'processing') return 'warning' as const;
  return 'neutral' as const;
}

function governanceCoverageTone(coverageState: string) {
  if (coverageState === 'delivery_suppressed' || coverageState === 'recipient_domain_blocked') {
    return 'warning' as const;
  }
  if (coverageState === 'failed' || coverageState === 'overdue') {
    return 'danger' as const;
  }
  if (coverageState === 'active_healthy') {
    return 'success' as const;
  }
  return 'neutral' as const;
}

function governanceFollowupTone(
  followup: { status: string; is_overdue: boolean; reason_code?: string | null },
) {
  if (followup.status !== 'open') {
    return 'neutral' as const;
  }
  if (followup.is_overdue) {
    return 'danger' as const;
  }
  if (followup.reason_code === 'recipient_domain_blocked') {
    return 'danger' as const;
  }
  return 'warning' as const;
}

function formatAgeSeconds(seconds: number | null | undefined, locale: string) {
  if (seconds == null) {
    return 'n/a';
  }
  if (seconds < 60) {
    return `${formatCompactNumber(seconds, locale)}s`;
  }
  if (seconds < 3600) {
    return `${formatCompactNumber(Math.round(seconds / 60), locale)}m`;
  }
  if (seconds < 86400) {
    return `${formatCompactNumber(Math.round(seconds / 3600), locale)}h`;
  }
  return `${formatCompactNumber(Math.round(seconds / 86400), locale)}d`;
}

function defaultReportingPolicy(audienceKey = 'finance') {
  const templateByAudience: Record<string, string> = {
    finance: 'finance_exec',
    product: 'product_exec',
    risk: 'risk_exec',
    ops: 'ops_exec',
  };

  return {
    templateKey: templateByAudience[audienceKey] ?? 'cross_function_exec',
    templateLocale: 'en-EN',
    emailSubjectPrefix: '',
    titleOverride: '',
    recipientDomainPolicy: 'allow_any',
    allowedRecipientDomains: '',
    suppressedUntil: '',
    suppressionReasonCode: '',
  };
}

function defaultReportingSubscriptionForm() {
  return {
    recipientEmail: '',
    recipientName: '',
    audienceKey: 'finance',
    cadence: 'daily',
    reportWindowDays: '30',
    ...defaultReportingPolicy('finance'),
  };
}

function toDateTimeLocalInput(value?: string | null) {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function reportingSubscriptionFormFromItem(subscription: AdminGrowthReportingSubscription) {
  return {
    recipientEmail: subscription.recipient_email,
    recipientName: subscription.recipient_name ?? '',
    audienceKey: subscription.audience_key,
    cadence: subscription.cadence,
    reportWindowDays: String(subscription.report_window_days),
    templateKey: subscription.policy.template_key,
    templateLocale: subscription.policy.template_locale,
    emailSubjectPrefix: subscription.policy.email_subject_prefix ?? '',
    titleOverride: subscription.policy.title_override ?? '',
    recipientDomainPolicy: subscription.policy.recipient_domain_policy,
    allowedRecipientDomains: subscription.policy.allowed_recipient_domains.join(', '),
    suppressedUntil: toDateTimeLocalInput(subscription.policy.suppressed_until),
    suppressionReasonCode: subscription.policy.suppression_reason_code ?? '',
  };
}

export function GrowthOverview() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const reportingWindowDays = 14;
  const [deliveryFilterUserId, setDeliveryFilterUserId] = useState('');
  const [selectedDeliveryId, setSelectedDeliveryId] = useState<string | null>(null);
  const [editingReportingSubscriptionId, setEditingReportingSubscriptionId] = useState<string | null>(null);
  const [reportingSubscriptionForm, setReportingSubscriptionForm] = useState(defaultReportingSubscriptionForm);
  const [manualForm, setManualForm] = useState({
    mobileUserId: '',
    title: '',
    message: '',
    routeSlug: '/referral',
    locale: 'en-EN',
    notes: '',
    channels: {
      inApp: true,
      email: true,
      telegram: true,
    },
  });

  const overviewQuery = useQuery({
    queryKey: ['growth', 'signals', 'overview'],
    queryFn: async () => {
      const response = await growthApi.getGrowthSignalsOverview();
      return response.data;
    },
    staleTime: 15_000,
  });

  const deliveriesQuery = useQuery({
    queryKey: ['growth', 'notification-deliveries', deliveryFilterUserId],
    queryFn: async () => {
      const response = await growthApi.listGrowthNotificationDeliveries({
        mobile_user_id: deliveryFilterUserId.trim() || undefined,
        limit: 8,
      });
      return response.data;
    },
    staleTime: 15_000,
  });

  const deliveryDetailQuery = useQuery({
    queryKey: ['growth', 'notification-deliveries', 'detail', selectedDeliveryId],
    queryFn: async () => {
      if (!selectedDeliveryId) {
        throw new Error('delivery_id_required');
      }
      const response = await growthApi.getGrowthNotificationDeliveryDetail(selectedDeliveryId);
      return response.data;
    },
    enabled: Boolean(selectedDeliveryId),
    staleTime: 15_000,
  });

  const reportingQuery = useQuery({
    queryKey: ['growth', 'reporting', reportingWindowDays],
    queryFn: async () => {
      const response = await growthApi.getGrowthReportingOverview({
        window_days: reportingWindowDays,
      });
      return response.data;
    },
    staleTime: 60_000,
  });

  const reportingGovernanceQuery = useQuery({
    queryKey: ['growth', 'reporting', 'governance'],
    queryFn: async () => {
      const response = await growthApi.getGrowthReportingGovernanceOverview();
      return response.data;
    },
    staleTime: 30_000,
  });

  const reportingSubscriptionsQuery = useQuery({
    queryKey: ['growth', 'reporting', 'subscriptions'],
    queryFn: async () => {
      const response = await growthApi.listGrowthReportingSubscriptions();
      return response.data;
    },
    staleTime: 30_000,
  });

  const reportingDeliveriesQuery = useQuery({
    queryKey: ['growth', 'reporting', 'deliveries'],
    queryFn: async () => {
      const response = await growthApi.listGrowthReportingDeliveries({ limit: 8 });
      return response.data;
    },
    staleTime: 30_000,
  });

  const manualNotifyMutation = useMutation({
    mutationKey: ['growth', 'notification-deliveries', 'manual'],
    mutationFn: async () => {
      const channels = [
        manualForm.channels.inApp ? 'in_app' : null,
        manualForm.channels.email ? 'email' : null,
        manualForm.channels.telegram ? 'telegram' : null,
      ].filter((value): value is string => value !== null);

      const response = await growthApi.createManualGrowthNotification({
        mobile_user_id: manualForm.mobileUserId.trim(),
        title: manualForm.title.trim(),
        message: manualForm.message.trim(),
        route_slug: manualForm.routeSlug.trim() || '/referral',
        locale: manualForm.locale.trim() || 'en-EN',
        notes: manualForm.notes
          .split('\n')
          .map((item) => item.trim())
          .filter(Boolean)
          .slice(0, 6),
        channels,
      });
      return response.data;
    },
    onSuccess: async () => {
      setManualForm((current) => ({
        ...current,
        title: '',
        message: '',
        notes: '',
      }));
      await queryClient.invalidateQueries({
        queryKey: ['growth', 'notification-deliveries'],
      });
    },
  });

  const deliveryActionMutation = useMutation({
    mutationKey: ['growth', 'notification-deliveries', 'action'],
    mutationFn: async ({
      deliveryId,
      action,
    }: {
      deliveryId: string;
      action: 'resend' | 'pause' | 'revoke' | 'resolve';
    }) => {
      if (action === 'resend') {
        const response = await growthApi.resendGrowthNotificationDelivery(deliveryId, {
          reason_code: 'manual_retry',
        });
        return response.data;
      }
      if (action === 'pause') {
        const response = await growthApi.pauseGrowthNotificationDelivery(deliveryId, {
          reason_code: 'manual_pause',
        });
        return response.data;
      }
      if (action === 'resolve') {
        const response = await growthApi.resolveGrowthNotificationDelivery(deliveryId, {
          reason_code: 'support_resolved',
        });
        return response.data;
      }
      const response = await growthApi.revokeGrowthNotificationDelivery(deliveryId, {
        reason_code: 'manual_revoke',
      });
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['growth', 'notification-deliveries'],
      });
    },
  });

  const exportDeliveryMutation = useMutation({
    mutationKey: ['growth', 'notification-deliveries', 'export'],
    mutationFn: async (deliveryId: string) => {
      const response = await growthApi.exportGrowthNotificationDeliveryDetail(deliveryId);
      downloadBlobResponse(response, `growth-notification-delivery-${deliveryId}.json`);
    },
  });

  const refreshReportingMutation = useMutation({
    mutationKey: ['growth', 'reporting', 'refresh', reportingWindowDays],
    mutationFn: async () => {
      const response = await growthApi.refreshGrowthReporting({
        window_days: Math.max(reportingWindowDays, 30),
      });
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['growth', 'reporting'],
      });
    },
  });

  const exportReportingMutation = useMutation({
    mutationKey: ['growth', 'reporting', 'export', reportingWindowDays],
    mutationFn: async () => {
      const response = await growthApi.exportGrowthReportingOverview({
        window_days: Math.max(reportingWindowDays, 30),
      });
      downloadBlobResponse(
        response,
        `growth-reporting-${reportingWindowDays}-day-window.json`,
      );
    },
  });

  const exportReportingGovernanceMutation = useMutation({
    mutationKey: ['growth', 'reporting', 'governance', 'export'],
    mutationFn: async () => {
      const response = await growthApi.exportGrowthReportingGovernanceSnapshot();
      downloadBlobResponse(
        response,
        'growth-reporting-governance-snapshot.json',
      );
    },
  });

  const createReportingSubscriptionMutation = useMutation({
    mutationKey: ['growth', 'reporting', 'subscriptions', 'upsert', editingReportingSubscriptionId],
    mutationFn: async () => {
      const payload = {
        recipient_email: reportingSubscriptionForm.recipientEmail.trim(),
        recipient_name: reportingSubscriptionForm.recipientName.trim() || null,
        audience_key: reportingSubscriptionForm.audienceKey,
        cadence: reportingSubscriptionForm.cadence,
        report_window_days: Math.max(Number(reportingSubscriptionForm.reportWindowDays) || 30, 1),
        policy: {
          template_key: reportingSubscriptionForm.templateKey || null,
          template_locale: reportingSubscriptionForm.templateLocale.trim() || 'en-EN',
          email_subject_prefix: reportingSubscriptionForm.emailSubjectPrefix.trim() || null,
          title_override: reportingSubscriptionForm.titleOverride.trim() || null,
          recipient_domain_policy: reportingSubscriptionForm.recipientDomainPolicy,
          allowed_recipient_domains: reportingSubscriptionForm.allowedRecipientDomains
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
          suppressed_until: reportingSubscriptionForm.suppressedUntil
            ? new Date(reportingSubscriptionForm.suppressedUntil).toISOString()
            : null,
          suppression_reason_code: reportingSubscriptionForm.suppressionReasonCode.trim() || null,
        },
      };
      const response = editingReportingSubscriptionId
        ? await growthApi.updateGrowthReportingSubscription(editingReportingSubscriptionId, {
            ...payload,
            reason_code: 'admin_reporting_policy_update',
          })
        : await growthApi.createGrowthReportingSubscription(payload);
      return response.data;
    },
    onSuccess: async () => {
      setEditingReportingSubscriptionId(null);
      setReportingSubscriptionForm(defaultReportingSubscriptionForm());
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'reporting', 'governance'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'reporting', 'subscriptions'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'reporting', 'deliveries'] }),
      ]);
    },
  });

  const reportingSubscriptionActionMutation = useMutation({
    mutationKey: ['growth', 'reporting', 'subscriptions', 'action'],
    mutationFn: async ({
      subscriptionId,
      action,
    }: {
      subscriptionId: string;
      action: 'pause' | 'resume';
    }) => {
      if (action === 'pause') {
        const response = await growthApi.pauseGrowthReportingSubscription(subscriptionId, {
          reason_code: 'admin_manual_pause',
        });
        return response.data;
      }
      const response = await growthApi.resumeGrowthReportingSubscription(subscriptionId, {
        reason_code: 'admin_manual_resume',
      });
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'reporting', 'governance'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'reporting', 'subscriptions'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'reporting', 'deliveries'] }),
      ]);
    },
  });

  const reportingGovernanceFollowupMutation = useMutation({
    mutationKey: ['growth', 'reporting', 'subscriptions', 'followup'],
    mutationFn: async ({
      subscriptionId,
      action,
    }: {
      subscriptionId: string;
      action: 'resolve' | 'dismiss';
    }) => {
      const response = await growthApi.updateGrowthReportingGovernanceFollowup(subscriptionId, action, {
        reason_code: action === 'resolve' ? 'admin_followup_resolved' : 'admin_followup_dismissed',
      });
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'reporting', 'governance'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'reporting', 'subscriptions'] }),
      ]);
    },
  });

  const exportReportingDeliveryArtifactMutation = useMutation({
    mutationKey: ['growth', 'reporting', 'deliveries', 'artifact'],
    mutationFn: async (deliveryId: string) => {
      const response = await growthApi.exportGrowthReportingDeliveryArtifact(deliveryId);
      downloadBlobResponse(response, `growth-reporting-delivery-${deliveryId}.json`);
    },
  });

  const overview = overviewQuery.data;
  const reporting = reportingQuery.data;
  const reportingSubscriptions = reportingSubscriptionsQuery.data;
  const reportingDeliveries = reportingDeliveriesQuery.data;
  const reportingGovernance = reportingGovernanceQuery.data;
  const topRejections = (overview?.rejection_reason_breakdown ?? []).slice(0, 4);
  const recentEvents = overview?.recent_lifecycle_events ?? [];
  const deliveries = deliveriesQuery.data?.items ?? [];
  const reportingTrendRows = buildReportingTrendRows(reporting);

  return (
    <GrowthPageShell
      eyebrow={t('overview.eyebrow')}
      title={t('overview.title')}
      description={t('overview.description')}
      icon={TrendingUp}
      metrics={[
        {
          label: t('overview.metrics.totalCodes'),
          value: formatCompactNumber(overview?.total_codes ?? 0, locale),
          hint: t('overview.metrics.totalCodesHint'),
          tone: 'info',
        },
        {
          label: t('overview.metrics.redemptions'),
          value: formatCompactNumber(overview?.total_redemptions ?? 0, locale),
          hint: t('overview.metrics.redemptionsHint'),
          tone: 'success',
        },
        {
          label: t('overview.metrics.blockedSignals'),
          value: formatCompactNumber(overview?.blocked_reward_count ?? 0, locale),
          hint: t('overview.metrics.blockedSignalsHint'),
          tone: (overview?.blocked_reward_count ?? 0) > 0 ? 'danger' : 'neutral',
        },
        {
          label: t('overview.metrics.availableCredit'),
          value: formatCurrencyAmount(overview?.available_referral_credit_usd, 'USD', locale),
          hint: t('overview.metrics.availableCreditHint'),
          tone: 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.routesTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('overview.routesDescription')}
          </p>
          <div className="mt-5 grid gap-3">
            {[
              {
                href: '/growth/promo-codes',
                title: t('nav.promoCodes'),
                description: t('overview.routes.promoCodes'),
                icon: Gift,
              },
              {
                href: '/growth/invite-codes',
                title: t('nav.inviteCodes'),
                description: t('overview.routes.inviteCodes'),
                icon: TicketPlus,
              },
              {
                href: '/growth/gift-codes',
                title: t('nav.giftCodes'),
                description: t('overview.routes.giftCodes'),
                icon: Gift,
              },
              {
                href: '/growth/partners',
                title: t('nav.partners'),
                description: t('overview.routes.partners'),
                icon: UserRoundPlus,
              },
              {
                href: '/growth/referrals',
                title: t('nav.referrals'),
                description: t('overview.routes.referrals'),
                icon: ShieldAlert,
              },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 transition-colors hover:border-neon-cyan/35 hover:bg-terminal-bg/60"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
                    <item.icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-display uppercase tracking-[0.18em] text-white">
                      {item.title}
                    </p>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {item.description}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.liveSignalsTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('overview.liveSignalsDescription')}
              </p>
            </div>
            <GrowthStatusChip label={t('referrals.liveOverview')} tone="success" />
          </div>

          <div className="mt-5 space-y-3">
            {overviewQuery.isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))
            ) : recentEvents.length ? (
              recentEvents.map((event) => (
                <div
                  key={event.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {humanizeToken(event.event_name)}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {event.aggregate_type} / {event.aggregate_id.slice(0, 12)}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={humanizeToken(event.event_status)}
                      tone={event.event_status === 'published' ? 'success' : 'warning'}
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <GrowthStatusChip label={humanizeToken(event.event_family)} tone="info" />
                    <GrowthStatusChip label={formatDateTime(event.occurred_at, locale)} tone="neutral" />
                  </div>
                </div>
              ))
            ) : (
              <GrowthEmptyState label={t('overview.liveSignalsEmpty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.breakdownTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('overview.breakdownDescription')}
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {(overview?.code_status_breakdown ?? []).slice(0, 8).map((item) => (
              <GrowthStatusChip
                key={item.key}
                label={`${humanizeToken(item.key)} · ${formatCompactNumber(item.count, locale)}`}
                tone={item.key.includes('active') ? 'success' : 'neutral'}
              />
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.topRejectionsTitle')}
          </h2>
          <div className="mt-5 space-y-3">
            {topRejections.length ? (
              topRejections.map((item) => (
                <div
                  key={item.key}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {humanizeToken(item.key)}
                    </p>
                    <GrowthStatusChip
                      label={formatCompactNumber(item.count, locale)}
                      tone="danger"
                    />
                  </div>
                </div>
              ))
            ) : (
              <GrowthEmptyState label={t('overview.topRejectionsEmpty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-12">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.reporting.title')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('overview.reporting.description')}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <GrowthStatusChip
                  label={t('overview.reporting.window', { days: reportingWindowDays })}
                  tone="info"
                />
                <GrowthStatusChip
                  label={t(`overview.reporting.health.statuses.${reporting?.health.freshness_status ?? 'never_refreshed'}`)}
                  tone={reportingHealthTone(reporting?.health.freshness_status ?? 'never_refreshed')}
                />
                <GrowthStatusChip
                  label={
                    reporting?.refreshed_at
                      ? t('overview.reporting.refreshedAt', {
                        value: formatDateTime(reporting.refreshed_at, locale),
                      })
                      : t('overview.reporting.notRefreshed')
                  }
                  tone={reporting?.refreshed_at ? 'success' : 'warning'}
                />
                {reporting?.health.refresh_age_seconds != null ? (
                  <GrowthStatusChip
                    label={t('overview.reporting.health.refreshAge', {
                      value: formatAgeSeconds(reporting.health.refresh_age_seconds, locale),
                    })}
                    tone="neutral"
                  />
                ) : null}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => {
                  refreshReportingMutation.mutate();
                }}
                disabled={refreshReportingMutation.isPending}
                className="inline-flex items-center gap-2 rounded-2xl border border-grid-line/25 bg-terminal-bg/45 px-4 py-2 text-sm font-mono text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/60 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RefreshCw className="h-4 w-4" />
                {refreshReportingMutation.isPending
                  ? t('overview.reporting.refreshing')
                  : t('overview.reporting.refresh')}
              </button>
              <button
                type="button"
                onClick={() => {
                  exportReportingMutation.mutate();
                }}
                disabled={exportReportingMutation.isPending}
                className="inline-flex items-center gap-2 rounded-2xl border border-grid-line/25 bg-terminal-bg/45 px-4 py-2 text-sm font-mono text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/60 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Download className="h-4 w-4" />
                {exportReportingMutation.isPending
                  ? t('overview.reporting.exporting')
                  : t('overview.reporting.export')}
              </button>
            </div>
          </div>

          {reportingQuery.isLoading ? (
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-28 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : reporting?.family_summaries.length ? (
            <div className="mt-5 space-y-5">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
                      {t('overview.reporting.health.title')}
                    </h3>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('overview.reporting.health.description')}
                    </p>
                  </div>
                  <GrowthStatusChip
                    label={t(`overview.reporting.health.statuses.${reporting.health.freshness_status}`)}
                    tone={reportingHealthTone(reporting.health.freshness_status)}
                  />
                </div>

                <dl className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                    <dt className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                      {t('overview.reporting.health.latestAttempt')}
                    </dt>
                    <dd className="mt-2 text-sm font-mono text-white">
                      {reporting.health.latest_attempt_at
                        ? formatDateTime(reporting.health.latest_attempt_at, locale)
                        : t('overview.reporting.health.unavailable')}
                    </dd>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                    <dt className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                      {t('overview.reporting.health.latestSuccess')}
                    </dt>
                    <dd className="mt-2 text-sm font-mono text-white">
                      {reporting.health.latest_success_at
                        ? formatDateTime(reporting.health.latest_success_at, locale)
                        : t('overview.reporting.health.unavailable')}
                    </dd>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                    <dt className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                      {t('overview.reporting.health.expectedInterval')}
                    </dt>
                    <dd className="mt-2 text-sm font-mono text-white">
                      {formatAgeSeconds(reporting.health.expected_refresh_interval_seconds, locale)}
                    </dd>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                    <dt className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                      {t('overview.reporting.health.lastRun')}
                    </dt>
                    <dd className="mt-2 text-sm font-mono text-white">
                      {reporting.health.latest_run
                        ? `${reporting.health.latest_run.trigger_kind} / ${reporting.health.latest_run.refresh_status}`
                        : t('overview.reporting.health.unavailable')}
                    </dd>
                  </div>
                </dl>

                {reporting.health.latest_failure_message ? (
                  <p className="mt-4 rounded-2xl border border-neon-pink/30 bg-neon-pink/5 p-3 text-sm font-mono leading-6 text-neon-pink">
                    {reporting.health.latest_failure_message}
                  </p>
                ) : null}
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                    {t('overview.reporting.executive.issued')}
                  </p>
                  <p className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                    {formatCompactNumber(reporting.executive_summary.total_issued, locale)}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                    {t('overview.reporting.executive.redemptions')}
                  </p>
                  <p className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                    {formatCompactNumber(reporting.executive_summary.total_redemptions, locale)}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                    {t('overview.reporting.executive.acceptanceRate')}
                  </p>
                  <p className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                    {reporting.executive_summary.resolution_acceptance_rate_pct.toFixed(1)}%
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                    {t('overview.reporting.executive.dominantFamily')}
                  </p>
                  <p className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                    {reporting.executive_summary.dominant_family
                      ? humanizeToken(reporting.executive_summary.dominant_family)
                      : t('overview.reporting.health.unavailable')}
                  </p>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {reporting.family_summaries.map((item) => (
                  <div
                    key={item.family}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-display uppercase tracking-[0.18em] text-white">
                        {humanizeToken(item.family)}
                      </p>
                      <GrowthStatusChip
                        label={formatCompactNumber(item.issued_total, locale)}
                        tone="info"
                      />
                    </div>
                    <dl className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                      <div className="flex items-center justify-between gap-3">
                        <dt>{t('overview.reporting.cards.accepted')}</dt>
                        <dd className="text-white">{formatCompactNumber(item.resolution_accepted_total, locale)}</dd>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <dt>{t('overview.reporting.cards.redeemed')}</dt>
                        <dd className="text-white">{formatCompactNumber(item.redemption_total, locale)}</dd>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <dt>{t('overview.reporting.cards.reserved')}</dt>
                        <dd className="text-white">{formatCompactNumber(item.reservations_reserved_total, locale)}</dd>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <dt>{t('overview.reporting.cards.availableCredit')}</dt>
                        <dd className="text-white">
                          {formatCurrencyAmount(item.reward_available_amount_usd, 'USD', locale)}
                        </dd>
                      </div>
                    </dl>
                  </div>
                ))}
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
                  {t('overview.reporting.executive.title')}
                </h3>
                <ul className="mt-3 space-y-2 text-sm font-mono leading-6 text-muted-foreground">
                  {reporting.executive_summary.highlights.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
                    {t('overview.reporting.trendTitle')}
                  </h3>
                  <GrowthStatusChip
                    label={t('overview.reporting.rows', { count: reportingTrendRows.length })}
                    tone="neutral"
                  />
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full border-separate border-spacing-y-2">
                    <thead>
                      <tr className="text-left text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        <th className="px-3 py-2">{t('overview.reporting.table.date')}</th>
                        <th className="px-3 py-2">{t('overview.reporting.table.inviteIssued')}</th>
                        <th className="px-3 py-2">{t('overview.reporting.table.promoAccepted')}</th>
                        <th className="px-3 py-2">{t('overview.reporting.table.giftRedeemed')}</th>
                        <th className="px-3 py-2">{t('overview.reporting.table.referralAvailable')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportingTrendRows.map((item) => (
                        <tr
                          key={item.reportDate}
                          className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 text-sm font-mono text-white"
                        >
                          <td className="px-3 py-3">{formatDateTime(item.reportDate, locale)}</td>
                          <td className="px-3 py-3">{formatCompactNumber(item.inviteIssued, locale)}</td>
                          <td className="px-3 py-3">{formatCompactNumber(item.promoAccepted, locale)}</td>
                          <td className="px-3 py-3">{formatCompactNumber(item.giftRedeemed, locale)}</td>
                          <td className="px-3 py-3">
                            {formatCurrencyAmount(item.referralAvailableUsd, 'USD', locale)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
                  {t('overview.reporting.coverageTitle')}
                </h3>
                <ul className="mt-3 space-y-2 text-sm font-mono leading-6 text-muted-foreground">
                  {reporting.coverage_notes.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
                      {t('overview.reporting.governance.title')}
                    </h3>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('overview.reporting.governance.description')}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <GrowthStatusChip
                      label={t('overview.reporting.governance.metrics.gaps', {
                        count: reportingGovernance?.coverage_gap_count ?? 0,
                      })}
                      tone={(reportingGovernance?.coverage_gap_count ?? 0) > 0 ? 'warning' : 'success'}
                    />
                    <button
                      type="button"
                      onClick={() => {
                        exportReportingGovernanceMutation.mutate();
                      }}
                      disabled={exportReportingGovernanceMutation.isPending}
                      className="inline-flex items-center gap-2 rounded-2xl border border-grid-line/25 bg-terminal-bg/45 px-4 py-2 text-sm font-mono text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/60 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Download className="h-4 w-4" />
                      {exportReportingGovernanceMutation.isPending
                        ? t('overview.reporting.governance.exporting')
                        : t('overview.reporting.governance.export')}
                    </button>
                  </div>
                </div>

                {reportingGovernanceQuery.isLoading ? (
                  <div className="mt-4 h-28 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-surface/35" />
                ) : reportingGovernance ? (
                  <div className="mt-4 space-y-4">
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                        <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                          {t('overview.reporting.governance.metrics.active')}
                        </p>
                        <p className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                          {formatCompactNumber(reportingGovernance.active_subscription_count, locale)}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                        <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                          {t('overview.reporting.governance.metrics.paused')}
                        </p>
                        <p className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                          {formatCompactNumber(reportingGovernance.paused_subscription_count, locale)}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                        <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                          {t('overview.reporting.governance.metrics.followups')}
                        </p>
                        <p className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                          {formatCompactNumber(reportingGovernance.followup_open_count, locale)}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                        <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                          {t('overview.reporting.governance.metrics.overdue')}
                        </p>
                        <p className="mt-3 text-lg font-display uppercase tracking-[0.16em] text-white">
                          {formatCompactNumber(reportingGovernance.followup_overdue_count, locale)}
                        </p>
                      </div>
                      {(reportingGovernance.coverage_counts ?? []).slice(0, 4).map((item) => (
                        <div
                          key={item.coverage_state}
                          className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                              {humanizeToken(item.coverage_state)}
                            </p>
                            <GrowthStatusChip
                              label={formatCompactNumber(item.count, locale)}
                              tone={governanceCoverageTone(item.coverage_state)}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    <ul className="space-y-2 text-sm font-mono leading-6 text-muted-foreground">
                      {reportingGovernance.notes.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>

                    <div className="grid gap-4 xl:grid-cols-2">
                      <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <h4 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                            {t('overview.reporting.governance.followupTitle')}
                          </h4>
                          <GrowthStatusChip
                            label={t('overview.reporting.rows', {
                              count: reportingGovernance.followup_queue.length,
                            })}
                            tone="neutral"
                          />
                        </div>
                        <div className="mt-4 space-y-3">
                          {reportingGovernance.followup_queue.length ? (
                            reportingGovernance.followup_queue.map((item) => (
                              <div
                                key={item.subscription_id}
                                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-3"
                              >
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                  <div>
                                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                                      {item.recipient_email}
                                    </p>
                                    <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                                      {humanizeToken(item.audience_key)} / {humanizeToken(item.followup.reason_code ?? item.health_status)}
                                    </p>
                                  </div>
                                  <GrowthStatusChip
                                    label={humanizeToken(item.followup.status)}
                                    tone={governanceFollowupTone(item.followup)}
                                  />
                                </div>
                                <div className="mt-3 flex flex-wrap gap-2 text-xs font-mono text-muted-foreground">
                                  {item.followup.due_at ? (
                                    <GrowthStatusChip
                                      label={t('overview.reporting.governance.followupDue', {
                                        value: formatDateTime(item.followup.due_at, locale),
                                      })}
                                      tone={item.followup.is_overdue ? 'danger' : 'warning'}
                                    />
                                  ) : null}
                                  {item.followup.last_notified_at ? (
                                    <GrowthStatusChip
                                      label={t('overview.reporting.governance.followupLastNotified', {
                                        value: formatDateTime(item.followup.last_notified_at, locale),
                                      })}
                                      tone="neutral"
                                    />
                                  ) : null}
                                </div>
                                <div className="mt-4 flex flex-wrap justify-end gap-2">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      reportingGovernanceFollowupMutation.mutate({
                                        subscriptionId: item.subscription_id,
                                        action: 'dismiss',
                                      });
                                    }}
                                    disabled={reportingGovernanceFollowupMutation.isPending}
                                    className="rounded-2xl border border-grid-line/20 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/55 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    {t('overview.reporting.governance.actions.dismiss')}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      reportingGovernanceFollowupMutation.mutate({
                                        subscriptionId: item.subscription_id,
                                        action: 'resolve',
                                      });
                                    }}
                                    disabled={reportingGovernanceFollowupMutation.isPending}
                                    className="rounded-2xl border border-grid-line/20 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/55 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    {t('overview.reporting.governance.actions.resolve')}
                                  </button>
                                </div>
                              </div>
                            ))
                          ) : (
                            <GrowthEmptyState label={t('overview.reporting.governance.followupEmpty')} />
                          )}
                        </div>
                      </div>

                      <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <h4 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                            {t('overview.reporting.governance.decisionsTitle')}
                          </h4>
                          <GrowthStatusChip
                            label={t('overview.reporting.rows', {
                              count: reportingGovernance.recent_decisions.length,
                            })}
                            tone="neutral"
                          />
                        </div>
                        <div className="mt-4 space-y-3">
                          {reportingGovernance.recent_decisions.length ? (
                            reportingGovernance.recent_decisions.map((item) => (
                              <div
                                key={item.delivery_id}
                                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-3"
                              >
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                  <div>
                                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                                      {item.recipient_email}
                                    </p>
                                    <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                                      {humanizeToken(item.audience_key)} / {humanizeToken(item.status_reason)}
                                    </p>
                                  </div>
                                  <GrowthStatusChip
                                    label={humanizeToken(item.decision_kind)}
                                    tone={governanceCoverageTone(item.status_reason)}
                                  />
                                </div>
                                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                                  {item.summary}
                                </p>
                                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-mono text-muted-foreground">
                                  <span>{formatDateTime(item.created_at, locale)}</span>
                                  {item.can_export_artifact ? (
                                    <button
                                      type="button"
                                      onClick={() => {
                                        exportReportingDeliveryArtifactMutation.mutate(item.delivery_id);
                                      }}
                                      disabled={exportReportingDeliveryArtifactMutation.isPending}
                                      className="rounded-full border border-grid-line/20 px-2 py-1 text-xs text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/55"
                                    >
                                      {t('overview.reporting.deliveries.actions.export')}
                                    </button>
                                  ) : null}
                                </div>
                              </div>
                            ))
                          ) : (
                            <GrowthEmptyState label={t('overview.reporting.governance.emptyDecisions')} />
                          )}
                        </div>
                      </div>

                      <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <h4 className="text-sm font-display uppercase tracking-[0.18em] text-white">
                            {t('overview.reporting.governance.auditTitle')}
                          </h4>
                          <Link
                            href="/governance/audit-log"
                            className="text-xs font-mono uppercase tracking-[0.16em] text-neon-cyan transition-colors hover:text-white"
                          >
                            {t('overview.reporting.governance.auditLink')}
                          </Link>
                        </div>
                        <div className="mt-4 space-y-3">
                          {reportingGovernance.recent_audit_events.length ? (
                            reportingGovernance.recent_audit_events.map((item) => (
                              <div
                                key={item.id}
                                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-3"
                              >
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                  <div>
                                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                                      {humanizeToken(item.action)}
                                    </p>
                                    <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                                      {item.actor_label}
                                    </p>
                                  </div>
                                  <GrowthStatusChip
                                    label={item.reason_code ? humanizeToken(item.reason_code) : 'audit'}
                                    tone="info"
                                  />
                                </div>
                                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                                  {item.changed_fields.length
                                    ? item.changed_fields.map((field) => humanizeToken(field)).join(', ')
                                    : t('overview.reporting.governance.noFieldDiff')}
                                </p>
                                <p className="mt-3 text-xs font-mono text-muted-foreground">
                                  {formatDateTime(item.created_at, locale)}
                                </p>
                              </div>
                            ))
                          ) : (
                            <GrowthEmptyState label={t('overview.reporting.governance.emptyAudit')} />
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
                        {t('overview.reporting.distribution.title')}
                      </h3>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {t('overview.reporting.distribution.description')}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={t('overview.reporting.distribution.metrics.active', {
                        count: reportingSubscriptions?.active_count ?? 0,
                      })}
                      tone={(reportingSubscriptions?.active_count ?? 0) > 0 ? 'success' : 'neutral'}
                    />
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.email')}</span>
                      <input
                        value={reportingSubscriptionForm.recipientEmail}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            recipientEmail: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                        placeholder="finance-growth@example.test"
                      />
                    </label>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.name')}</span>
                      <input
                        value={reportingSubscriptionForm.recipientName}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            recipientName: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                        placeholder={t('overview.reporting.distribution.fields.namePlaceholder')}
                      />
                    </label>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.audience')}</span>
                      <select
                        value={reportingSubscriptionForm.audienceKey}
                        onChange={(event) => {
                          const nextAudience = event.target.value;
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            audienceKey: nextAudience,
                            templateKey: defaultReportingPolicy(nextAudience).templateKey,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                      >
                        {['finance', 'product', 'risk', 'ops'].map((audience) => (
                          <option key={audience} value={audience} className="bg-terminal-bg text-white">
                            {humanizeToken(audience)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="grid gap-3 md:grid-cols-2">
                      <label className="space-y-2 text-sm font-mono text-muted-foreground">
                        <span>{t('overview.reporting.distribution.fields.cadence')}</span>
                        <select
                          value={reportingSubscriptionForm.cadence}
                          onChange={(event) => {
                            setReportingSubscriptionForm((current) => ({
                              ...current,
                              cadence: event.target.value,
                            }));
                          }}
                          className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                        >
                          {['daily', 'weekly'].map((cadence) => (
                            <option key={cadence} value={cadence} className="bg-terminal-bg text-white">
                              {humanizeToken(cadence)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="space-y-2 text-sm font-mono text-muted-foreground">
                        <span>{t('overview.reporting.distribution.fields.windowDays')}</span>
                        <input
                          value={reportingSubscriptionForm.reportWindowDays}
                          onChange={(event) => {
                            setReportingSubscriptionForm((current) => ({
                              ...current,
                              reportWindowDays: event.target.value.replace(/[^0-9]/g, ''),
                            }));
                          }}
                          className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                          inputMode="numeric"
                        />
                      </label>
                    </div>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.template')}</span>
                      <select
                        value={reportingSubscriptionForm.templateKey}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            templateKey: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                      >
                        {['finance_exec', 'product_exec', 'risk_exec', 'ops_exec', 'cross_function_exec'].map((templateKey) => (
                          <option key={templateKey} value={templateKey} className="bg-terminal-bg text-white">
                            {humanizeToken(templateKey)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.locale')}</span>
                      <input
                        value={reportingSubscriptionForm.templateLocale}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            templateLocale: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                        placeholder="en-EN"
                      />
                    </label>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.subjectPrefix')}</span>
                      <input
                        value={reportingSubscriptionForm.emailSubjectPrefix}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            emailSubjectPrefix: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                        placeholder="[CyberVPN][Growth][Finance]"
                      />
                    </label>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.titleOverride')}</span>
                      <input
                        value={reportingSubscriptionForm.titleOverride}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            titleOverride: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                        placeholder={t('overview.reporting.distribution.fields.titleOverridePlaceholder')}
                      />
                    </label>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.domainPolicy')}</span>
                      <select
                        value={reportingSubscriptionForm.recipientDomainPolicy}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            recipientDomainPolicy: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                      >
                        {['allow_any', 'allowlist_only'].map((domainPolicy) => (
                          <option key={domainPolicy} value={domainPolicy} className="bg-terminal-bg text-white">
                            {humanizeToken(domainPolicy)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.allowedDomains')}</span>
                      <input
                        value={reportingSubscriptionForm.allowedRecipientDomains}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            allowedRecipientDomains: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                        placeholder="example.test, cybervpn.example"
                      />
                    </label>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.suppressedUntil')}</span>
                      <input
                        type="datetime-local"
                        value={reportingSubscriptionForm.suppressedUntil}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            suppressedUntil: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                      />
                    </label>
                    <label className="space-y-2 text-sm font-mono text-muted-foreground">
                      <span>{t('overview.reporting.distribution.fields.suppressionReason')}</span>
                      <input
                        value={reportingSubscriptionForm.suppressionReasonCode}
                        onChange={(event) => {
                          setReportingSubscriptionForm((current) => ({
                            ...current,
                            suppressionReasonCode: event.target.value,
                          }));
                        }}
                        className="w-full rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                        placeholder="board_freeze"
                      />
                    </label>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-3">
                    <p className="text-sm font-mono text-muted-foreground">
                      {createReportingSubscriptionMutation.isError
                        ? t('overview.reporting.distribution.createFailed')
                        : t('overview.reporting.distribution.createHint')}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {editingReportingSubscriptionId ? (
                        <button
                          type="button"
                          onClick={() => {
                            setEditingReportingSubscriptionId(null);
                            setReportingSubscriptionForm(defaultReportingSubscriptionForm());
                          }}
                          className="rounded-2xl border border-grid-line/20 px-4 py-2 text-sm font-mono text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/55"
                        >
                          {t('overview.reporting.distribution.actions.cancelEdit')}
                        </button>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => {
                          createReportingSubscriptionMutation.mutate();
                        }}
                        disabled={
                          createReportingSubscriptionMutation.isPending
                          || !reportingSubscriptionForm.recipientEmail.trim()
                        }
                        className="inline-flex items-center gap-2 rounded-2xl border border-grid-line/25 bg-terminal-surface/45 px-4 py-2 text-sm font-mono text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-surface/60 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <UserRoundPlus className="h-4 w-4" />
                        {createReportingSubscriptionMutation.isPending
                          ? t('overview.reporting.distribution.creating')
                          : editingReportingSubscriptionId
                            ? t('overview.reporting.distribution.actions.update')
                            : t('overview.reporting.distribution.create')}
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    {reportingSubscriptionsQuery.isLoading ? (
                      <div className="h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-surface/35" />
                    ) : reportingSubscriptions?.items.length ? (
                      reportingSubscriptions.items.map((subscription) => (
                        <div
                          key={subscription.id}
                          className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                                {subscription.recipient_email}
                              </p>
                              <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                                {humanizeToken(subscription.audience_key)} / {humanizeToken(subscription.cadence)}
                              </p>
                            </div>
                            <GrowthStatusChip
                              label={humanizeToken(subscription.health_status)}
                              tone={reportingSubscriptionTone(subscription)}
                            />
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2 text-xs font-mono text-muted-foreground">
                            <GrowthStatusChip
                              label={humanizeToken(subscription.subscription_status)}
                              tone={subscription.subscription_status === 'active' ? 'success' : 'neutral'}
                            />
                            <GrowthStatusChip
                              label={t('overview.reporting.distribution.nextDelivery', {
                                value: formatDateTime(subscription.next_delivery_at, locale),
                              })}
                              tone="neutral"
                            />
                            <GrowthStatusChip
                              label={humanizeToken(subscription.policy.template_key)}
                              tone="info"
                            />
                            <GrowthStatusChip
                              label={humanizeToken(subscription.policy.recipient_domain_policy)}
                              tone={subscription.policy.recipient_domain_policy === 'allow_any' ? 'neutral' : 'warning'}
                            />
                            {subscription.policy.suppressed_until ? (
                              <GrowthStatusChip
                                label={t('overview.reporting.distribution.suppressedUntil', {
                                  value: formatDateTime(subscription.policy.suppressed_until, locale),
                                })}
                                tone="warning"
                              />
                            ) : null}
                            {subscription.followup.status !== 'none' ? (
                              <GrowthStatusChip
                                label={humanizeToken(subscription.followup.status)}
                                tone={governanceFollowupTone(subscription.followup)}
                              />
                            ) : null}
                            {subscription.followup.due_at ? (
                              <GrowthStatusChip
                                label={t('overview.reporting.governance.followupDue', {
                                  value: formatDateTime(subscription.followup.due_at, locale),
                                })}
                                tone={subscription.followup.is_overdue ? 'danger' : 'warning'}
                              />
                            ) : null}
                          </div>
                          {subscription.policy.allowed_recipient_domains.length ? (
                            <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                              {t('overview.reporting.distribution.allowedDomainsValue', {
                                value: subscription.policy.allowed_recipient_domains.join(', '),
                              })}
                            </p>
                          ) : null}
                          <div className="mt-4 flex flex-wrap justify-end gap-2">
                            {subscription.followup.action_required ? (
                              <>
                                <button
                                  type="button"
                                  onClick={() => {
                                    reportingGovernanceFollowupMutation.mutate({
                                      subscriptionId: subscription.id,
                                      action: 'dismiss',
                                    });
                                  }}
                                  disabled={reportingGovernanceFollowupMutation.isPending}
                                  className="rounded-2xl border border-grid-line/20 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/55 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {t('overview.reporting.governance.actions.dismiss')}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    reportingGovernanceFollowupMutation.mutate({
                                      subscriptionId: subscription.id,
                                      action: 'resolve',
                                    });
                                  }}
                                  disabled={reportingGovernanceFollowupMutation.isPending}
                                  className="rounded-2xl border border-grid-line/20 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/55 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {t('overview.reporting.governance.actions.resolve')}
                                </button>
                              </>
                            ) : null}
                            <button
                              type="button"
                              onClick={() => {
                                setEditingReportingSubscriptionId(subscription.id);
                                setReportingSubscriptionForm(reportingSubscriptionFormFromItem(subscription));
                              }}
                              className="rounded-2xl border border-grid-line/20 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/55"
                            >
                              {t('common.edit')}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                reportingSubscriptionActionMutation.mutate({
                                  subscriptionId: subscription.id,
                                  action: subscription.subscription_status === 'active' ? 'pause' : 'resume',
                                });
                              }}
                              disabled={reportingSubscriptionActionMutation.isPending}
                              className="rounded-2xl border border-grid-line/20 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/55 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {subscription.subscription_status === 'active'
                                ? t('overview.reporting.distribution.actions.pause')
                                : t('overview.reporting.distribution.actions.resume')}
                            </button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <GrowthEmptyState label={t('overview.reporting.distribution.empty')} />
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-display uppercase tracking-[0.2em] text-white">
                        {t('overview.reporting.deliveries.title')}
                      </h3>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {t('overview.reporting.deliveries.description')}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={t('overview.reporting.deliveries.failed', {
                        count: reportingDeliveries?.failed_count ?? 0,
                      })}
                      tone={(reportingDeliveries?.failed_count ?? 0) > 0 ? 'danger' : 'neutral'}
                    />
                  </div>

                  <div className="mt-4 space-y-3">
                    {reportingDeliveriesQuery.isLoading ? (
                      <div className="h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-surface/35" />
                    ) : reportingDeliveries?.items.length ? (
                      reportingDeliveries.items.map((delivery) => (
                        <div
                          key={delivery.id}
                          className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                                {humanizeToken(delivery.audience_key)} / {delivery.recipient_email}
                              </p>
                              <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                                {humanizeToken(delivery.delivery_channel)} / {humanizeToken(delivery.cadence)}
                              </p>
                            </div>
                            <GrowthStatusChip
                              label={humanizeToken(delivery.delivery_status)}
                              tone={reportingDeliveryTone(delivery)}
                            />
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2 text-xs font-mono text-muted-foreground">
                            <GrowthStatusChip
                              label={`${delivery.window_start} -> ${delivery.window_end}`}
                              tone="neutral"
                            />
                            <GrowthStatusChip
                              label={humanizeToken(delivery.freshness_status)}
                              tone={reportingHealthTone(delivery.freshness_status)}
                            />
                            <GrowthStatusChip
                              label={humanizeToken(delivery.template_key)}
                              tone="info"
                            />
                            {delivery.provider_name ? (
                              <GrowthStatusChip
                                label={humanizeToken(delivery.provider_name)}
                                tone="info"
                              />
                            ) : null}
                          </div>
                          <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                            {delivery.subject_line}
                          </p>
                          {delivery.failure_message || delivery.status_reason ? (
                            <p className="mt-3 text-sm font-mono leading-6 text-neon-pink">
                              {delivery.failure_message ?? delivery.status_reason}
                            </p>
                          ) : null}
                          <div className="mt-4 flex flex-wrap justify-end gap-2">
                            {delivery.can_export_artifact ? (
                              <button
                                type="button"
                                onClick={() => {
                                  exportReportingDeliveryArtifactMutation.mutate(delivery.id);
                                }}
                                disabled={exportReportingDeliveryArtifactMutation.isPending}
                                className="inline-flex items-center gap-2 rounded-2xl border border-grid-line/20 px-3 py-2 text-xs font-mono uppercase tracking-[0.16em] text-white transition-colors hover:border-neon-cyan/40 hover:bg-terminal-bg/55 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                <Download className="h-4 w-4" />
                                {t('overview.reporting.deliveries.actions.export')}
                              </button>
                            ) : null}
                          </div>
                        </div>
                      ))
                    ) : (
                      <GrowthEmptyState label={t('overview.reporting.deliveries.empty')} />
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <GrowthEmptyState label={t('overview.reporting.empty')} />
            </div>
          )}
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.deliveryOpsTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('overview.deliveryOpsDescription')}
              </p>
            </div>
            <GrowthStatusChip label={t('overview.deliveryOpsLive')} tone="info" />
          </div>

          <form
            className="mt-5 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              manualNotifyMutation.mutate();
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm font-mono text-muted-foreground">
                <span>{t('overview.deliveryOps.fields.userId')}</span>
                <input
                  value={manualForm.mobileUserId}
                  onChange={(event) =>
                    setManualForm((current) => ({
                      ...current,
                      mobileUserId: event.target.value,
                    }))
                  }
                  className="w-full rounded-2xl border border-grid-line/25 bg-terminal-bg/45 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-neon-cyan/45"
                  placeholder="uuid"
                  required
                />
              </label>
              <label className="space-y-2 text-sm font-mono text-muted-foreground">
                <span>{t('overview.deliveryOps.fields.routeSlug')}</span>
                <input
                  value={manualForm.routeSlug}
                  onChange={(event) =>
                    setManualForm((current) => ({
                      ...current,
                      routeSlug: event.target.value,
                    }))
                  }
                  className="w-full rounded-2xl border border-grid-line/25 bg-terminal-bg/45 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-neon-cyan/45"
                  placeholder="/referral"
                />
              </label>
            </div>

            <label className="space-y-2 text-sm font-mono text-muted-foreground">
              <span>{t('overview.deliveryOps.fields.title')}</span>
              <input
                value={manualForm.title}
                onChange={(event) =>
                  setManualForm((current) => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
                className="w-full rounded-2xl border border-grid-line/25 bg-terminal-bg/45 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-neon-cyan/45"
                required
              />
            </label>

            <label className="space-y-2 text-sm font-mono text-muted-foreground">
              <span>{t('overview.deliveryOps.fields.message')}</span>
              <textarea
                value={manualForm.message}
                onChange={(event) =>
                  setManualForm((current) => ({
                    ...current,
                    message: event.target.value,
                  }))
                }
                className="min-h-28 w-full rounded-2xl border border-grid-line/25 bg-terminal-bg/45 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-neon-cyan/45"
                required
              />
            </label>

            <label className="space-y-2 text-sm font-mono text-muted-foreground">
              <span>{t('overview.deliveryOps.fields.notes')}</span>
              <textarea
                value={manualForm.notes}
                onChange={(event) =>
                  setManualForm((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))
                }
                className="min-h-24 w-full rounded-2xl border border-grid-line/25 bg-terminal-bg/45 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-neon-cyan/45"
                placeholder={t('overview.deliveryOps.notesPlaceholder')}
              />
            </label>

            <div className="flex flex-wrap gap-2">
              {([
                ['inApp', t('overview.deliveryOps.channels.inApp')],
                ['email', t('overview.deliveryOps.channels.email')],
                ['telegram', t('overview.deliveryOps.channels.telegram')],
              ] as const).map(([stateKey, label]) => (
                <button
                  key={stateKey}
                  type="button"
                  onClick={() =>
                    setManualForm((current) => ({
                      ...current,
                      channels: {
                        ...current.channels,
                        [stateKey]: !current.channels[stateKey],
                      },
                    }))
                  }
                  className={[
                    'rounded-full border px-3 py-1 text-xs font-mono transition-colors',
                    manualForm.channels[stateKey]
                      ? 'border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan'
                      : 'border-grid-line/30 bg-terminal-bg/30 text-muted-foreground',
                  ].join(' ')}
                  aria-pressed={manualForm.channels[stateKey]}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-mono text-muted-foreground">
                {manualNotifyMutation.isError
                  ? t('overview.deliveryOps.manualFailed')
                  : t('overview.deliveryOps.manualHint')}
              </p>
              <button
                type="submit"
                disabled={manualNotifyMutation.isPending}
                className="rounded-full border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 text-xs font-display uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/70 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {manualNotifyMutation.isPending
                  ? t('overview.deliveryOps.sending')
                  : t('overview.deliveryOps.send')}
              </button>
            </div>
          </form>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.deliveryFeedTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('overview.deliveryFeedDescription')}
              </p>
            </div>
            <GrowthStatusChip
              label={formatCompactNumber(deliveriesQuery.data?.total ?? 0, locale)}
              tone="neutral"
            />
          </div>

          <div className="mt-5 flex gap-3">
            <input
              value={deliveryFilterUserId}
              onChange={(event) => setDeliveryFilterUserId(event.target.value)}
              className="w-full rounded-2xl border border-grid-line/25 bg-terminal-bg/45 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-neon-cyan/45"
              placeholder={t('overview.deliveryOps.fields.filterUserId')}
            />
          </div>

          <div className="mt-5 space-y-3">
            {deliveriesQuery.isLoading ? (
              Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={index}
                  className="h-28 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))
            ) : deliveries.length ? (
              deliveries.map((delivery) => (
                <article
                  key={delivery.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {delivery.title}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {delivery.delivery_channel} / {delivery.user?.email ?? delivery.mobile_user_id}
                      </p>
                    </div>
                    <GrowthStatusChip
                      label={humanizeToken(delivery.delivery_status)}
                      tone={deliveryTone(delivery)}
                    />
                  </div>

                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {delivery.message}
                  </p>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <GrowthStatusChip
                      label={humanizeToken(delivery.notification_kind)}
                      tone="info"
                    />
                    <GrowthStatusChip
                      label={formatDateTime(delivery.planned_at, locale)}
                      tone="neutral"
                    />
                    {delivery.queue_status ? (
                      <GrowthStatusChip
                        label={`${t('overview.deliveryOps.queueStatus')} ${humanizeToken(delivery.queue_status)}`}
                        tone="warning"
                      />
                    ) : null}
                  </div>

                  {delivery.status_reason || delivery.queue_error_message ? (
                    <p className="mt-3 text-xs font-mono leading-5 text-neon-pink">
                      {delivery.queue_error_message ?? delivery.status_reason}
                    </p>
                  ) : null}

                  <div className="mt-4 flex flex-wrap gap-2">
                    {delivery.can_resend ? (
                      <button
                        type="button"
                        onClick={() =>
                          deliveryActionMutation.mutate({
                            deliveryId: delivery.id,
                            action: 'resend',
                          })
                        }
                        disabled={deliveryActionMutation.isPending}
                        className="rounded-full border border-neon-cyan/40 bg-neon-cyan/10 px-3 py-1 text-xs font-mono text-neon-cyan transition-colors hover:border-neon-cyan/70 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {t('overview.deliveryOps.actions.resend')}
                      </button>
                    ) : null}
                    {delivery.can_pause ? (
                      <button
                        type="button"
                        onClick={() =>
                          deliveryActionMutation.mutate({
                            deliveryId: delivery.id,
                            action: 'pause',
                          })
                        }
                        disabled={deliveryActionMutation.isPending}
                        className="rounded-full border border-amber-300/40 bg-amber-300/10 px-3 py-1 text-xs font-mono text-amber-300 transition-colors hover:border-amber-300/70 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {t('overview.deliveryOps.actions.pause')}
                      </button>
                    ) : null}
                    {delivery.can_revoke ? (
                      <button
                        type="button"
                        onClick={() =>
                          deliveryActionMutation.mutate({
                            deliveryId: delivery.id,
                            action: 'revoke',
                          })
                        }
                        disabled={deliveryActionMutation.isPending}
                        className="rounded-full border border-neon-pink/40 bg-neon-pink/10 px-3 py-1 text-xs font-mono text-neon-pink transition-colors hover:border-neon-pink/70 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {t('overview.deliveryOps.actions.revoke')}
                      </button>
                    ) : null}
                    {delivery.can_resolve ? (
                      <button
                        type="button"
                        onClick={() =>
                          deliveryActionMutation.mutate({
                            deliveryId: delivery.id,
                            action: 'resolve',
                          })
                        }
                        disabled={deliveryActionMutation.isPending}
                        className="rounded-full border border-emerald-400/40 bg-emerald-400/10 px-3 py-1 text-xs font-mono text-emerald-300 transition-colors hover:border-emerald-300/70 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {t('overview.deliveryOps.actions.resolve')}
                      </button>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => setSelectedDeliveryId(delivery.id)}
                      className="rounded-full border border-grid-line/40 bg-terminal-bg/30 px-3 py-1 text-xs font-mono text-white transition-colors hover:border-neon-cyan/60 hover:text-neon-cyan"
                    >
                      {t('overview.deliveryOps.actions.inspect')}
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <GrowthEmptyState label={t('overview.deliveryFeedEmpty')} />
            )}
          </div>
        </article>
      </div>

      <Modal
        isOpen={selectedDeliveryId !== null}
        onClose={() => setSelectedDeliveryId(null)}
        title={t('overview.deliveryForensics.title')}
      >
        {deliveryDetailQuery.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
              />
            ))}
          </div>
        ) : deliveryDetailQuery.data ? (
          <GrowthDeliveryForensicsContent
            detail={deliveryDetailQuery.data}
            locale={locale}
            onExport={() => {
              if (selectedDeliveryId) {
                exportDeliveryMutation.mutate(selectedDeliveryId);
              }
            }}
            isExporting={exportDeliveryMutation.isPending}
          />
        ) : (
          <GrowthEmptyState label={t('overview.deliveryForensics.empty')} />
        )}
      </Modal>
    </GrowthPageShell>
  );
}

function GrowthDeliveryForensicsContent({
  detail,
  locale,
  onExport,
  isExporting,
}: {
  detail: AdminGrowthNotificationDeliveryDetail;
  locale: string;
  onExport: () => void;
  isExporting: boolean;
}) {
  const t = useTranslations('Growth');
  const sourceMetadata = Object.entries(detail.source_summary?.metadata ?? {});

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
            {detail.delivery.title}
          </p>
          <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {detail.delivery.delivery_channel} / {detail.delivery.user?.email ?? detail.delivery.mobile_user_id}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <GrowthStatusChip label={humanizeToken(detail.troubleshooting_state)} tone={deliveryTone(detail.delivery)} />
          <button
            type="button"
            onClick={onExport}
            disabled={isExporting}
            className="inline-flex items-center gap-2 rounded-full border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-2 text-xs font-mono text-neon-cyan transition-colors hover:border-neon-cyan/70 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Download className="h-3.5 w-3.5" />
            {isExporting
              ? t('overview.deliveryForensics.exporting')
              : t('overview.deliveryForensics.export')}
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
        <p className="text-xs font-display uppercase tracking-[0.18em] text-white">
          {t('overview.deliveryForensics.supportSummary')}
        </p>
        <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
          {detail.support_summary}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <GrowthStatusChip label={detail.customer_message_key} tone="info" />
          <GrowthStatusChip label={formatDateTime(detail.delivery.updated_at, locale)} tone="neutral" />
        </div>
      </div>

      <section className="space-y-3">
        <h3 className="text-xs font-display uppercase tracking-[0.18em] text-white">
          {t('overview.deliveryForensics.siblingTitle')}
        </h3>
        {detail.sibling_deliveries.length ? (
          detail.sibling_deliveries.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-mono text-white">{item.delivery_channel}</p>
                <GrowthStatusChip label={humanizeToken(item.delivery_status)} tone={deliveryTone(item)} />
              </div>
              <p className="mt-2 text-xs font-mono text-muted-foreground">
                {formatDateTime(item.updated_at, locale)}
              </p>
            </div>
          ))
        ) : (
          <GrowthEmptyState label={t('overview.deliveryForensics.siblingEmpty')} />
        )}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
          <h3 className="text-xs font-display uppercase tracking-[0.18em] text-white">
            {t('overview.deliveryForensics.queueTitle')}
          </h3>
          {detail.queue_snapshot ? (
            <div className="mt-3 space-y-2 text-sm font-mono text-muted-foreground">
              <p>{humanizeToken(detail.queue_snapshot.status)}</p>
              <p>{t('overview.deliveryForensics.queueAttempts', { count: detail.queue_snapshot.attempts })}</p>
              <p>{formatDateTime(detail.queue_snapshot.scheduled_at, locale)}</p>
              {detail.queue_snapshot.error_message ? (
                <p className="text-neon-pink">{detail.queue_snapshot.error_message}</p>
              ) : null}
            </div>
          ) : (
            <GrowthEmptyState label={t('overview.deliveryForensics.queueEmpty')} />
          )}
        </div>

        <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
          <h3 className="text-xs font-display uppercase tracking-[0.18em] text-white">
            {t('overview.deliveryForensics.sourceTitle')}
          </h3>
          {detail.source_summary ? (
            <div className="mt-3 space-y-2 text-sm font-mono text-muted-foreground">
              <p className="text-white">{detail.source_summary.source_label ?? humanizeToken(detail.source_summary.source_kind)}</p>
              {detail.source_summary.source_status ? (
                <p>{humanizeToken(detail.source_summary.source_status)}</p>
              ) : null}
              {sourceMetadata.length ? (
                <div className="space-y-1">
                  {sourceMetadata.map(([key, value]) => (
                    <p key={key}>
                      {humanizeToken(key)}: {String(value)}
                    </p>
                  ))}
                </div>
              ) : null}
            </div>
          ) : (
            <GrowthEmptyState label={t('overview.deliveryForensics.sourceEmpty')} />
          )}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-xs font-display uppercase tracking-[0.18em] text-white">
          {t('overview.deliveryForensics.timelineTitle')}
        </h3>
        {detail.event_timeline.length ? (
          detail.event_timeline.map((event) => (
            <div
              key={event.id}
              className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {humanizeToken(event.event_type)}
                </p>
                <GrowthStatusChip label={humanizeToken(event.delivery_status)} tone="neutral" />
              </div>
              <p className="mt-2 text-xs font-mono text-muted-foreground">
                {formatDateTime(event.occurred_at, locale)}
              </p>
              {event.reason_code ? (
                <p className="mt-2 text-xs font-mono text-neon-pink">{event.reason_code}</p>
              ) : null}
            </div>
          ))
        ) : (
          <GrowthEmptyState label={t('overview.deliveryForensics.timelineEmpty')} />
        )}
      </section>
    </div>
  );
}

function deliveryTone(delivery: AdminGrowthNotificationDelivery) {
  if (delivery.delivery_status === 'delivered') {
    return 'success' as const;
  }
  if (delivery.delivery_status === 'failed' || delivery.delivery_status === 'revoked') {
    return 'danger' as const;
  }
  if (delivery.delivery_status === 'paused' || delivery.delivery_status === 'queued') {
    return 'warning' as const;
  }
  return 'neutral' as const;
}
