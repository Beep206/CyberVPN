'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ShieldCheck, UserPlus, Users } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';

const FIELD_CLASS_NAME = 'w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20';

const LAUNCH_ROLE_KEYS = ['owner', 'finance', 'analyst', 'traffic_manager', 'support_manager'];
const DEFERRED_ROLE_KEYS = ['manager', 'technical_manager'];

export function TeamAccessPage() {
  const t = useTranslations('Partner.team');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const { state, activeWorkspace } = usePartnerPortalRuntimeState();

  const [operatorLookup, setOperatorLookup] = useState('');
  const [selectedRoleKey, setSelectedRoleKey] = useState('owner');
  const [feedback, setFeedback] = useState<'idle' | 'saved' | 'error'>('idle');

  const membersQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-members', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return [];
      }
      const response = await partnerPortalApi.listWorkspaceMembers(activeWorkspace.id);
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const rolesQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-roles', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return [];
      }
      const response = await partnerPortalApi.listWorkspaceRoles(activeWorkspace.id);
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const roleLabelByKey = useMemo(
    () => new Map((rolesQuery.data ?? []).map((role) => [role.role_key, role.display_name])),
    [rolesQuery.data],
  );

  const launchRoles = (rolesQuery.data ?? []).filter((role) => LAUNCH_ROLE_KEYS.includes(role.role_key));
  const deferredRoles = (rolesQuery.data ?? []).filter((role) => DEFERRED_ROLE_KEYS.includes(role.role_key));

  const createMemberMutation = useMutation({
    mutationFn: async () => {
      if (!activeWorkspace) {
        throw new Error('Partner workspace is not available.');
      }
      const response = await partnerPortalApi.createWorkspaceMember(activeWorkspace.id, {
        operator_lookup: operatorLookup,
        role_key: selectedRoleKey,
      });
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['partner-portal', 'workspace-members', activeWorkspace?.id ?? null] }),
        queryClient.invalidateQueries({ queryKey: ['partner-portal', 'session-bootstrap'] }),
      ]);
      setOperatorLookup('');
      setFeedback('saved');
    },
    onError: () => {
      setFeedback('error');
    },
  });

  const updateMemberMutation = useMutation({
    mutationFn: async ({
      memberId,
      membershipStatus,
      roleKey,
    }: {
      memberId: string;
      membershipStatus?: string;
      roleKey?: string;
    }) => {
      if (!activeWorkspace) {
        throw new Error('Partner workspace is not available.');
      }
      const response = await partnerPortalApi.updateWorkspaceMember(activeWorkspace.id, memberId, {
        membership_status: membershipStatus,
        role_key: roleKey,
      });
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['partner-portal', 'workspace-members', activeWorkspace?.id ?? null] }),
        queryClient.invalidateQueries({ queryKey: ['partner-portal', 'session-bootstrap'] }),
      ]);
      setFeedback('saved');
    },
    onError: () => {
      setFeedback('error');
    },
  });

  return (
    <PartnerRouteGuard route="team" title={t('title')}>
      {(access) => {
        const canManage = access === 'admin' || access === 'write';
        const members = membersQuery.data ?? [];

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

                <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[320px]">
                  <div className="flex items-center justify-between gap-3">
                    <span>{t('summary.currentRole')}</span>
                    <span className="text-foreground">
                      {portalT(`workspaceRoles.${state.workspaceRole}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.routeAccess')}</span>
                    <span className="text-neon-cyan">
                      {portalT(`routeAccess.${access}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.memberCount')}</span>
                    <span className="text-foreground">{members.length}</span>
                  </div>
                </div>
              </div>
            </header>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
                <div className="flex items-center justify-between gap-3 border-b border-grid-line/20 pb-4">
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('members.title')}
                    </h2>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('members.description')}
                    </p>
                  </div>
                  <span className="inline-flex rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                    {portalT(`routeAccess.${access}`)}
                  </span>
                </div>

                {canManage ? (
                  <div className="mt-5 grid gap-3 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 md:grid-cols-[minmax(0,1fr)_220px_auto]">
                    <input
                      className={FIELD_CLASS_NAME}
                      value={operatorLookup}
                      onChange={(event) => {
                        setOperatorLookup(event.target.value);
                        setFeedback('idle');
                      }}
                      placeholder={t('editor.lookupPlaceholder')}
                    />
                    <select
                      className={FIELD_CLASS_NAME}
                      value={selectedRoleKey}
                      onChange={(event) => setSelectedRoleKey(event.target.value)}
                    >
                      {(rolesQuery.data ?? []).map((role) => (
                        <option key={role.id} value={role.role_key}>
                          {role.display_name}
                        </option>
                      ))}
                    </select>
                    <Button
                      type="button"
                      onClick={() => void createMemberMutation.mutateAsync()}
                      disabled={createMemberMutation.isPending || operatorLookup.trim().length === 0}
                      className="bg-neon-cyan text-black hover:bg-neon-cyan/90 font-mono text-xs uppercase tracking-[0.18em]"
                    >
                      <UserPlus className="mr-2 h-4 w-4" aria-hidden="true" />
                      {t('editor.addMember')}
                    </Button>
                  </div>
                ) : null}

                <div className="mt-5 space-y-3">
                  {members.length === 0 ? (
                    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground">
                      {t('members.empty')}
                    </article>
                  ) : null}
                  {members.map((member) => (
                    <article
                      key={member.id}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                    >
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                            {member.operator_display_name || member.operator_login || member.role_display_name}
                          </h3>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {member.operator_email || member.operator_login || member.admin_user_id}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {roleLabelByKey.get(member.role_key) || member.role_display_name}
                          </p>
                          <p className="mt-2 text-xs font-mono text-muted-foreground">
                            {t(`memberStatuses.${member.membership_status === 'limited' ? 'limited' : member.membership_status === 'active' ? 'active' : 'invited'}`)}
                          </p>
                        </div>
                      </div>

                      {canManage ? (
                        <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_180px]">
                          <select
                            className={FIELD_CLASS_NAME}
                            value={member.role_key}
                            onChange={(event) => void updateMemberMutation.mutateAsync({
                              memberId: member.id,
                              roleKey: event.target.value,
                            })}
                          >
                            {(rolesQuery.data ?? []).map((role) => (
                              <option key={role.id} value={role.role_key}>
                                {role.display_name}
                              </option>
                            ))}
                          </select>
                          <select
                            className={FIELD_CLASS_NAME}
                            value={member.membership_status}
                            onChange={(event) => void updateMemberMutation.mutateAsync({
                              memberId: member.id,
                              membershipStatus: event.target.value,
                            })}
                          >
                            <option value="active">{t('memberStatuses.active')}</option>
                            <option value="invited">{t('memberStatuses.invited')}</option>
                            <option value="limited">{t('memberStatuses.limited')}</option>
                          </select>
                          <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-xs font-mono text-muted-foreground">
                            {member.permission_keys.length} permissions
                          </div>
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              </article>

              <div className="space-y-6">
                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <Users className="h-5 w-5 text-neon-cyan" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('launchSet.title')}
                    </h2>
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t('launchSet.description')}
                  </p>
                  <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                    {launchRoles.map((role) => (
                      <li key={role.id}>{role.display_name}</li>
                    ))}
                  </ul>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-neon-purple" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('deferredRoles.title')}
                    </h2>
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t('deferredRoles.description')}
                  </p>
                  <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                    {deferredRoles.map((role) => (
                      <li key={role.id}>{role.display_name}</li>
                    ))}
                  </ul>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <UserPlus className="h-5 w-5 text-matrix-green" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('actions.title')}
                    </h2>
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {canManage ? t('actions.manageAllowed') : t('actions.manageBlocked')}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Link href="/settings" className="text-sm font-mono text-neon-cyan underline underline-offset-4">
                      {t('actions.settings')}
                    </Link>
                    <Link href="/organization" className="text-sm font-mono text-neon-purple underline underline-offset-4">
                      {t('actions.organization')}
                    </Link>
                  </div>
                  {feedback !== 'idle' ? (
                    <p className="mt-4 text-xs font-mono text-muted-foreground">
                      {feedback === 'saved' ? t('editor.saved') : t('editor.error')}
                    </p>
                  ) : null}
                </article>
              </div>
            </div>
          </section>
        );
      }}
    </PartnerRouteGuard>
  );
}
