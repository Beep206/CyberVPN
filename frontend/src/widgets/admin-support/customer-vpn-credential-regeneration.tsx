'use client';

import { AlertTriangle, CheckCircle2, KeyRound, RotateCw } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import {
  buildCredentialRegenerationRequest,
  canRegenerateVpnCredentials,
  summarizeCredentialRegenerationResult,
  type CredentialRegenerationResult,
  type SafeCredentialRegenerationSummary,
  type Stage1CredentialRegenerationRole,
} from './customer-vpn-credential-regeneration-model';

export type CustomerVpnCredentialRegenerationProps = {
  actorRole: Stage1CredentialRegenerationRole;
  customerLabel: string;
  disabled?: boolean;
  onRegenerate: (payload: {
    reason: string;
    revoke_only_passwords: boolean;
  }) => Promise<CredentialRegenerationResult>;
  userId: string;
};

type SubmitState =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'success'; summary: SafeCredentialRegenerationSummary }
  | { kind: 'error'; message: string };

export function CustomerVpnCredentialRegeneration({
  actorRole,
  customerLabel,
  disabled = false,
  onRegenerate,
  userId,
}: CustomerVpnCredentialRegenerationProps) {
  const [reason, setReason] = useState('');
  const [revokeOnlyPasswords, setRevokeOnlyPasswords] = useState(false);
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: 'idle' });
  const allowed = canRegenerateVpnCredentials(actorRole);
  const actionDisabled = disabled || !allowed || submitState.kind === 'submitting';

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!allowed) {
      setSubmitState({
        kind: 'error',
        message: 'This role cannot regenerate VPN credentials.',
      });
      return;
    }

    const request = buildCredentialRegenerationRequest({
      reason,
      revokeOnlyPasswords,
    });
    if (!request.ok) {
      setSubmitState({ kind: 'error', message: request.error });
      return;
    }

    setSubmitState({ kind: 'submitting' });
    try {
      const result = await onRegenerate(request.payload);
      setSubmitState({
        kind: 'success',
        summary: summarizeCredentialRegenerationResult(result),
      });
      setReason('');
      setRevokeOnlyPasswords(false);
    } catch {
      setSubmitState({
        kind: 'error',
        message: 'Credential regeneration failed. Escalate to manual support review.',
      });
    }
  }

  return (
    <section
      aria-labelledby="vpn-credential-regeneration-title"
      className="rounded border border-grid-line/60 bg-black/30 p-4"
      data-testid="vpn-credential-regeneration"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 text-neon-cyan">
            <KeyRound aria-hidden="true" className="h-4 w-4 shrink-0" />
            <h3
              className="truncate text-sm font-display uppercase"
              id="vpn-credential-regeneration-title"
            >
              VPN credential rotation
            </h3>
          </div>
          <p className="break-words text-xs font-mono text-muted-foreground">
            {customerLabel} · {userId}
          </p>
        </div>
        <span
          className="w-fit rounded border border-matrix-green/60 px-2 py-1 text-[10px] font-bold uppercase text-matrix-green"
          data-testid="vpn-credential-role"
        >
          {actorRole}
        </span>
      </div>

      {!allowed ? (
        <div
          className="mt-4 flex items-start gap-2 rounded border border-server-warning/50 bg-server-warning/10 p-3 text-xs text-server-warning"
          role="alert"
        >
          <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Credential rotation is restricted to owner, super admin, admin, or support roles.</span>
        </div>
      ) : null}

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase text-muted-foreground">Support reason</span>
          <textarea
            className="min-h-24 w-full resize-y rounded border border-grid-line/70 bg-black/40 px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-neon-cyan"
            disabled={actionDisabled}
            maxLength={1000}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Customer lost device; rotate VPN credentials"
            value={reason}
          />
        </label>

        <label className="flex items-start gap-3 rounded border border-grid-line/50 bg-black/20 p-3 text-sm text-foreground">
          <input
            checked={revokeOnlyPasswords}
            className="mt-1 h-4 w-4 accent-neon-cyan"
            disabled={actionDisabled}
            onChange={(event) => setRevokeOnlyPasswords(event.target.checked)}
            type="checkbox"
          />
          <span>
            Revoke only protocol passwords and keep the subscription short UUID if Remnawave allows it.
          </span>
        </label>

        <button
          className="inline-flex min-h-10 items-center gap-2 rounded border border-neon-cyan px-4 py-2 text-sm font-bold uppercase text-neon-cyan transition-colors hover:bg-neon-cyan/10 disabled:cursor-not-allowed disabled:border-muted-foreground disabled:text-muted-foreground"
          disabled={actionDisabled}
          type="submit"
        >
          <RotateCw
            aria-hidden="true"
            className={`h-4 w-4 ${submitState.kind === 'submitting' ? 'animate-spin' : ''}`}
          />
          Regenerate credentials
        </button>
      </form>

      {submitState.kind === 'error' ? (
        <div
          className="mt-4 flex items-start gap-2 rounded border border-server-offline/50 bg-server-offline/10 p-3 text-xs text-server-offline"
          role="alert"
        >
          <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{submitState.message}</span>
        </div>
      ) : null}

      {submitState.kind === 'success' ? (
        <CredentialRegenerationSuccess summary={submitState.summary} />
      ) : null}
    </section>
  );
}

function CredentialRegenerationSuccess({
  summary,
}: {
  summary: SafeCredentialRegenerationSummary;
}) {
  return (
    <div
      className="mt-4 rounded border border-matrix-green/50 bg-matrix-green/10 p-3 text-xs"
      role="status"
    >
      <div className="mb-3 flex items-center gap-2 font-bold uppercase text-matrix-green">
        <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
        Credentials regenerated
      </div>
      <dl className="grid gap-2 text-muted-foreground sm:grid-cols-2">
        <div>
          <dt className="font-mono uppercase">Audit action</dt>
          <dd className="break-words text-foreground">{summary.auditAction}</dd>
        </div>
        <div>
          <dt className="font-mono uppercase">VPN identity</dt>
          <dd className="break-words text-foreground">{summary.vpnIdentity}</dd>
        </div>
        <div>
          <dt className="font-mono uppercase">Subscription URL changed</dt>
          <dd className="text-foreground">{summary.subscriptionUrlChanged ? 'yes' : 'no'}</dd>
        </div>
        <div>
          <dt className="font-mono uppercase">Short UUID changed</dt>
          <dd className="text-foreground">{summary.shortUuidChanged ? 'yes' : 'no'}</dd>
        </div>
        <div>
          <dt className="font-mono uppercase">Delivery required</dt>
          <dd className="text-foreground">{summary.deliveryRequired ? 'yes' : 'no'}</dd>
        </div>
        <div>
          <dt className="font-mono uppercase">Mode</dt>
          <dd className="text-foreground">
            {summary.revokeOnlyPasswords ? 'password rotation' : 'full rotation'}
          </dd>
        </div>
      </dl>
    </div>
  );
}
