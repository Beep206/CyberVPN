'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, KeyRound, RefreshCw, Trash2, UserPlus } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { governanceApi } from '@/lib/api/governance';
import { GovernanceEmptyState } from '@/features/governance/components/governance-empty-state';
import { GovernancePageShell } from '@/features/governance/components/governance-page-shell';
import { GovernanceStatusChip } from '@/features/governance/components/governance-status-chip';
import {
  formatDateTime,
  formatTtl,
  getErrorMessage,
  matchesSearch,
  shortId,
  toneForInviteRole,
} from '@/features/governance/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';
import { AdminActionDialog } from '@/shared/ui/admin-action-dialog';

const ROLE_OPTIONS = [
  'viewer',
  'support',
  'operator',
  'admin',
  'super_admin',
] as const;

export function AdminInvitesConsole() {
  const t = useTranslations('Governance');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [role, setRole] = useState<(typeof ROLE_OPTIONS)[number]>('viewer');
  const [emailHint, setEmailHint] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [selectedToken, setSelectedToken] = useState<string | null>(null);
  const [inviteToRevoke, setInviteToRevoke] = useState<string | null>(null);

  const invitesQuery = useQuery({
    queryKey: ['governance', 'admin-invites'],
    queryFn: async () => {
      const response = await governanceApi.listAdminInvites();
      return response.data;
    },
    staleTime: 15_000,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      governanceApi.createAdminInvite({
        role,
        email_hint: emailHint.trim() || null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['governance', 'admin-invites'] });
      setEmailHint('');
      setRole('viewer');
      setFeedback(t('adminInvites.createSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (token: string) => governanceApi.revokeAdminInvite(token),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['governance', 'admin-invites'] });
      setFeedback(t('adminInvites.revokeSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const invites = invitesQuery.data?.invites ?? [];
  const filteredInvites = invites.filter((invite) =>
    matchesSearch(
      [
        invite.token,
        invite.role,
        invite.email_hint,
        invite.created_by,
        invite.created_at,
      ],
      search,
    ),
  );
  const selectedInvite =
    filteredInvites.find((invite) => invite.token === selectedToken) ??
    filteredInvites[0] ??
    null;
  const restrictedCount = invites.filter((invite) => invite.email_hint).length;
  const expiringSoonCount = invites.filter((invite) => invite.ttl_seconds < 7_200).length;
  const privilegedCount = invites.filter(
    (invite) => invite.role === 'admin' || invite.role === 'super_admin',
  ).length;

  async function copyToken(token: string) {
    try {
      await navigator.clipboard.writeText(token);
      setFeedback(t('common.copied'));
    } catch {
      setFeedback(t('adminInvites.copyFailed'));
    }
  }

  return (
    <GovernancePageShell
      eyebrow={t('adminInvites.eyebrow')}
      title={t('adminInvites.title')}
      description={t('adminInvites.description')}
      icon={UserPlus}
      actions={
        <>
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('adminInvites.searchPlaceholder')}
            className="w-[15rem]"
          />
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            onClick={() => {
              void queryClient.invalidateQueries({ queryKey: ['governance', 'admin-invites'] });
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('common.refresh')}
          </Button>
        </>
      }
      metrics={[
        {
          label: t('adminInvites.metrics.active'),
          value: String(invites.length),
          hint: t('adminInvites.metrics.activeHint'),
          tone: invites.length > 0 ? 'warning' : 'neutral',
        },
        {
          label: t('adminInvites.metrics.restricted'),
          value: String(restrictedCount),
          hint: t('adminInvites.metrics.restrictedHint'),
          tone: 'info',
        },
        {
          label: t('adminInvites.metrics.expiringSoon'),
          value: String(expiringSoonCount),
          hint: t('adminInvites.metrics.expiringSoonHint'),
          tone: expiringSoonCount > 0 ? 'warning' : 'success',
        },
        {
          label: t('adminInvites.metrics.privileged'),
          value: String(privilegedCount),
          hint: t('adminInvites.metrics.privilegedHint'),
          tone: privilegedCount > 0 ? 'danger' : 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
          {feedback ? (
            <div className="mb-5 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}

          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('adminInvites.inventoryTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('adminInvites.inventoryDescription')}
          </p>

          <div className="mt-5">
            {invitesQuery.isLoading ? (
              <div className="grid gap-3">
                {Array.from({ length: 5 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                  />
                ))}
              </div>
            ) : filteredInvites.length === 0 ? (
              <GovernanceEmptyState label={t('adminInvites.empty')} />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('common.token')}</TableHead>
                    <TableHead>{t('common.role')}</TableHead>
                    <TableHead>{t('common.emailHint')}</TableHead>
                    <TableHead>{t('common.ttl')}</TableHead>
                    <TableHead>{t('common.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredInvites.map((invite) => {
                    const isSelected = selectedInvite?.token === invite.token;

                    return (
                      <TableRow
                        key={invite.token}
                        className={isSelected ? 'border-l-2 border-l-neon-cyan bg-neon-cyan/5' : undefined}
                        onClick={() => setSelectedToken(invite.token)}
                      >
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-display uppercase tracking-[0.14em] text-white">
                              #{shortId(invite.token)}
                            </p>
                            <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                              {formatDateTime(invite.created_at, locale)}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <GovernanceStatusChip
                            label={invite.role}
                            tone={toneForInviteRole(invite.role)}
                          />
                        </TableCell>
                        <TableCell>{invite.email_hint ?? t('common.none')}</TableCell>
                        <TableCell>{formatTtl(invite.ttl_seconds)}</TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              magnetic={false}
                              onClick={(event) => {
                                event.stopPropagation();
                                void copyToken(invite.token);
                              }}
                            >
                              <Copy className="mr-2 h-4 w-4" />
                              {t('common.copy')}
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              magnetic={false}
                              disabled={revokeMutation.isPending}
                              onClick={(event) => {
                                event.stopPropagation();
                                setInviteToRevoke(invite.token);
                              }}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              {t('common.revoke')}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </div>
        </section>

        <section className="space-y-6 xl:col-span-4">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('adminInvites.createTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('adminInvites.createDescription')}
            </p>

            <div className="mt-5 space-y-4">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.role')}
                </span>
                <select
                  value={role}
                  onChange={(event) => setRole(event.target.value as (typeof ROLE_OPTIONS)[number])}
                  className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                >
                  {ROLE_OPTIONS.map((roleOption) => (
                    <option key={roleOption} value={roleOption}>
                      {roleOption}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.emailHint')}
                </span>
                <Input
                  value={emailHint}
                  onChange={(event) => setEmailHint(event.target.value)}
                  placeholder={t('adminInvites.emailHintPlaceholder')}
                />
              </label>

              <Button
                type="button"
                magnetic={false}
                disabled={createMutation.isPending}
                onClick={() => {
                  createMutation.mutate();
                }}
              >
                <KeyRound className="mr-2 h-4 w-4" />
                {t('common.create')}
              </Button>
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('adminInvites.detailTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('adminInvites.detailDescription')}
            </p>

            {selectedInvite ? (
              <div className="mt-5 space-y-3">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.token')}
                  </p>
                  <p className="mt-3 break-all text-sm font-mono leading-6 text-white">
                    {selectedInvite.token}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.createdBy')}
                  </p>
                  <p className="mt-3 break-all text-sm font-mono leading-6 text-white">
                    {selectedInvite.created_by}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.createdAt')}
                  </p>
                  <p className="mt-3 text-sm font-mono leading-6 text-white">
                    {formatDateTime(selectedInvite.created_at, locale)}
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-5">
                <GovernanceEmptyState label={t('adminInvites.empty')} />
              </div>
            )}
          </article>
        </section>
      </div>

      <AdminActionDialog
        isOpen={Boolean(inviteToRevoke)}
        isPending={revokeMutation.isPending}
        title={t('adminInvites.revokeTitle')}
        description={t('adminInvites.revokeConfirm')}
        confirmLabel={t('common.revoke')}
        cancelLabel={t('common.cancel')}
        subjectLabel={t('common.token')}
        subject={inviteToRevoke}
        onClose={() => setInviteToRevoke(null)}
        onConfirm={async () => {
          if (!inviteToRevoke) {
            return;
          }
          await revokeMutation.mutateAsync(inviteToRevoke);
          setInviteToRevoke(null);
        }}
      />
    </GovernancePageShell>
  );
}
