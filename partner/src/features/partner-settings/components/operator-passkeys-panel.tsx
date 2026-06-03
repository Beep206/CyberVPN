'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Fingerprint, Plus, Trash2 } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { passkeysApi, type PasskeyCredentialResponse } from '@/lib/api/passkeys';
import { requestPasskeyFreshAuthGrant } from '@/features/auth/lib/passkey-fresh-auth';
import { SecurityEmptyState } from '@/features/security/components/security-empty-state';
import { SecurityStatusChip } from '@/features/security/components/security-status-chip';
import { formatDateTime, getErrorMessage } from '@/features/security/lib/formatting';
import { startPasskeyRegistration } from '@/features/auth/lib/passkey-webauthn';

const PARTNER_PASSKEYS_PERSONAL_QUERY_KEY = ['partner', 'passkeys', 'personal'] as const;
const PARTNER_PASSKEYS_POLICY_QUERY_KEY = ['partner', 'passkeys', 'policy'] as const;

function getWorkspacePolicyQueryKey(workspaceId: string | null) {
  return ['partner', 'passkeys', 'workspace-policy', workspaceId] as const;
}

function getWorkspaceComplianceQueryKey(workspaceId: string | null) {
  return ['partner', 'passkeys', 'workspace-compliance', workspaceId] as const;
}

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

interface OperatorPasskeysPanelProps {
  activeWorkspaceId: string | null;
  isReadOnly: boolean;
}

export function OperatorPasskeysPanel({
  activeWorkspaceId,
  isReadOnly,
}: OperatorPasskeysPanelProps) {
  const t = useTranslations('Partner.settings');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [newLabel, setNewLabel] = useState('');
  const [renameDrafts, setRenameDrafts] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<{
    tone: 'success' | 'error';
    message: string;
  } | null>(null);

  const personalQuery = useQuery({
    queryKey: PARTNER_PASSKEYS_PERSONAL_QUERY_KEY,
    queryFn: async () => {
      const response = await passkeysApi.listPasskeys();
      return response.data;
    },
    staleTime: 15_000,
  });

  const policyQuery = useQuery({
    queryKey: PARTNER_PASSKEYS_POLICY_QUERY_KEY,
    queryFn: async () => {
      const response = await passkeysApi.getAuthPolicy();
      return response.data;
    },
    staleTime: 30_000,
  });

  const workspacePolicyQuery = useQuery({
    queryKey: getWorkspacePolicyQueryKey(activeWorkspaceId),
    queryFn: async () => {
      if (!activeWorkspaceId) {
        return null;
      }
      const response = await passkeysApi.getWorkspacePolicy(activeWorkspaceId);
      return response.data;
    },
    enabled: Boolean(activeWorkspaceId),
    staleTime: 30_000,
  });

  const workspaceComplianceQuery = useQuery({
    queryKey: getWorkspaceComplianceQueryKey(activeWorkspaceId),
    queryFn: async () => {
      if (!activeWorkspaceId) {
        return null;
      }
      const response = await passkeysApi.getWorkspaceCompliance(activeWorkspaceId);
      return response.data;
    },
    enabled: Boolean(activeWorkspaceId),
    staleTime: 30_000,
  });

  async function refreshPasskeys() {
    await queryClient.invalidateQueries({ queryKey: PARTNER_PASSKEYS_PERSONAL_QUERY_KEY });
    await queryClient.invalidateQueries({ queryKey: PARTNER_PASSKEYS_POLICY_QUERY_KEY });
    await queryClient.invalidateQueries({ queryKey: getWorkspacePolicyQueryKey(activeWorkspaceId) });
    await queryClient.invalidateQueries({ queryKey: getWorkspaceComplianceQueryKey(activeWorkspaceId) });
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

  const policy = policyQuery.data ?? workspacePolicyQuery.data?.policy;
  const personalCredentials = personalQuery.data?.credentials ?? [];
  const activePersonalCredentials = personalCredentials.filter(
    (credential) => !credential.revokedAt && credential.status === 'active',
  );
  const operatorCompliance = workspacePolicyQuery.data?.operatorCompliance
    ?? workspaceComplianceQuery.data?.operatorCompliance;
  const complianceCredentials = workspaceComplianceQuery.data?.credentials ?? [];
  const isMutating =
    registrationMutation.isPending || renameMutation.isPending || deleteMutation.isPending;
  const canRegister = !isReadOnly && Boolean(policy?.registrationEnabled);

  return (
    <section className="space-y-5 rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-matrix-green/30 bg-matrix-green/10 text-matrix-green">
            <Fingerprint className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
              {t('passkeys.title')}
            </h3>
            <p className="mt-1 text-xs font-mono leading-5 text-muted-foreground">
              {t('passkeys.description')}
            </p>
          </div>
        </div>
        <div className="grid gap-2 text-xs font-mono text-muted-foreground sm:grid-cols-3 lg:w-[420px]">
          <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-3">
            <span className="block uppercase tracking-[0.16em]">{t('passkeys.metrics.policy')}</span>
            <span className={policy?.enabled ? 'mt-2 block text-matrix-green' : 'mt-2 block text-amber-300'}>
              {policy?.enabled ? t('passkeys.values.enabled') : t('passkeys.values.disabled')}
            </span>
          </div>
          <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-3">
            <span className="block uppercase tracking-[0.16em]">{t('passkeys.metrics.personal')}</span>
            <span className="mt-2 block text-neon-cyan">{activePersonalCredentials.length}</span>
          </div>
          <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-3">
            <span className="block uppercase tracking-[0.16em]">{t('passkeys.metrics.missing')}</span>
            <span className="mt-2 block text-neon-pink">
              {operatorCompliance?.operatorsMissingActivePasskeys ?? 0}
            </span>
          </div>
        </div>
      </div>

      {feedback ? (
        <div
          role={feedback.tone === 'error' ? 'alert' : 'status'}
          className={`rounded-xl border px-4 py-3 text-sm font-mono ${
            feedback.tone === 'success'
              ? 'border-matrix-green/25 bg-matrix-green/10 text-matrix-green'
              : 'border-neon-pink/25 bg-neon-pink/10 text-neon-pink'
          }`}
        >
          {feedback.message}
        </div>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
        <label className="space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('passkeys.addLabel')}
          </span>
          <Input
            value={newLabel}
            onChange={(event) => setNewLabel(event.target.value)}
            placeholder={t('passkeys.addPlaceholder')}
            disabled={!canRegister || isMutating}
          />
        </label>
        <div className="flex items-end">
          <Button
            type="button"
            onClick={() => registrationMutation.mutate(normalizeLabel(newLabel) || t('passkeys.defaultLabel'))}
            disabled={!canRegister || isMutating}
            className="bg-neon-cyan text-black hover:bg-neon-cyan/90 font-mono text-xs uppercase tracking-[0.18em]"
            aria-label={t('passkeys.addAction')}
          >
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            {registrationMutation.isPending ? t('passkeys.addingAction') : t('passkeys.addAction')}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div className="space-y-3">
          <h4 className="text-xs font-display uppercase tracking-[0.16em] text-white">
            {t('passkeys.personalTitle')}
          </h4>
          {personalQuery.isLoading ? (
            <SecurityEmptyState label={t('passkeys.loading')} />
          ) : personalCredentials.length === 0 ? (
            <SecurityEmptyState label={t('passkeys.emptyPersonal')} />
          ) : (
            personalCredentials.map((credential) => {
              const draftLabel = renameDrafts[credential.id] ?? credential.label;
              const canRename =
                normalizeLabel(draftLabel).length > 0
                && normalizeLabel(draftLabel) !== credential.label
                && !isReadOnly;

              return (
                <article
                  key={credential.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
                          {credential.label}
                        </p>
                        <SecurityStatusChip
                          label={t(getCredentialStatusKey(credential))}
                          tone={getCredentialTone(credential)}
                        />
                      </div>
                      <p className="mt-2 text-xs font-mono text-muted-foreground">
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
                      disabled={isReadOnly || isMutating}
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
                  <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                    <Input
                      value={draftLabel}
                      disabled={isReadOnly || isMutating}
                      onChange={(event) => setRenameDrafts((current) => ({
                        ...current,
                        [credential.id]: event.target.value,
                      }))}
                      aria-label={t('passkeys.renameInputAria', { label: credential.label })}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      disabled={!canRename || isMutating}
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

        <div className="space-y-3">
          <h4 className="text-xs font-display uppercase tracking-[0.16em] text-white">
            {t('passkeys.complianceTitle')}
          </h4>
          <div className="overflow-x-auto rounded-2xl border border-grid-line/20 bg-terminal-bg/55">
            <table className="min-w-full text-left text-xs font-mono">
              <caption className="sr-only">{t('passkeys.complianceCaption')}</caption>
              <thead className="uppercase tracking-[0.16em] text-muted-foreground">
                <tr className="border-b border-grid-line/20">
                  <th scope="col" className="px-3 py-3">{t('passkeys.table.member')}</th>
                  <th scope="col" className="px-3 py-3">{t('passkeys.table.status')}</th>
                  <th scope="col" className="px-3 py-3">{t('passkeys.table.lastUsed')}</th>
                </tr>
              </thead>
              <tbody>
                {workspaceComplianceQuery.isLoading ? (
                  <tr>
                    <td colSpan={3} className="p-4">
                      <SecurityEmptyState label={t('passkeys.loading')} />
                    </td>
                  </tr>
                ) : complianceCredentials.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="p-4">
                      <SecurityEmptyState label={t('passkeys.emptyCompliance')} />
                    </td>
                  </tr>
                ) : (
                  complianceCredentials.map((credential) => (
                    <tr key={credential.id} className="border-b border-grid-line/10">
                      <td className="px-3 py-3 text-foreground">
                        <div className="max-w-[180px] truncate">{credential.principalSubject}</div>
                        <div className="text-muted-foreground">{credential.principalClass}</div>
                      </td>
                      <td className="px-3 py-3">
                        <SecurityStatusChip
                          label={t(getCredentialStatusKey(credential))}
                          tone={getCredentialTone(credential)}
                        />
                      </td>
                      <td className="px-3 py-3 text-muted-foreground">
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
        </div>
      </div>
    </section>
  );
}
