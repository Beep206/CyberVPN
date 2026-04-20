'use client';

import { useTranslations } from 'next-intl';
import { usePartnerWorkspaceSelection } from '@/features/partner-portal-state/lib/use-partner-workspace-selection';

interface PartnerWorkspaceSwitcherProps {
  compact?: boolean;
}

export function PartnerWorkspaceSwitcher({
  compact = false,
}: PartnerWorkspaceSwitcherProps) {
  const t = useTranslations('workspaceSwitcher');
  const portalStateT = useTranslations('portalState');
  const {
    workspaces,
    activeWorkspace,
    isSwitching,
    selectWorkspace,
    workspacesQuery,
  } = usePartnerWorkspaceSelection();

  if (workspaces.length <= 1 && !workspacesQuery.isLoading) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-neon-cyan/80">
            {t('label')}
          </div>
          {!compact ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {t('description')}
            </p>
          ) : null}
        </div>
        <span className="rounded-full border border-neon-cyan/25 bg-neon-cyan/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-neon-cyan">
          {t('canonicalSource')}
        </span>
      </div>

      <label className="mt-3 block">
        <span className="sr-only">{t('inputLabel')}</span>
        <select
          aria-label={t('inputLabel')}
          className="w-full rounded-xl border border-grid-line/25 bg-terminal-surface/80 px-3 py-2 font-mono text-sm text-foreground outline-hidden transition-colors focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/40"
          disabled={workspacesQuery.isLoading || isSwitching || workspaces.length === 0}
          value={activeWorkspace?.id ?? ''}
          onChange={(event) => selectWorkspace(event.target.value)}
        >
          {workspaces.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>
              {workspace.display_name}
            </option>
          ))}
        </select>
      </label>

      {activeWorkspace ? (
        <div className="mt-3 flex items-center justify-between gap-3 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          <span className="truncate">{activeWorkspace.account_key}</span>
          <span className="shrink-0 text-matrix-green">
            {portalStateT(`workspaceStatuses.${activeWorkspace.status}`)}
          </span>
        </div>
      ) : null}

      {!compact ? (
        <p className="mt-2 text-[11px] text-muted-foreground">
          {t('sessionNote')}
        </p>
      ) : null}
    </div>
  );
}
