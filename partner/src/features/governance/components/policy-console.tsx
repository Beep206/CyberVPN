'use client';

import { Settings2, ShieldCheck } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { GovernanceEmptyState } from '@/features/governance/components/governance-empty-state';
import { GovernancePageShell } from '@/features/governance/components/governance-page-shell';
import { GovernanceStatusChip } from '@/features/governance/components/governance-status-chip';
import {
  GOVERNANCE_ROLE_PERMISSION_MATRIX,
  humanizeToken,
} from '@/features/governance/lib/formatting';

/**
 * The legacy governance route intentionally does not request Remnawave global
 * settings. Those settings can contain provider credentials and are outside a
 * partner workspace's authority. Workspace settings remain available through
 * the workspace-scoped partner contract.
 */
export function PolicyConsole() {
  const t = useTranslations('Governance');

  return (
    <GovernancePageShell
      eyebrow={t('policy.eyebrow')}
      title={t('policy.title')}
      description={t('policy.description')}
      icon={Settings2}
      metrics={[
        {
          label: t('policy.roleMatrixTitle'),
          value: String(GOVERNANCE_ROLE_PERMISSION_MATRIX.length),
          hint: t('policy.roleMatrixDescription'),
          tone: 'info',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="space-y-6 xl:col-span-7">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.roleMatrixTitle')}
                </h2>
                <p className="mt-1 text-sm font-mono text-muted-foreground">
                  {t('policy.roleMatrixDescription')}
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-3">
              {GOVERNANCE_ROLE_PERMISSION_MATRIX.map((entry) => (
                <div
                  key={entry.role}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {entry.role}
                    </p>
                    <GovernanceStatusChip
                      label={String(entry.permissions.length)}
                      tone="info"
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {entry.permissions.map((permission) => (
                      <GovernanceStatusChip
                        key={`${entry.role}-${permission}`}
                        label={humanizeToken(permission)}
                        tone="neutral"
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="xl:col-span-5">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('policy.gapTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('policy.gapDescription')}
            </p>
            <div className="mt-5">
              <GovernanceEmptyState label={t('policy.empty')} />
            </div>
          </article>
        </section>
      </div>
    </GovernancePageShell>
  );
}
