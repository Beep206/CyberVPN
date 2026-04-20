'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle,
  Copy,
  Key,
  ShieldCheck,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { twofaApi } from '@/lib/api/twofa';
import { SecurityEmptyState } from '@/features/security/components/security-empty-state';
import { SecurityPageShell } from '@/features/security/components/security-page-shell';
import { SecurityStatusChip } from '@/features/security/components/security-status-chip';
import { getErrorMessage } from '@/features/security/lib/formatting';

export function SecurityTwoFactorConsole() {
  const t = useTranslations('AdminSecurity');
  const queryClient = useQueryClient();
  const [reauthPassword, setReauthPassword] = useState('');
  const [setupCode, setSetupCode] = useState('');
  const [validateCode, setValidateCode] = useState('');
  const [disablePassword, setDisablePassword] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [secret, setSecret] = useState('');
  const [qrUri, setQrUri] = useState('');
  const [qrCodeDataUrl, setQrCodeDataUrl] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [validationState, setValidationState] = useState<boolean | null>(null);
  const [copiedSecret, setCopiedSecret] = useState(false);

  const statusQuery = useQuery({
    queryKey: ['security', 'two-factor', 'status'],
    queryFn: async () => {
      const response = await twofaApi.getStatus();
      return response.data;
    },
    staleTime: 15_000,
  });

  const setupMutation = useMutation({
    mutationFn: async (password: string) => {
      await twofaApi.reauth({ password });
      return twofaApi.setup();
    },
    onSuccess: async (response) => {
      const payload = response.data;
      setSecret(payload.secret);
      setQrUri(payload.qr_uri);
      setRecoveryCodes([]);
      setSetupCode('');
      setFeedback(t('twoFactor.setupReady'));

      const QRCode = (await import('qrcode')).default;
      const dataUrl = await QRCode.toDataURL(payload.qr_uri, {
        width: 240,
        margin: 2,
        color: {
          dark: '#ff00ff',
          light: '#0a0e1a',
        },
      });
      setQrCodeDataUrl(dataUrl);
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const verifyMutation = useMutation({
    mutationFn: (code: string) => twofaApi.verify({ code }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['security', 'two-factor', 'status'],
      });
      setSecret('');
      setQrUri('');
      setQrCodeDataUrl('');
      setReauthPassword('');
      setSetupCode('');
      setFeedback(t('twoFactor.enableSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const validateMutation = useMutation({
    mutationFn: (code: string) => twofaApi.validate({ code }),
    onSuccess: (response) => {
      setValidationState(response.data.valid);
      setFeedback(
        response.data.valid
          ? t('twoFactor.validateSuccess')
          : t('twoFactor.validateFailure'),
      );
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const disableMutation = useMutation({
    mutationFn: (payload: { password: string; code: string }) =>
      twofaApi.disable(payload),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: ['security', 'two-factor', 'status'],
      });
      setDisablePassword('');
      setDisableCode('');
      setValidationState(null);
      setRecoveryCodes(response.data.recovery_codes ?? []);
      setFeedback(t('twoFactor.disableSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const isEnabled = statusQuery.data?.status === 'enabled';

  async function copySecretToClipboard() {
    try {
      await navigator.clipboard.writeText(secret);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    } catch {
      setFeedback(t('twoFactor.copyFailure'));
    }
  }

  return (
    <SecurityPageShell
      eyebrow={t('twoFactor.eyebrow')}
      title={t('twoFactor.title')}
      description={t('twoFactor.description')}
      icon={ShieldCheck}
      metrics={[
        {
          label: t('twoFactor.metrics.status'),
          value: isEnabled ? t('common.enabled') : t('common.disabled'),
          hint: t('twoFactor.metrics.statusHint'),
          tone: isEnabled ? 'success' : 'warning',
        },
        {
          label: t('twoFactor.metrics.setup'),
          value: secret ? t('common.ready') : t('common.idle'),
          hint: t('twoFactor.metrics.setupHint'),
          tone: secret ? 'info' : 'neutral',
        },
        {
          label: t('twoFactor.metrics.validation'),
          value:
            validationState === null
              ? '--'
              : validationState
                ? t('common.valid')
                : t('common.invalid'),
          hint: t('twoFactor.metrics.validationHint'),
          tone:
            validationState === null
              ? 'neutral'
              : validationState
                ? 'success'
                : 'danger',
        },
        {
          label: t('twoFactor.metrics.recoveryCodes'),
          value: String(recoveryCodes.length),
          hint: t('twoFactor.metrics.recoveryCodesHint'),
          tone: recoveryCodes.length > 0 ? 'warning' : 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="space-y-6 xl:col-span-7">
          {feedback ? (
            <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}

          {!isEnabled ? (
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('twoFactor.setupTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('twoFactor.setupDescription')}
              </p>

              <div className="mt-5 space-y-4">
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.reauthPassword')}
                  </span>
                  <Input
                    type="password"
                    value={reauthPassword}
                    onChange={(event) => setReauthPassword(event.target.value)}
                    placeholder={t('twoFactor.reauthPlaceholder')}
                  />
                </label>
                <Button
                  type="button"
                  magnetic={false}
                  disabled={setupMutation.isPending}
                  onClick={() => {
                    if (!reauthPassword.trim()) {
                      setFeedback(t('common.validation.passwordRequired'));
                      return;
                    }
                    setupMutation.mutate(reauthPassword);
                  }}
                >
                  <Key className="mr-2 h-4 w-4" />
                  {t('twoFactor.beginSetupAction')}
                </Button>
              </div>
            </article>
          ) : (
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('twoFactor.validateTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('twoFactor.validateDescription')}
              </p>

              <div className="mt-5 space-y-4">
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.totpCode')}
                  </span>
                  <Input
                    inputMode="numeric"
                    value={validateCode}
                    onChange={(event) => setValidateCode(event.target.value)}
                    placeholder="123456"
                  />
                </label>
                <Button
                  type="button"
                  magnetic={false}
                  disabled={validateMutation.isPending}
                  onClick={() => {
                    if (validateCode.trim().length !== 6) {
                      setFeedback(t('common.validation.codeInvalid'));
                      return;
                    }
                    validateMutation.mutate(validateCode.trim());
                  }}
                >
                  <CheckCircle className="mr-2 h-4 w-4" />
                  {t('common.verify')}
                </Button>
              </div>
            </article>
          )}

          {secret ? (
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('twoFactor.provisioningTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('twoFactor.provisioningDescription')}
              </p>

              <div className="mt-5 grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
                <div className="flex items-center justify-center rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  {qrCodeDataUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={qrCodeDataUrl}
                      alt={t('twoFactor.qrAlt')}
                      className="h-60 w-60 rounded-lg"
                    />
                  ) : (
                    <SecurityEmptyState label={t('common.loading')} />
                  )}
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('twoFactor.secretLabel')}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                      <code className="rounded-lg bg-terminal-bg px-3 py-2 font-mono text-sm text-matrix-green">
                        {secret}
                      </code>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        magnetic={false}
                        onClick={() => {
                          void copySecretToClipboard();
                        }}
                      >
                        <Copy className="mr-2 h-4 w-4" />
                        {copiedSecret ? t('twoFactor.copied') : t('twoFactor.copySecret')}
                      </Button>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('twoFactor.qrUriLabel')}
                    </p>
                    <p className="mt-3 break-all font-mono text-xs leading-6 text-white">
                      {qrUri}
                    </p>
                  </div>

                  <label className="block space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.totpCode')}
                    </span>
                    <Input
                      inputMode="numeric"
                      value={setupCode}
                      onChange={(event) => setSetupCode(event.target.value)}
                      placeholder="123456"
                    />
                  </label>
                  <Button
                    type="button"
                    magnetic={false}
                    disabled={verifyMutation.isPending}
                    onClick={() => {
                      if (setupCode.trim().length !== 6) {
                        setFeedback(t('common.validation.codeInvalid'));
                        return;
                      }
                      verifyMutation.mutate(setupCode.trim());
                    }}
                  >
                    <ShieldCheck className="mr-2 h-4 w-4" />
                    {t('twoFactor.enableAction')}
                  </Button>
                </div>
              </div>
            </article>
          ) : null}
        </section>

        <section className="space-y-6 xl:col-span-5">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('twoFactor.stateTitle')}
            </h2>
            <div className="mt-5 flex items-center gap-3">
              <SecurityStatusChip
                label={isEnabled ? t('common.enabled') : t('common.disabled')}
                tone={isEnabled ? 'success' : 'warning'}
              />
              {statusQuery.isLoading ? (
                <span className="text-sm font-mono text-muted-foreground">
                  {t('common.loading')}
                </span>
              ) : null}
            </div>
          </article>

          {isEnabled ? (
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('twoFactor.disableTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('twoFactor.disableDescription')}
              </p>

              <div className="mt-5 space-y-4">
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.password')}
                  </span>
                  <Input
                    type="password"
                    value={disablePassword}
                    onChange={(event) => setDisablePassword(event.target.value)}
                    placeholder={t('twoFactor.disablePasswordPlaceholder')}
                  />
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.totpCode')}
                  </span>
                  <Input
                    inputMode="numeric"
                    value={disableCode}
                    onChange={(event) => setDisableCode(event.target.value)}
                    placeholder="123456"
                  />
                </label>
                <Button
                  type="button"
                  magnetic={false}
                  disabled={disableMutation.isPending}
                  onClick={() => {
                    if (!disablePassword.trim()) {
                      setFeedback(t('common.validation.passwordRequired'));
                      return;
                    }
                    if (disableCode.trim().length !== 6) {
                      setFeedback(t('common.validation.codeInvalid'));
                      return;
                    }
                    disableMutation.mutate({
                      password: disablePassword.trim(),
                      code: disableCode.trim(),
                    });
                  }}
                >
                  <AlertCircle className="mr-2 h-4 w-4" />
                  {t('twoFactor.disableAction')}
                </Button>
              </div>
            </article>
          ) : null}

          {recoveryCodes.length > 0 ? (
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('twoFactor.recoveryTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('twoFactor.recoveryDescription')}
              </p>

              <div className="mt-5 grid gap-2">
                {recoveryCodes.map((code) => (
                  <code
                    key={code}
                    className="rounded-lg border border-grid-line/20 bg-terminal-bg/45 px-3 py-2 font-mono text-sm text-white"
                  >
                    {code}
                  </code>
                ))}
              </div>
            </article>
          ) : (
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('twoFactor.notesTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('twoFactor.notesDescription')}
              </p>
            </article>
          )}
        </section>
      </div>
    </SecurityPageShell>
  );
}
