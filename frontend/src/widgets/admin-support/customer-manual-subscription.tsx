'use client';

import { AlertTriangle, CalendarPlus, CheckCircle2, ShieldPlus } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import {
  buildManualSubscriptionRequest,
  canApplyManualSubscription,
  summarizeManualSubscriptionResult,
  type ManualSubscriptionResult,
  type SafeManualSubscriptionSummary,
  type Stage1ManualSubscriptionRole,
} from './customer-manual-subscription-model';

export type CustomerManualSubscriptionProps = {
  actorRole: Stage1ManualSubscriptionRole;
  customerLabel: string;
  disabled?: boolean;
  onApply: (payload: {
    device_limit: number;
    duration_days: number;
    reason: string;
    traffic_limit_bytes?: number | null;
  }) => Promise<ManualSubscriptionResult>;
  userId: string;
};

type SubmitState =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'success'; summary: SafeManualSubscriptionSummary }
  | { kind: 'error'; message: string };

export function CustomerManualSubscription({
  actorRole,
  customerLabel,
  disabled = false,
  onApply,
  userId,
}: CustomerManualSubscriptionProps) {
  const [durationDays, setDurationDays] = useState(30);
  const [deviceLimit, setDeviceLimit] = useState(1);
  const [trafficLimitGb, setTrafficLimitGb] = useState('');
  const [reason, setReason] = useState('');
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: 'idle' });
  const allowed = canApplyManualSubscription(actorRole);
  const actionDisabled = disabled || !allowed || submitState.kind === 'submitting';

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!allowed) {
      setSubmitState({
        kind: 'error',
        message: 'This role cannot grant or extend subscriptions manually.',
      });
      return;
    }

    const parsedTrafficGb = trafficLimitGb.trim() ? Number(trafficLimitGb) : null;
    const trafficLimitBytes =
      parsedTrafficGb === null ? null : Math.floor(parsedTrafficGb * 1024 * 1024 * 1024);
    const request = buildManualSubscriptionRequest({
      deviceLimit,
      durationDays,
      reason,
      trafficLimitBytes,
    });
    if (!request.ok) {
      setSubmitState({ kind: 'error', message: request.error });
      return;
    }

    setSubmitState({ kind: 'submitting' });
    try {
      const result = await onApply(request.payload);
      setSubmitState({
        kind: 'success',
        summary: summarizeManualSubscriptionResult(result),
      });
      setReason('');
    } catch {
      setSubmitState({
        kind: 'error',
        message: 'Manual subscription operation failed. Escalate to owner support review.',
      });
    }
  }

  return (
    <section
      aria-labelledby="manual-subscription-title"
      className="rounded border border-grid-line/60 bg-black/30 p-4"
      data-testid="manual-subscription"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 text-neon-cyan">
            <ShieldPlus aria-hidden="true" className="h-4 w-4 shrink-0" />
            <h3
              className="truncate text-sm font-display uppercase"
              id="manual-subscription-title"
            >
              Manual subscription grant
            </h3>
          </div>
          <p className="break-words text-xs font-mono text-muted-foreground">
            {customerLabel} · {userId}
          </p>
        </div>
        <span
          className="w-fit rounded border border-matrix-green/60 px-2 py-1 text-[10px] font-bold uppercase text-matrix-green"
          data-testid="manual-subscription-role"
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
          <span>Manual subscription grants are restricted to owner, super admin, admin, or operator roles.</span>
        </div>
      ) : null}

      <form className="mt-4 space-y-4" noValidate onSubmit={handleSubmit}>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block space-y-2">
            <span className="text-xs font-mono uppercase text-muted-foreground">Duration days</span>
            <input
              className="h-10 w-full rounded border border-grid-line/70 bg-black/40 px-3 text-sm text-foreground outline-none transition-colors focus:border-neon-cyan"
              disabled={actionDisabled}
              max={365}
              min={1}
              onChange={(event) => setDurationDays(Number(event.target.value))}
              type="number"
              value={durationDays}
            />
          </label>
          <label className="block space-y-2">
            <span className="text-xs font-mono uppercase text-muted-foreground">Device limit</span>
            <input
              className="h-10 w-full rounded border border-grid-line/70 bg-black/40 px-3 text-sm text-foreground outline-none transition-colors focus:border-neon-cyan"
              disabled={actionDisabled}
              max={10}
              min={1}
              onChange={(event) => setDeviceLimit(Number(event.target.value))}
              type="number"
              value={deviceLimit}
            />
          </label>
          <label className="block space-y-2">
            <span className="text-xs font-mono uppercase text-muted-foreground">Traffic GB</span>
            <input
              className="h-10 w-full rounded border border-grid-line/70 bg-black/40 px-3 text-sm text-foreground outline-none transition-colors focus:border-neon-cyan"
              disabled={actionDisabled}
              min={1}
              onChange={(event) => setTrafficLimitGb(event.target.value)}
              placeholder="Unlimited"
              type="number"
              value={trafficLimitGb}
            />
          </label>
        </div>

        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase text-muted-foreground">Operator reason</span>
          <textarea
            className="min-h-24 w-full resize-y rounded border border-grid-line/70 bg-black/40 px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-neon-cyan"
            disabled={actionDisabled}
            maxLength={1000}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Payment provider failed; grant beta access after manual review"
            value={reason}
          />
        </label>

        <button
          className="inline-flex min-h-10 items-center gap-2 rounded border border-neon-cyan px-4 py-2 text-sm font-bold uppercase text-neon-cyan transition-colors hover:bg-neon-cyan/10 disabled:cursor-not-allowed disabled:border-muted-foreground disabled:text-muted-foreground"
          disabled={actionDisabled}
          type="submit"
        >
          <CalendarPlus
            aria-hidden="true"
            className={`h-4 w-4 ${submitState.kind === 'submitting' ? 'animate-pulse' : ''}`}
          />
          Apply access
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
        <ManualSubscriptionSuccess summary={submitState.summary} />
      ) : null}
    </section>
  );
}

function ManualSubscriptionSuccess({
  summary,
}: {
  summary: SafeManualSubscriptionSummary;
}) {
  return (
    <div
      className="mt-4 rounded border border-matrix-green/50 bg-matrix-green/10 p-3 text-xs"
      role="status"
    >
      <div className="mb-3 flex items-center gap-2 font-bold uppercase text-matrix-green">
        <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
        Manual access applied
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
          <dt className="font-mono uppercase">Operation</dt>
          <dd className="text-foreground">{summary.operation}</dd>
        </div>
        <div>
          <dt className="font-mono uppercase">Duration</dt>
          <dd className="text-foreground">{summary.durationDays} days</dd>
        </div>
        <div>
          <dt className="font-mono uppercase">Expires</dt>
          <dd className="break-words text-foreground">{summary.expiresAt}</dd>
        </div>
        <div>
          <dt className="font-mono uppercase">Delivery required</dt>
          <dd className="text-foreground">{summary.configDeliveryRequired ? 'yes' : 'no'}</dd>
        </div>
      </dl>
    </div>
  );
}
