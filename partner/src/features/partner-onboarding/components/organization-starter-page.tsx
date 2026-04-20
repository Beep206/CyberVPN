'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Building2, Link2, RotateCcw, Save, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { useUser } from '@/stores/auth-store';
import { getPartnerRoleRouteAccess } from '@/features/partner-portal-state/lib/portal-access';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  EMPTY_PARTNER_APPLICATION_DRAFT,
  type PartnerApplicationDraft,
} from '@/features/partner-onboarding/lib/application-draft-storage';
import {
  buildOrganizationProfilePayload,
  mapOrganizationProfileToDraft,
} from '@/features/partner-onboarding/lib/organization-contract';

const FIELD_CLASS_NAME = 'w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20';
const TEXTAREA_CLASS_NAME = `${FIELD_CLASS_NAME} min-h-[120px] resize-y`;

function formatSavedAt(value: string | null, locale: string): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function buildFallbackDraft(
  activeWorkspaceName: string | null | undefined,
  userEmail: string | null | undefined,
): PartnerApplicationDraft {
  return {
    ...EMPTY_PARTNER_APPLICATION_DRAFT,
    workspaceName: activeWorkspaceName ?? '',
    contactEmail: userEmail ?? '',
  };
}

export function OrganizationStarterPage() {
  const locale = useLocale();
  const t = useTranslations('Partner.organization');
  const user = useUser();
  const queryClient = useQueryClient();
  const { state: portalState, activeWorkspace } = usePartnerPortalRuntimeState();

  const [localDraft, setLocalDraft] = useState<PartnerApplicationDraft | null>(null);
  const [saveState, setSaveState] = useState<'idle' | 'saved' | 'error'>('idle');

  const routeAccess = getPartnerRoleRouteAccess('organization', portalState);
  const isReadOnly = routeAccess === 'read';

  const organizationProfileQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-organization-profile', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      const response = await partnerPortalApi.getWorkspaceOrganizationProfile(activeWorkspace.id);
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const canonicalDraft = useMemo(
    () => (organizationProfileQuery.data
      ? mapOrganizationProfileToDraft(organizationProfileQuery.data)
      : buildFallbackDraft(activeWorkspace?.display_name, user?.email)),
    [activeWorkspace?.display_name, organizationProfileQuery.data, user?.email],
  );

  const effectiveDraft = localDraft ?? canonicalDraft;
  const savedAt = formatSavedAt(
    localDraft?.updatedAt ?? organizationProfileQuery.data?.updated_at ?? null,
    locale,
  );

  const organizationScore = [
    effectiveDraft.workspaceName,
    effectiveDraft.website,
    effectiveDraft.country,
    effectiveDraft.languages,
    effectiveDraft.supportContact,
    effectiveDraft.technicalContact,
  ].filter(Boolean).length;

  const updateOrganizationMutation = useMutation({
    mutationFn: async (draft: PartnerApplicationDraft) => {
      if (!activeWorkspace) {
        throw new Error('Partner workspace is not available.');
      }
      const response = await partnerPortalApi.updateWorkspaceOrganizationProfile(
        activeWorkspace.id,
        buildOrganizationProfilePayload(draft),
      );
      return response.data;
    },
    onSuccess: async (data) => {
      queryClient.setQueryData(
        ['partner-portal', 'workspace-organization-profile', activeWorkspace?.id ?? null],
        data,
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['partner-portal', 'session-bootstrap'] }),
        queryClient.invalidateQueries({ queryKey: ['partner-portal', 'workspace-organization-profile', activeWorkspace?.id ?? null] }),
      ]);
      setLocalDraft(null);
      setSaveState('saved');
    },
    onError: () => {
      setSaveState('error');
    },
  });

  const handleFieldChange = <Key extends keyof PartnerApplicationDraft>(
    key: Key,
    value: PartnerApplicationDraft[Key],
  ) => {
    setLocalDraft({
      ...effectiveDraft,
      [key]: value,
      reviewReady: false,
      updatedAt: new Date().toISOString(),
    });
    setSaveState('idle');
  };

  const handleSave = () => {
    void updateOrganizationMutation.mutateAsync(effectiveDraft);
  };

  const handleResetProfile = () => {
    setLocalDraft(null);
    setSaveState('idle');
  };

  return (
    <section className="space-y-6">
      <header className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <span className="inline-flex rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em] text-neon-cyan">
              {t('status.foundation')}
            </span>
            <div>
              <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                {t('eyebrow')}
              </p>
              <h1 className="mt-2 text-2xl font-display tracking-[0.16em] text-white md:text-3xl">
                {t('title')}
              </h1>
              <p className="mt-3 max-w-3xl text-sm font-mono leading-6 text-muted-foreground">
                {t('subtitle')}
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[320px]">
            <div className="flex items-center justify-between gap-3">
              <span>{t('summary.profileCoverage')}</span>
              <span className="text-neon-cyan">{organizationScore}/6</span>
            </div>
            <p className="mt-3 text-xs leading-5">
              {savedAt ? t('summary.savedAt', { value: savedAt }) : t('summary.notSaved')}
            </p>
            <p className="mt-2 text-xs leading-5">
              {organizationProfileQuery.isLoading
                ? t('summary.reviewPending')
                : t('summary.reviewReady')}
            </p>
          </div>
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
          {isReadOnly ? (
            <div className="mb-5 rounded-xl border border-grid-line/20 bg-terminal-surface/35 px-4 py-3 text-sm font-mono text-muted-foreground">
              {t('readOnlyMode')}
            </div>
          ) : null}
          <fieldset disabled={isReadOnly || updateOrganizationMutation.isPending} className="grid gap-5 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.workspaceName')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.workspaceName}
                onChange={(event) => handleFieldChange('workspaceName', event.target.value)}
                placeholder={t('placeholders.workspaceName')}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.website')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.website}
                onChange={(event) => handleFieldChange('website', event.target.value)}
                placeholder={t('placeholders.website')}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.country')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.country}
                onChange={(event) => handleFieldChange('country', event.target.value)}
                placeholder={t('placeholders.country')}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.operatingRegions')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.operatingRegions}
                onChange={(event) => handleFieldChange('operatingRegions', event.target.value)}
                placeholder={t('placeholders.operatingRegions')}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.languages')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.languages}
                onChange={(event) => handleFieldChange('languages', event.target.value)}
                placeholder={t('placeholders.languages')}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.primaryLane')}</span>
              <div className={cn(FIELD_CLASS_NAME, 'flex items-center border-dashed text-muted-foreground')}>
                {effectiveDraft.primaryLane ? t(`laneSummary.${effectiveDraft.primaryLane}`) : t('placeholders.primaryLane')}
              </div>
            </label>
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.contactName')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.contactName}
                onChange={(event) => handleFieldChange('contactName', event.target.value)}
                placeholder={t('placeholders.contactName')}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.contactEmail')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.contactEmail}
                onChange={(event) => handleFieldChange('contactEmail', event.target.value)}
                placeholder={t('placeholders.contactEmail')}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.supportContact')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.supportContact}
                onChange={(event) => handleFieldChange('supportContact', event.target.value)}
                placeholder={t('placeholders.supportContact')}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.technicalContact')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.technicalContact}
                onChange={(event) => handleFieldChange('technicalContact', event.target.value)}
                placeholder={t('placeholders.technicalContact')}
              />
            </label>
            <label className="space-y-2 md:col-span-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.financeContact')}</span>
              <input
                className={FIELD_CLASS_NAME}
                value={effectiveDraft.financeContact}
                onChange={(event) => handleFieldChange('financeContact', event.target.value)}
                placeholder={t('placeholders.financeContact')}
              />
            </label>
            <label className="space-y-2 md:col-span-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.businessDescription')}</span>
              <textarea
                className={TEXTAREA_CLASS_NAME}
                value={effectiveDraft.businessDescription}
                onChange={(event) => handleFieldChange('businessDescription', event.target.value)}
                placeholder={t('placeholders.businessDescription')}
              />
            </label>
            <label className="space-y-2 md:col-span-2">
              <span className="text-sm font-mono text-muted-foreground">{t('fields.acquisitionChannels')}</span>
              <textarea
                className={TEXTAREA_CLASS_NAME}
                value={effectiveDraft.acquisitionChannels}
                onChange={(event) => handleFieldChange('acquisitionChannels', event.target.value)}
                placeholder={t('placeholders.acquisitionChannels')}
              />
            </label>
          </fieldset>

          <div className="mt-6 flex flex-col gap-3 border-t border-grid-line/20 pt-5 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                onClick={handleSave}
                disabled={isReadOnly || updateOrganizationMutation.isPending}
                className="bg-neon-cyan text-black hover:bg-neon-cyan/90 font-mono text-xs uppercase tracking-[0.18em]"
              >
                <Save className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('actions.save')}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={handleResetProfile}
                disabled={isReadOnly || updateOrganizationMutation.isPending}
                className="border-grid-line/30 bg-terminal-surface/35 font-mono text-xs uppercase tracking-[0.18em]"
              >
                <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('actions.reset')}
              </Button>
            </div>

            {saveState !== 'idle' ? (
              <p className={cn(
                'text-sm font-mono',
                saveState === 'saved' ? 'text-matrix-green' : 'text-neon-pink',
              )}>
                {saveState === 'saved' ? t('saveFeedback.saved') : t('saveFeedback.error')}
              </p>
            ) : null}
          </div>
        </article>

        <aside className="space-y-6">
          <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)]">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan">
                <Building2 className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('readiness.title')}
                </h2>
                <p className="mt-1 text-xs font-mono leading-5 text-muted-foreground">
                  {t('readiness.description')}
                </p>
              </div>
            </div>

            <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
              <li>{t('readiness.items.workspace')}</li>
              <li>{t('readiness.items.contacts')}</li>
              <li>{t('readiness.items.geo')}</li>
              <li>{t('readiness.items.channels')}</li>
            </ul>
          </article>

          <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)]">
            <h2 className="text-sm font-display uppercase tracking-[0.16em] text-white">
              {t('links.title')}
            </h2>
            <div className="mt-4 flex flex-col gap-3">
              <Link
                href="/application"
                className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4"
              >
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                {t('links.application')}
              </Link>
              <Link
                href="/settings"
                className="inline-flex items-center gap-2 text-sm font-mono text-neon-purple underline underline-offset-4"
              >
                <Link2 className="h-4 w-4" aria-hidden="true" />
                {t('links.settings')}
              </Link>
              <Link
                href="/programs"
                className="inline-flex items-center gap-2 text-sm font-mono text-matrix-green underline underline-offset-4"
              >
                <Link2 className="h-4 w-4" aria-hidden="true" />
                {t('links.programs')}
              </Link>
            </div>
          </article>
        </aside>
      </div>
    </section>
  );
}
