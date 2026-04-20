'use client';

import { useState } from 'react';
import { BellRing, Smartphone } from 'lucide-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import {
  integrationsApi,
  type NotificationPreferencesResponse,
} from '@/lib/api/integrations';
import { IntegrationsPageShell } from '@/features/integrations/components/integrations-page-shell';
import { IntegrationsStatusChip } from '@/features/integrations/components/integrations-status-chip';
import {
  countEnabledChannels,
  formatDateTime,
  getErrorMessage,
} from '@/features/integrations/lib/formatting';

type PreferencesDraft = NotificationPreferencesResponse;

const DEFAULT_DRAFT: PreferencesDraft = {
  email_security: true,
  email_marketing: false,
  push_connection: true,
  push_payment: true,
  push_subscription: true,
};

export function PushOpsConsole() {
  const t = useTranslations('Integrations');
  const locale = useLocale();
  const [draftOverride, setDraftOverride] = useState<PreferencesDraft | null>(null);
  const [token, setToken] = useState('');
  const [deviceId, setDeviceId] = useState('admin-device-01');
  const [platform, setPlatform] = useState<'android' | 'ios'>('ios');

  const prefsQuery = useQuery({
    queryKey: ['integrations', 'push', 'preferences'],
    queryFn: async () => {
      const response = await integrationsApi.getNotificationPreferences();
      return response.data;
    },
    staleTime: 30_000,
  });

  const savePreferencesMutation = useMutation({
    mutationFn: async () => {
      const response = await integrationsApi.updateNotificationPreferences(draft);
      return response.data;
    },
    onSuccess: (data) => {
      setDraftOverride(data);
    },
  });

  const registerFcmMutation = useMutation({
    mutationFn: async () => {
      const response = await integrationsApi.registerFcmToken({
        token,
        device_id: deviceId,
        platform,
      });
      return response.data;
    },
  });

  const unregisterFcmMutation = useMutation({
    mutationFn: async () => {
      const response = await integrationsApi.unregisterFcmToken({
        device_id: deviceId,
      });
      return response.status;
    },
  });

  const draft = draftOverride ?? prefsQuery.data ?? DEFAULT_DRAFT;
  const enabledChannels = countEnabledChannels(draft);

  return (
    <IntegrationsPageShell
      eyebrow={t('push.eyebrow')}
      title={t('push.title')}
      description={t('push.description')}
      icon={BellRing}
      metrics={[
        {
          label: t('push.metrics.channels'),
          value: `${enabledChannels}/5`,
          hint: t('push.metrics.channelsHint'),
          tone: enabledChannels >= 3 ? 'success' : 'warning',
        },
        {
          label: t('push.metrics.device'),
          value: deviceId,
          hint: t('push.metrics.deviceHint'),
          tone: 'info',
        },
        {
          label: t('push.metrics.platform'),
          value: platform.toUpperCase(),
          hint: t('push.metrics.platformHint'),
          tone: 'neutral',
        },
        {
          label: t('push.metrics.scope'),
          value: t('push.metrics.scopeValue'),
          hint: t('push.metrics.scopeHint'),
          tone: 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <BellRing className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('push.preferencesTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('push.preferencesDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3">
            {(
              [
                ['email_security', t('push.toggles.emailSecurity')],
                ['email_marketing', t('push.toggles.emailMarketing')],
                ['push_connection', t('push.toggles.pushConnection')],
                ['push_payment', t('push.toggles.pushPayment')],
                ['push_subscription', t('push.toggles.pushSubscription')],
              ] as const
            ).map(([key, label]) => (
              <label
                key={key}
                className="flex items-center justify-between gap-4 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3"
              >
                <span className="text-sm font-mono text-white">{label}</span>
                <input
                  type="checkbox"
                  checked={draft[key]}
                  onChange={(event) =>
                    setDraftOverride({
                      ...draft,
                      [key]: event.target.checked,
                    })}
                  className="h-4 w-4 accent-cyan-400"
                />
              </label>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => savePreferencesMutation.mutate()}
              disabled={savePreferencesMutation.isPending}
              className="rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-sm font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15"
            >
              {savePreferencesMutation.isPending
                ? t('push.actions.saving')
                : t('push.actions.savePreferences')}
            </button>

            {savePreferencesMutation.data ? (
              <IntegrationsStatusChip
                label={t('push.savedLabel')}
                tone="success"
              />
            ) : null}
          </div>

          {savePreferencesMutation.error ? (
            <div className="mt-4 rounded-2xl border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
              {getErrorMessage(savePreferencesMutation.error)}
            </div>
          ) : null}
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Smartphone className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('push.fcmTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('push.fcmDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-4">
            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('push.fields.deviceId')}
              </span>
              <input
                value={deviceId}
                onChange={(event) => setDeviceId(event.target.value)}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/40"
              />
            </label>

            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('push.fields.platform')}
              </span>
              <select
                value={platform}
                onChange={(event) =>
                  setPlatform(event.target.value as 'android' | 'ios')}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors focus:border-neon-cyan/40"
              >
                <option value="ios">iOS</option>
                <option value="android">Android</option>
              </select>
            </label>

            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('push.fields.token')}
              </span>
              <textarea
                value={token}
                onChange={(event) => setToken(event.target.value)}
                rows={5}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/40"
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => registerFcmMutation.mutate()}
              disabled={!token || registerFcmMutation.isPending}
              className="rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-sm font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15"
            >
              {registerFcmMutation.isPending
                ? t('push.actions.registering')
                : t('push.actions.registerToken')}
            </button>

            <button
              type="button"
              onClick={() => unregisterFcmMutation.mutate()}
              disabled={!deviceId || unregisterFcmMutation.isPending}
              className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono uppercase tracking-[0.18em] text-white transition-colors hover:border-neon-cyan/35"
            >
              {unregisterFcmMutation.isPending
                ? t('push.actions.unregistering')
                : t('push.actions.unregisterToken')}
            </button>
          </div>

          {registerFcmMutation.data ? (
            <div className="mt-4 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('push.registeredTitle')}
                </p>
                <IntegrationsStatusChip
                  label={registerFcmMutation.data.platform}
                  tone="success"
                />
              </div>
              <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                {t('push.registeredSummary', {
                  createdAt: formatDateTime(
                    registerFcmMutation.data.created_at,
                    locale,
                  ),
                })}
              </p>
            </div>
          ) : null}

          {(registerFcmMutation.error || unregisterFcmMutation.error) ? (
            <div className="mt-4 rounded-2xl border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
              {getErrorMessage(
                registerFcmMutation.error || unregisterFcmMutation.error,
              )}
            </div>
          ) : null}
        </article>
      </div>
    </IntegrationsPageShell>
  );
}
