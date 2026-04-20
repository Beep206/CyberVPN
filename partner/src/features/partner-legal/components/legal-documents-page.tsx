'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ScrollText, ShieldAlert } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';

const ROLE_KEY_TO_PORTAL_ROLE: Record<string, string> = {
  owner: 'workspace_owner',
  manager: 'workspace_admin',
  finance: 'finance_manager',
  analyst: 'analyst',
  traffic_manager: 'traffic_manager',
  support_manager: 'support_manager',
  technical_manager: 'technical_manager',
};

export function LegalDocumentsPage() {
  const t = useTranslations('Partner.legal');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const { state, activeWorkspace } = usePartnerPortalRuntimeState();

  const legalDocumentsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-legal-documents', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return [];
      }
      const response = await partnerPortalApi.listWorkspaceLegalDocuments(activeWorkspace.id);
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const acceptMutation = useMutation({
    mutationFn: async (documentKind: string) => {
      if (!activeWorkspace) {
        throw new Error('Partner workspace is not available.');
      }
      const response = await partnerPortalApi.acceptWorkspaceLegalDocument(activeWorkspace.id, documentKind);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['partner-portal', 'workspace-legal-documents', activeWorkspace?.id ?? null] });
      await queryClient.invalidateQueries({ queryKey: ['partner-portal', 'workspace-notifications'] });
      await queryClient.invalidateQueries({ queryKey: ['partner-portal', 'session-bootstrap'] });
    },
  });

  return (
    <PartnerRouteGuard route="legal" title={t('title')}>
      {(access) => {
        const documents = legalDocumentsQuery.data ?? [];
        const pendingDocuments = documents.filter((document) => document.status === 'pending_acceptance');
        const canAccept = access === 'admin' || access === 'write';
        const acceptanceRoleLabel = (roleKey: string | null | undefined) => {
          if (!roleKey) {
            return null;
          }
          const portalRole = ROLE_KEY_TO_PORTAL_ROLE[roleKey];
          return portalRole ? portalT(`workspaceRoles.${portalRole}`) : roleKey;
        };

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
                    <span>{t('summary.pending')}</span>
                    <span className="text-foreground">{pendingDocuments.length}</span>
                  </div>
                </div>
              </div>
            </header>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
                <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                  <ScrollText className="h-5 w-5 text-neon-cyan" />
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('documents.title')}
                    </h2>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('documents.description')}
                    </p>
                  </div>
                </div>

                <div className="mt-5 space-y-3">
                  {documents.map((document) => {
                    const notes = document.notes ?? [];

                    return (
                      <article
                        key={document.id}
                        className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                      >
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div>
                            <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                              {document.title}
                            </h3>
                            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                              {t('documents.version', { value: document.version })}
                            </p>
                            {notes.length > 0 ? (
                              <ul className="mt-3 space-y-1 text-xs font-mono text-muted-foreground">
                                {notes.map((note) => (
                                  <li key={note}>{note}</li>
                                ))}
                              </ul>
                            ) : null}
                          </div>
                        <div className="text-right">
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {portalT(`legalDocumentStatuses.${document.status}`)}
                          </p>
                          <p className="mt-2 text-xs font-mono text-muted-foreground">
                            {document.accepted_by_role_key
                              ? t('documents.acceptedBy', {
                                  role: acceptanceRoleLabel(document.accepted_by_role_key) ?? document.accepted_by_role_key,
                                })
                              : t('documents.acceptancePending')}
                          </p>
                          {canAccept && document.status === 'pending_acceptance' ? (
                            <button
                              type="button"
                              onClick={() => void acceptMutation.mutateAsync(document.kind)}
                              disabled={acceptMutation.isPending}
                              className="mt-3 inline-flex items-center justify-center rounded-lg bg-neon-cyan px-3 py-2 text-xs font-mono uppercase tracking-[0.18em] text-black transition-colors hover:bg-neon-cyan/90 disabled:cursor-not-allowed disabled:bg-neon-cyan/50"
                            >
                              {t('documents.acceptAction')}
                            </button>
                          ) : null}
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </article>

              <div className="space-y-6">
                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <ShieldAlert className="h-5 w-5 text-neon-purple" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('ownerActions.title')}
                    </h2>
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {canAccept
                      ? t('ownerActions.allowed')
                      : t('ownerActions.blocked')}
                  </p>
                  <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                    <li>{t('ownerActions.items.contracts')}</li>
                    <li>{t('ownerActions.items.payoutDestination')}</li>
                    <li>{t('ownerActions.items.termination')}</li>
                  </ul>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('links.title')}
                  </h2>
                  <div className="mt-4 flex flex-col gap-3">
                    <Link href="/programs" className="text-sm font-mono text-neon-cyan underline underline-offset-4">
                      {t('links.programs')}
                    </Link>
                    <Link href="/cases" className="text-sm font-mono text-neon-purple underline underline-offset-4">
                      {t('links.cases')}
                    </Link>
                    <Link href="/settings" className="text-sm font-mono text-matrix-green underline underline-offset-4">
                      {t('links.settings')}
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
