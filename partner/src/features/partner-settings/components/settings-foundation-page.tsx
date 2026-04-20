'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { BellRing, LockKeyhole, RotateCcw, Save, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { getPartnerRoleRouteAccess } from '@/features/partner-portal-state/lib/portal-access';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  EMPTY_PARTNER_SETTINGS_FOUNDATION_DRAFT,
  type PartnerSettingsFoundationDraft,
} from '@/features/partner-settings/lib/settings-foundation-storage';
import {
  buildWorkspaceSettingsPayload,
  mapWorkspaceSettingsToDraft,
} from '@/features/partner-settings/lib/workspace-settings-contract';

const FIELD_CLASS_NAME = 'w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20';

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

function ToggleField({
  checked,
  description,
  disabled,
  label,
  onChange,
}: {
  checked: boolean;
  description: string;
  disabled?: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-4">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-1 h-4 w-4 rounded border-grid-line bg-terminal-bg text-neon-cyan focus:ring-neon-cyan/50"
      />
      <span className="space-y-1">
        <span className="block text-sm font-display uppercase tracking-[0.14em] text-white">
          {label}
        </span>
        <span className="block text-sm font-mono leading-6 text-muted-foreground">
          {description}
        </span>
      </span>
    </label>
  );
}

export function SettingsFoundationPage() {
  const locale = useLocale();
  const t = useTranslations('Partner.settings');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const { state: portalState, activeWorkspace } = usePartnerPortalRuntimeState();

  const [localDraft, setLocalDraft] = useState<PartnerSettingsFoundationDraft | null>(null);
  const [saveState, setSaveState] = useState<'idle' | 'saved' | 'error'>('idle');

  const routeAccess = getPartnerRoleRouteAccess('settings', portalState);
  const isReadOnly = routeAccess === 'read';

  const workspaceSettingsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-settings', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      const response = await partnerPortalApi.getWorkspaceSettings(activeWorkspace.id);
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const canonicalDraft = useMemo(
    () => (workspaceSettingsQuery.data
      ? mapWorkspaceSettingsToDraft(workspaceSettingsQuery.data)
      : {
          ...EMPTY_PARTNER_SETTINGS_FOUNDATION_DRAFT,
          preferredLanguage: locale,
        }),
    [locale, workspaceSettingsQuery.data],
  );

  const effectiveDraft = localDraft ?? canonicalDraft;
  const savedAt = formatSavedAt(
    localDraft?.updatedAt ?? workspaceSettingsQuery.data?.updated_at ?? null,
    locale,
  );
  const securityScore = [
    effectiveDraft.workspaceSecurityAlerts,
    effectiveDraft.payoutStatusEmails,
    effectiveDraft.requireMfaForWorkspace,
    effectiveDraft.reviewedActiveSessions,
  ].filter(Boolean).length;

  const updateSettingsMutation = useMutation({
    mutationFn: async (draft: PartnerSettingsFoundationDraft) => {
      if (!activeWorkspace) {
        throw new Error('Partner workspace is not available.');
      }
      const response = await partnerPortalApi.updateWorkspaceSettings(
        activeWorkspace.id,
        buildWorkspaceSettingsPayload(draft),
      );
      return response.data;
    },
    onSuccess: async (data) => {
      queryClient.setQueryData(
        ['partner-portal', 'workspace-settings', activeWorkspace?.id ?? null],
        data,
      );
      await queryClient.invalidateQueries({ queryKey: ['partner-portal', 'workspace-settings', activeWorkspace?.id ?? null] });
      setLocalDraft(null);
      setSaveState('saved');
    },
    onError: () => {
      setSaveState('error');
    },
  });

  const handleFieldChange = <Key extends keyof PartnerSettingsFoundationDraft>(
    key: Key,
    value: PartnerSettingsFoundationDraft[Key],
  ) => {
    setLocalDraft({
      ...effectiveDraft,
      [key]: value,
      updatedAt: new Date().toISOString(),
    });
    setSaveState('idle');
  };

  const handleSave = () => {
    void updateSettingsMutation.mutateAsync(effectiveDraft);
  };

  const handleReset = () => {
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
              <span>{t('summary.securityCoverage')}</span>
              <span className="text-neon-cyan">{securityScore}/4</span>
            </div>
            <p className="mt-3 text-xs leading-5">
              {savedAt ? t('summary.savedAt', { value: savedAt }) : t('summary.notSaved')}
            </p>
            <p className="mt-2 text-xs leading-5">
              {t('summary.cookieModel')}
            </p>
          </div>
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <article className="space-y-6 rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan">
                <ShieldCheck className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('identity.title')}
                </h2>
                <p className="mt-1 text-xs font-mono leading-5 text-muted-foreground">
                  {t('identity.description')}
                </p>
              </div>
            </div>

            <dl className="grid gap-3 rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-4 text-sm font-mono text-muted-foreground md:grid-cols-2">
              <div className="space-y-1">
                <dt>{t('identity.items.email')}</dt>
                <dd className="text-foreground">{workspaceSettingsQuery.data?.operator_email ?? '—'}</dd>
              </div>
              <div className="space-y-1">
                <dt>{t('identity.items.role')}</dt>
                <dd className="text-foreground">{workspaceSettingsQuery.data?.operator_role ?? '—'}</dd>
              </div>
              <div className="space-y-1">
                <dt>{t('identity.items.emailVerified')}</dt>
                <dd className={cn(workspaceSettingsQuery.data?.is_email_verified ? 'text-matrix-green' : 'text-neon-pink')}>
                  {workspaceSettingsQuery.data?.is_email_verified ? t('identity.values.yes') : t('identity.values.no')}
                </dd>
              </div>
              <div className="space-y-1">
                <dt>{t('identity.items.sessionModel')}</dt>
                <dd className="text-foreground">{t('identity.values.cookieBacked')}</dd>
              </div>
            </dl>
          </section>

          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-neon-purple/30 bg-neon-purple/10 text-neon-purple">
                <BellRing className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('preferences.title')}
                </h2>
                <p className="mt-1 text-xs font-mono leading-5 text-muted-foreground">
                  {t('preferences.description')}
                </p>
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-mono text-muted-foreground">{t('fields.preferredLanguage')}</span>
                <input
                  className={FIELD_CLASS_NAME}
                  value={effectiveDraft.preferredLanguage}
                  disabled={isReadOnly || updateSettingsMutation.isPending}
                  onChange={(event) => handleFieldChange('preferredLanguage', event.target.value)}
                  placeholder={t('placeholders.preferredLanguage')}
                />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-mono text-muted-foreground">{t('fields.preferredCurrency')}</span>
                <input
                  className={FIELD_CLASS_NAME}
                  value={effectiveDraft.preferredCurrency}
                  disabled={isReadOnly || updateSettingsMutation.isPending}
                  onChange={(event) => handleFieldChange('preferredCurrency', event.target.value)}
                  placeholder={t('placeholders.preferredCurrency')}
                />
              </label>
            </div>

            <div className="grid gap-3">
              <ToggleField
                checked={effectiveDraft.workspaceSecurityAlerts}
                disabled={isReadOnly || updateSettingsMutation.isPending}
                label={t('toggles.workspaceSecurityAlerts.label')}
                description={t('toggles.workspaceSecurityAlerts.description')}
                onChange={(checked) => handleFieldChange('workspaceSecurityAlerts', checked)}
              />
              <ToggleField
                checked={effectiveDraft.payoutStatusEmails}
                disabled={isReadOnly || updateSettingsMutation.isPending}
                label={t('toggles.payoutStatusEmails.label')}
                description={t('toggles.payoutStatusEmails.description')}
                onChange={(checked) => handleFieldChange('payoutStatusEmails', checked)}
              />
              <ToggleField
                checked={effectiveDraft.productAnnouncements}
                disabled={isReadOnly || updateSettingsMutation.isPending}
                label={t('toggles.productAnnouncements.label')}
                description={t('toggles.productAnnouncements.description')}
                onChange={(checked) => handleFieldChange('productAnnouncements', checked)}
              />
            </div>
          </section>

          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-matrix-green/30 bg-matrix-green/10 text-matrix-green">
                <LockKeyhole className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('security.title')}
                </h2>
                <p className="mt-1 text-xs font-mono leading-5 text-muted-foreground">
                  {t('security.description')}
                </p>
              </div>
            </div>

            <div className="grid gap-3">
              <ToggleField
                checked={effectiveDraft.requireMfaForWorkspace}
                disabled={isReadOnly || updateSettingsMutation.isPending}
                label={t('toggles.requireMfaForWorkspace.label')}
                description={t('toggles.requireMfaForWorkspace.description')}
                onChange={(checked) => handleFieldChange('requireMfaForWorkspace', checked)}
              />
              <ToggleField
                checked={effectiveDraft.preferPasskeys}
                disabled={isReadOnly || updateSettingsMutation.isPending}
                label={t('toggles.preferPasskeys.label')}
                description={t('toggles.preferPasskeys.description')}
                onChange={(checked) => handleFieldChange('preferPasskeys', checked)}
              />
              <ToggleField
                checked={effectiveDraft.reviewedActiveSessions}
                disabled={isReadOnly || updateSettingsMutation.isPending}
                label={t('toggles.reviewedActiveSessions.label')}
                description={t('toggles.reviewedActiveSessions.description')}
                onChange={(checked) => handleFieldChange('reviewedActiveSessions', checked)}
              />
            </div>
          </section>

          <div className="flex flex-col gap-3 border-t border-grid-line/20 pt-5 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                onClick={handleSave}
                disabled={isReadOnly || updateSettingsMutation.isPending}
                className="bg-neon-cyan text-black hover:bg-neon-cyan/90 font-mono text-xs uppercase tracking-[0.18em]"
              >
                <Save className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('actions.save')}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={handleReset}
                disabled={isReadOnly || updateSettingsMutation.isPending}
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
            <h2 className="text-sm font-display uppercase tracking-[0.16em] text-white">
              {t('nextSteps.title')}
            </h2>
            <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
              {t('nextSteps.description')}
            </p>
            <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
              <li>{t('nextSteps.items.mfa')}</li>
              <li>{t('nextSteps.items.sessions')}</li>
              <li>{t('nextSteps.items.notifications')}</li>
            </ul>
          </article>

          <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)]">
            <h2 className="text-sm font-display uppercase tracking-[0.16em] text-white">
              {t('links.title')}
            </h2>
            <div className="mt-4 flex flex-col gap-3">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-muted-foreground">
                <div className="flex items-center justify-between gap-3">
                  <span>{t('workspaceContext.role')}</span>
                  <span className="text-foreground">
                    {portalT(`workspaceRoles.${portalState.workspaceRole}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('workspaceContext.status')}</span>
                  <span className="text-foreground">
                    {portalT(`workspaceStatuses.${portalState.workspaceStatus}`)}
                  </span>
                </div>
              </div>
              <Link
                href="/application"
                className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4"
              >
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                {t('links.application')}
              </Link>
              <Link
                href="/organization"
                className="inline-flex items-center gap-2 text-sm font-mono text-neon-purple underline underline-offset-4"
              >
                <BellRing className="h-4 w-4" aria-hidden="true" />
                {t('links.organization')}
              </Link>
              <Link
                href="/team"
                className="inline-flex items-center gap-2 text-sm font-mono text-matrix-green underline underline-offset-4"
              >
                <LockKeyhole className="h-4 w-4" aria-hidden="true" />
                {t('links.team')}
              </Link>
              <Link
                href="/legal"
                className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4"
              >
                <LockKeyhole className="h-4 w-4" aria-hidden="true" />
                {t('links.legal')}
              </Link>
            </div>
          </article>
        </aside>
      </div>
    </section>
  );
}
