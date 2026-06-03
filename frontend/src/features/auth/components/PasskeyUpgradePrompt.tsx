'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { KeyRound, RefreshCw, X } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import { passkeysApi, type PasskeyCredential } from '@/lib/api';
import { completePasskeyRegistration } from '@/features/auth/lib/passkey-webauthn';

const PASSKEY_UPGRADE_DISMISSED_UNTIL_KEY = 'cybervpn.passkeyUpgrade.dismissedUntil';
const PASSKEY_UPGRADE_DISMISS_MS = 14 * 24 * 60 * 60 * 1000;
const PASSKEY_UPGRADE_STALE_MS = 5 * 60 * 1000;

function isPromptDismissed(): boolean {
  if (typeof window === 'undefined') {
    return true;
  }

  const dismissedUntil = Number(window.localStorage.getItem(PASSKEY_UPGRADE_DISMISSED_UNTIL_KEY));
  return Number.isFinite(dismissedUntil) && dismissedUntil > Date.now();
}

function writePromptDismissal(): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(
    PASSKEY_UPGRADE_DISMISSED_UNTIL_KEY,
    String(Date.now() + PASSKEY_UPGRADE_DISMISS_MS),
  );
}

export function PasskeyUpgradePrompt() {
  const t = useTranslations('Settings.cabinet.security.passkeys');
  const queryClient = useQueryClient();
  const [isDismissed, setIsDismissed] = useState(isPromptDismissed);
  const [errorVisible, setErrorVisible] = useState(false);

  const policyQuery = useQuery({
    queryKey: ['settings', 'passkey-policy'],
    queryFn: async () => {
      const response = await passkeysApi.getPolicy();
      return response.data;
    },
    enabled: !isDismissed,
    refetchOnWindowFocus: false,
    staleTime: PASSKEY_UPGRADE_STALE_MS,
  });

  const passkeysQuery = useQuery({
    queryKey: ['settings', 'passkeys'],
    queryFn: async () => {
      const response = await passkeysApi.list();
      return response.data;
    },
    enabled:
      !isDismissed &&
      policyQuery.data?.enabled === true &&
      policyQuery.data.registrationEnabled === true,
    refetchOnWindowFocus: false,
    staleTime: PASSKEY_UPGRADE_STALE_MS,
  });

  const addPasskeyMutation = useMutation({
    mutationFn: async () => {
      const response = await completePasskeyRegistration(null);
      return response.data;
    },
    onSuccess: (credential) => {
      queryClient.setQueryData(['settings', 'passkeys'], (current?: { credentials: PasskeyCredential[] }) => ({
        credentials: [
          credential,
          ...(current?.credentials ?? []).filter((item) => item.id !== credential.id),
        ],
      }));
      setErrorVisible(false);
    },
    onError: () => {
      setErrorVisible(true);
    },
  });

  const dismissPrompt = () => {
    writePromptDismissal();
    setIsDismissed(true);
  };

  const policy = policyQuery.data;
  const credentials = passkeysQuery.data?.credentials ?? [];

  if (
    isDismissed ||
    policyQuery.isPending ||
    policyQuery.isError ||
    !policy?.enabled ||
    !policy.registrationEnabled ||
    passkeysQuery.isPending ||
    passkeysQuery.isError ||
    credentials.length > 0
  ) {
    return null;
  }

  return (
    <section
      className="relative z-20 border-b border-matrix-green/25 bg-terminal-surface/90 px-4 py-3 backdrop-blur-xl md:px-6"
      aria-label={t('upgradeAriaLabel')}
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-3 rounded-xl border border-matrix-green/25 bg-matrix-green/10 p-3 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 gap-3">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-matrix-green/30 bg-black/30 text-matrix-green">
            <KeyRound className="h-4 w-4" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="font-mono text-sm font-semibold text-white">{t('upgradeTitle')}</p>
            <p className="mt-1 font-mono text-xs leading-5 text-muted-foreground">
              {errorVisible ? t('upgradeError') : t('upgradeDescription')}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 md:justify-end">
          <button
            type="button"
            onClick={() => addPasskeyMutation.mutate()}
            disabled={addPasskeyMutation.isPending}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-matrix-green/40 bg-matrix-green/15 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-matrix-green transition hover:bg-matrix-green/20 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-matrix-green focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-50"
          >
            {addPasskeyMutation.isPending ? (
              <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <KeyRound className="h-4 w-4" aria-hidden="true" />
            )}
            {addPasskeyMutation.isPending ? t('upgradeAdding') : t('upgradeAction')}
          </button>
          <Link
            href="/settings"
            className="inline-flex min-h-10 items-center justify-center rounded-lg border border-grid-line/35 bg-black/20 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
          >
            {t('upgradeSecondary')}
          </Link>
          <button
            type="button"
            onClick={dismissPrompt}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/35 bg-black/20 text-muted-foreground transition hover:border-grid-line/60 hover:text-white focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
            aria-label={t('dismissUpgrade')}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </section>
  );
}
