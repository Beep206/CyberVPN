'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Megaphone, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import type { PartnerRouteAccessLevel } from '@/features/partner-portal-state/lib/portal-access';
import {
  getPartnerCampaignCapabilities,
  getPartnerCommercialSurfaceMode,
} from '@/features/partner-commercial/lib/commercial-capabilities';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';

const FIELD_CLASS_NAME = 'w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20';
const TEXTAREA_CLASS_NAME = `${FIELD_CLASS_NAME} min-h-[120px] resize-y`;

const CAMPAIGN_CHANNELS = ['content', 'telegram', 'paid_social', 'search', 'storefront'] as const;

function isWriteAccess(access: PartnerRouteAccessLevel) {
  return access === 'write' || access === 'admin';
}

export function CampaignsEnablementPage() {
  const t = useTranslations('Partner.campaigns');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const { state, activeWorkspace } = usePartnerPortalRuntimeState();
  const mode = getPartnerCommercialSurfaceMode('campaigns', state);
  const capabilities = getPartnerCampaignCapabilities(state);
  const activeWorkspaceId = activeWorkspace?.id ?? null;

  const [scopeLabel, setScopeLabel] = useState('');
  const [creativeRef, setCreativeRef] = useState('');
  const [campaignChannel, setCampaignChannel] = useState<(typeof CAMPAIGN_CHANNELS)[number]>('content');
  const [requestDetails, setRequestDetails] = useState('');
  const [actionFeedback, setActionFeedback] = useState<{
    tone: 'success' | 'error';
    message: string;
  } | null>(null);

  const submitCreativeApprovalMutation = useMutation({
    mutationFn: async () => {
      if (!activeWorkspaceId) {
        throw new Error(t('submission.workspaceRequired'));
      }

      return partnerPortalApi.submitWorkspaceCreativeApproval(activeWorkspaceId, {
        scope_label: scopeLabel.trim(),
        creative_ref: creativeRef.trim() || null,
        approval_payload: {
          channel: campaignChannel,
          request_origin: 'partner_portal_campaigns_surface',
          requested_surface_mode: mode,
        },
        notes: requestDetails.trim() ? [requestDetails.trim()] : [],
      });
    },
    onSuccess: async () => {
      if (activeWorkspaceId) {
        await Promise.all([
          queryClient.invalidateQueries({
            queryKey: ['partner-portal', 'workspace-campaign-assets', activeWorkspaceId],
          }),
          queryClient.invalidateQueries({
            queryKey: ['partner-portal', 'workspace-traffic-declarations', activeWorkspaceId],
          }),
        ]);
      }
      setScopeLabel('');
      setCreativeRef('');
      setCampaignChannel('content');
      setRequestDetails('');
      setActionFeedback({
        tone: 'success',
        message: t('submission.success'),
      });
    },
    onError: (error) => {
      setActionFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : t('submission.error'),
      });
    },
  });

  return (
    <PartnerRouteGuard route="campaigns" title={t('title')}>
      {(access) => {
        const canWrite = isWriteAccess(access);

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

                <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[340px]">
                  <div className="flex items-center justify-between gap-3">
                    <span>{t('summary.currentLane')}</span>
                    <span className="text-foreground">
                      {state.primaryLane
                        ? portalT(`laneLabels.${state.primaryLane}`)
                        : portalT('noLane')}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.routeAccess')}</span>
                    <span className="text-neon-cyan">
                      {portalT(`routeAccess.${access}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.surfaceMode')}</span>
                    <span className="text-foreground">
                      {portalT(`commercialModes.${mode}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.compliance')}</span>
                    <span className="text-foreground">
                      {portalT(`complianceStates.${state.complianceReadiness}`)}
                    </span>
                  </div>
                </div>
              </div>
            </header>

            {actionFeedback ? (
              <div
                className={`rounded-2xl border px-4 py-3 text-sm font-mono ${
                  actionFeedback.tone === 'success'
                    ? 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green'
                    : 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink'
                }`}
              >
                {actionFeedback.message}
              </div>
            ) : null}

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
                <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                  <Megaphone className="h-5 w-5 text-neon-cyan" />
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('library.title')}
                    </h2>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('library.description')}
                    </p>
                  </div>
                </div>

                <div className="mt-5 space-y-3">
                  {state.campaignAssets.length > 0 ? state.campaignAssets.map((asset) => (
                    <article
                      key={asset.id}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                    >
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                            {asset.name}
                          </h3>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {t('library.approvalOwner', { value: asset.approvalOwner })}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {portalT(`campaignChannels.${asset.channel}`)}
                          </p>
                          <p className="mt-2 text-xs font-mono text-muted-foreground">
                            {portalT(`campaignStatuses.${asset.status}`)}
                          </p>
                        </div>
                      </div>
                      <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                        {asset.notes.map((note) => (
                          <li key={note}>{note}</li>
                        ))}
                      </ul>
                    </article>
                  )) : (
                    <p className="rounded-2xl border border-dashed border-grid-line/25 bg-terminal-surface/25 p-4 text-sm font-mono leading-6 text-muted-foreground">
                      {t('library.empty')}
                    </p>
                  )}
                </div>
              </article>

              <div className="space-y-6">
                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <Sparkles className="h-5 w-5 text-neon-purple" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('capabilities.title')}
                    </h2>
                  </div>
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
                          {portalT(`capabilityAvailability.${capability.availability}`)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('actions.title')}
                  </h2>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {!canWrite || mode === 'read_only'
                      ? t('actions.readOnly')
                      : mode === 'starter'
                        ? t('actions.starter')
                        : mode === 'controlled'
                          ? t('actions.controlled')
                          : t('actions.full')}
                  </p>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('submission.title')}
                  </h2>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {canWrite ? t('submission.description') : t('submission.readOnly')}
                  </p>
                  <div className="mt-4 space-y-3">
                    <input
                      className={FIELD_CLASS_NAME}
                      value={scopeLabel}
                      onChange={(event) => {
                        setScopeLabel(event.target.value);
                        setActionFeedback(null);
                      }}
                      placeholder={t('submission.scopePlaceholder')}
                      disabled={!canWrite}
                    />
                    <input
                      className={FIELD_CLASS_NAME}
                      value={creativeRef}
                      onChange={(event) => {
                        setCreativeRef(event.target.value);
                        setActionFeedback(null);
                      }}
                      placeholder={t('submission.referencePlaceholder')}
                      disabled={!canWrite}
                    />
                    <select
                      className={FIELD_CLASS_NAME}
                      value={campaignChannel}
                      onChange={(event) => {
                        setCampaignChannel(event.target.value as (typeof CAMPAIGN_CHANNELS)[number]);
                        setActionFeedback(null);
                      }}
                      disabled={!canWrite}
                    >
                      {CAMPAIGN_CHANNELS.map((channel) => (
                        <option key={channel} value={channel}>
                          {portalT(`campaignChannels.${channel}`)}
                        </option>
                      ))}
                    </select>
                    <textarea
                      className={TEXTAREA_CLASS_NAME}
                      value={requestDetails}
                      onChange={(event) => {
                        setRequestDetails(event.target.value);
                        setActionFeedback(null);
                      }}
                      placeholder={t('submission.detailsPlaceholder')}
                      disabled={!canWrite}
                    />
                    <Button
                      type="button"
                      className="bg-neon-cyan text-black hover:bg-neon-cyan/90 font-mono text-xs uppercase tracking-[0.18em]"
                      disabled={submitCreativeApprovalMutation.isPending || !canWrite || scopeLabel.trim().length === 0}
                      onClick={() => void submitCreativeApprovalMutation.mutateAsync()}
                    >
                      {submitCreativeApprovalMutation.isPending
                        ? t('submission.submitting')
                        : t('submission.submitAction')}
                    </Button>
                  </div>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('links.title')}
                  </h2>
                  <div className="mt-4 flex flex-col gap-3">
                    <Link href="/codes" className="text-sm font-mono text-neon-cyan underline underline-offset-4">
                      {t('links.codes')}
                    </Link>
                    <Link href="/compliance" className="text-sm font-mono text-neon-purple underline underline-offset-4">
                      {t('links.compliance')}
                    </Link>
                    <Link href="/legal" className="text-sm font-mono text-matrix-green underline underline-offset-4">
                      {t('links.legal')}
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
