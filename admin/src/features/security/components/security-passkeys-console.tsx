'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Fingerprint, Plus, ShieldCheck, Trash2 } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { passkeysApi, type PasskeyCredentialResponse } from '@/lib/api/passkeys';
import { requestPasskeyFreshAuthGrant } from '@/features/auth/lib/passkey-fresh-auth';
import { SecurityEmptyState } from '@/features/security/components/security-empty-state';
import { SecurityPageShell } from '@/features/security/components/security-page-shell';
import { SecurityStatusChip } from '@/features/security/components/security-status-chip';
import { formatDateTime, getErrorMessage } from '@/features/security/lib/formatting';
import { startPasskeyRegistration } from '@/features/auth/lib/passkey-webauthn';

const PASSKEYS_PERSONAL_QUERY_KEY = ['security', 'passkeys', 'personal'] as const;
const PASSKEYS_POLICY_QUERY_KEY = ['security', 'passkeys', 'policy'] as const;
const PASSKEYS_COMPLIANCE_QUERY_KEY = ['security', 'passkeys', 'compliance'] as const;

function getCredentialTone(credential: Pick<PasskeyCredentialResponse, 'revokedAt' | 'status'>) {
  if (credential.revokedAt || credential.status === 'revoked') {
    return 'danger' as const;
  }
  if (credential.status === 'active') {
    return 'success' as const;
  }
  return 'warning' as const;
}

function getCredentialStatusKey(
  credential: Pick<PasskeyCredentialResponse, 'revokedAt' | 'status'>,
) {
  if (credential.revokedAt || credential.status === 'revoked') {
    return 'passkeys.credentialStatus.revoked';
  }
  if (credential.status === 'active') {
    return 'passkeys.credentialStatus.active';
  }
  return 'passkeys.credentialStatus.pending';
}

function normalizeLabel(value: string) {
  return value.trim();
}

function getPasskeyRenameAction(credentialId: string): string {
  return `passkey.credential.rename:${credentialId}`;
}

function getPasskeyRevokeAction(credentialId: string): string {
  return `passkey.credential.revoke:${credentialId}`;
}

export function SecurityPasskeysConsole() {
  const t = useTranslations('AdminSecurity');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [newLabel, setNewLabel] = useState('');
  const [renameDrafts, setRenameDrafts] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<{
    tone: 'success' | 'error';
    message: string;
  } | null>(null);

  const personalQuery = useQuery({
    queryKey: PASSKEYS_PERSONAL_QUERY_KEY,
    queryFn: async () => {
      const response = await passkeysApi.listPasskeys();
      return response.data;
    },
    staleTime: 15_000,
  });

  const policyQuery = useQuery({
    queryKey: PASSKEYS_POLICY_QUERY_KEY,
    queryFn: async () => {
      const response = await passkeysApi.getSecurityPolicy();
      return response.data;
    },
    staleTime: 30_000,
  });

  const complianceQuery = useQuery({
    queryKey: PASSKEYS_COMPLIANCE_QUERY_KEY,
    queryFn: async () => {
      const response = await passkeysApi.getSecurityCompliance();
      return response.data;
    },
    staleTime: 30_000,
  });

  async function refreshPasskeys() {
    await queryClient.invalidateQueries({ queryKey: PASSKEYS_PERSONAL_QUERY_KEY });
    await queryClient.invalidateQueries({ queryKey: PASSKEYS_POLICY_QUERY_KEY });
    await queryClient.invalidateQueries({ queryKey: PASSKEYS_COMPLIANCE_QUERY_KEY });
  }

  const registrationMutation = useMutation({
    mutationFn: async (label: string) => {
      const optionsResponse = await passkeysApi.createRegistrationOptions(label);
      const credential = await startPasskeyRegistration(optionsResponse.data.publicKey);
      const response = await passkeysApi.verifyRegistration({
        challengeId: optionsResponse.data.challengeId,
        credential,
        label,
      });
      return response.data;
    },
    onSuccess: async (credential) => {
      setNewLabel('');
      setFeedback({
        tone: 'success',
        message: t('passkeys.feedback.added', { label: credential.label }),
      });
      await refreshPasskeys();
    },
    onError: (error) => {
      setFeedback({
        tone: 'error',
        message: getErrorMessage(error, t('passkeys.feedback.addFailed')),
      });
    },
  });

  const renameMutation = useMutation({
    mutationFn: async ({ credentialId, label }: { credentialId: string; label: string }) => {
      const freshAuthGrantId = await requestPasskeyFreshAuthGrant(
        getPasskeyRenameAction(credentialId),
      );
      const response = await passkeysApi.renamePasskey(credentialId, label, {
        freshAuthGrantId,
      });
      return response.data;
    },
    onSuccess: async (credential) => {
      setRenameDrafts((current) => {
        const next = { ...current };
        delete next[credential.id];
        return next;
      });
      setFeedback({
        tone: 'success',
        message: t('passkeys.feedback.renamed', { label: credential.label }),
      });
      await refreshPasskeys();
    },
    onError: (error) => {
      setFeedback({
        tone: 'error',
        message: getErrorMessage(error, t('passkeys.feedback.renameFailed')),
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (credentialId: string) => {
      const freshAuthGrantId = await requestPasskeyFreshAuthGrant(
        getPasskeyRevokeAction(credentialId),
      );
      const response = await passkeysApi.deletePasskey(credentialId, {
        freshAuthGrantId,
      });
      return response.data;
    },
    onSuccess: async () => {
      setFeedback({
        tone: 'success',
        message: t('passkeys.feedback.deleted'),
      });
      await refreshPasskeys();
    },
    onError: (error) => {
      setFeedback({
        tone: 'error',
        message: getErrorMessage(error, t('passkeys.feedback.deleteFailed')),
      });
    },
  });

  const personalCredentials = personalQuery.data?.credentials ?? [];
  const activePersonalCredentials = personalCredentials.filter(
    (credential) => !credential.revokedAt && credential.status === 'active',
  );
  const policy = policyQuery.data ?? complianceQuery.data?.policy;
  const complianceSummary = complianceQuery.data?.summary;
  const complianceCredentials = complianceQuery.data?.credentials ?? [];
  const isMutating =
    registrationMutation.isPending || renameMutation.isPending || deleteMutation.isPending;

  return (
    <SecurityPageShell
      eyebrow={t('passkeys.eyebrow')}
      title={t('passkeys.title')}
      description={t('passkeys.description')}
      icon={Fingerprint}
      metrics={[
        {
          label: t('passkeys.metrics.policy'),
          value: policy?.enabled ? t('common.enabled') : t('common.disabled'),
          hint: policy?.realm_key ? t('passkeys.metrics.realm', { value: policy.realm_key }) : t('passkeys.metrics.policyHint'),
          tone: policy?.enabled ? 'success' : 'warning',
        },
        {
          label: t('passkeys.metrics.personalActive'),
          value: String(activePersonalCredentials.length),
          hint: t('passkeys.metrics.personalActiveHint'),
          tone: activePersonalCredentials.length > 0 ? 'success' : 'warning',
        },
        {
          label: t('passkeys.metrics.adminsCovered'),
          value: String(complianceSummary?.principalsWithActivePasskeys ?? 0),
          hint: t('passkeys.metrics.adminsCoveredHint'),
          tone: 'info',
        },
        {
          label: t('passkeys.metrics.cloneSuspected'),
          value: String(complianceSummary?.cloneSuspectedCredentials ?? 0),
          hint: t('passkeys.metrics.cloneSuspectedHint'),
          tone: (complianceSummary?.cloneSuspectedCredentials ?? 0) > 0 ? 'danger' : 'success',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="space-y-6 xl:col-span-5">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('passkeys.personalTitle')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('passkeys.personalDescription')}
                </p>
              </div>
              <SecurityStatusChip
                label={policy?.registrationEnabled ? t('passkeys.status.registrationOpen') : t('passkeys.status.registrationClosed')}
                tone={policy?.registrationEnabled ? 'success' : 'warning'}
              />
            </div>

            {feedback ? (
              <div
                role={feedback.tone === 'error' ? 'alert' : 'status'}
                className={`mt-5 rounded-xl border px-4 py-3 text-sm font-mono ${
                  feedback.tone === 'success'
                    ? 'border-matrix-green/25 bg-matrix-green/10 text-matrix-green'
                    : 'border-neon-pink/25 bg-neon-pink/10 text-neon-pink'
                }`}
              >
                {feedback.message}
              </div>
            ) : null}

            <div className="mt-5 space-y-3">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('passkeys.addLabel')}
                </span>
                <Input
                  value={newLabel}
                  onChange={(event) => setNewLabel(event.target.value)}
                  placeholder={t('passkeys.addPlaceholder')}
                  disabled={isMutating || !policy?.registrationEnabled}
                />
              </label>
              <Button
                type="button"
                magnetic={false}
                disabled={isMutating || !policy?.registrationEnabled}
                onClick={() => registrationMutation.mutate(normalizeLabel(newLabel) || t('passkeys.defaultLabel'))}
                className="bg-neon-cyan text-black hover:bg-neon-cyan/90 font-mono text-xs uppercase tracking-[0.18em]"
                aria-label={t('passkeys.addAction')}
              >
                <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                {registrationMutation.isPending ? t('passkeys.addingAction') : t('passkeys.addAction')}
              </Button>
            </div>

            <div className="mt-6 space-y-3">
              {personalQuery.isLoading ? (
                <SecurityEmptyState label={t('common.loading')} />
              ) : personalCredentials.length === 0 ? (
                <SecurityEmptyState label={t('passkeys.emptyPersonal')} />
              ) : (
                personalCredentials.map((credential) => {
                  const draftLabel = renameDrafts[credential.id] ?? credential.label;
                  const canRename = normalizeLabel(draftLabel).length > 0
                    && normalizeLabel(draftLabel) !== credential.label;

                  return (
                    <article
                      key={credential.id}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                    >
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {credential.label}
                            </h3>
                            <SecurityStatusChip
                              label={t(getCredentialStatusKey(credential))}
                              tone={getCredentialTone(credential)}
                            />
                          </div>
                          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                            {t('passkeys.createdAt', { value: formatDateTime(credential.createdAt, locale) })}
                          </p>
                          <p className="mt-1 text-xs font-mono leading-5 text-muted-foreground">
                            {t('passkeys.lastUsedAt', {
                              value: credential.lastUsedAt
                                ? formatDateTime(credential.lastUsedAt, locale)
                                : t('passkeys.neverUsed'),
                            })}
                          </p>
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          magnetic={false}
                          disabled={isMutating}
                          onClick={() => {
                            if (window.confirm(t('passkeys.deleteConfirm', { label: credential.label }))) {
                              deleteMutation.mutate(credential.id);
                            }
                          }}
                          className="border-neon-pink/30 bg-neon-pink/10 text-neon-pink hover:bg-neon-pink/15"
                          aria-label={t('passkeys.deleteAria', { label: credential.label })}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </div>
                      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                        <Input
                          value={draftLabel}
                          onChange={(event) => setRenameDrafts((current) => ({
                            ...current,
                            [credential.id]: event.target.value,
                          }))}
                          disabled={isMutating}
                          aria-label={t('passkeys.renameInputAria', { label: credential.label })}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          magnetic={false}
                          disabled={isMutating || !canRename}
                          onClick={() => renameMutation.mutate({
                            credentialId: credential.id,
                            label: normalizeLabel(draftLabel),
                          })}
                          className="border-grid-line/30 bg-terminal-surface/35 font-mono text-xs uppercase tracking-[0.18em]"
                          aria-label={t('passkeys.renameAria', { label: credential.label })}
                        >
                          {t('passkeys.renameAction')}
                        </Button>
                      </div>
                    </article>
                  );
                })
              )}
            </div>
          </article>
        </section>

        <section className="space-y-6 xl:col-span-7">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 text-neon-cyan" aria-hidden="true" />
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('passkeys.complianceTitle')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('passkeys.complianceDescription')}
                </p>
              </div>
            </div>

            <div className="mt-5 overflow-x-auto">
              <table className="min-w-full text-left text-sm font-mono">
                <caption className="sr-only">{t('passkeys.complianceCaption')}</caption>
                <thead className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  <tr className="border-b border-grid-line/20">
                    <th scope="col" className="py-3 pr-4">{t('passkeys.table.principal')}</th>
                    <th scope="col" className="py-3 pr-4">{t('passkeys.table.status')}</th>
                    <th scope="col" className="py-3 pr-4">{t('passkeys.table.hashPrefix')}</th>
                    <th scope="col" className="py-3 pr-4">{t('passkeys.table.lastUsed')}</th>
                  </tr>
                </thead>
                <tbody>
                  {complianceQuery.isLoading ? (
                    <tr>
                      <td colSpan={4} className="py-6">
                        <SecurityEmptyState label={t('common.loading')} />
                      </td>
                    </tr>
                  ) : complianceCredentials.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-6">
                        <SecurityEmptyState label={t('passkeys.emptyCompliance')} />
                      </td>
                    </tr>
                  ) : (
                    complianceCredentials.map((credential) => (
                      <tr key={credential.id} className="border-b border-grid-line/10">
                        <td className="py-3 pr-4 text-foreground">
                          <div className="max-w-[240px] truncate">{credential.principalSubject}</div>
                          <div className="text-xs text-muted-foreground">{credential.principalClass}</div>
                        </td>
                        <td className="py-3 pr-4">
                          <SecurityStatusChip
                            label={t(getCredentialStatusKey(credential))}
                            tone={getCredentialTone(credential)}
                          />
                        </td>
                        <td className="py-3 pr-4 text-muted-foreground">
                          {credential.credentialIdHashPrefix}
                        </td>
                        <td className="py-3 pr-4 text-muted-foreground">
                          {credential.lastUsedAt
                            ? formatDateTime(credential.lastUsedAt, locale)
                            : t('passkeys.neverUsed')}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </article>
        </section>
      </div>
    </SecurityPageShell>
  );
}
