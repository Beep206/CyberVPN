'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, ShieldAlert, SquareTerminal, Unplug } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { requestPasskeyFreshAuthGrant } from '@/features/auth/lib/passkey-fresh-auth';
import { adminRemnawaveStatusApi } from '@/lib/api/remnawave-status';
import { InfrastructureEmptyState } from './empty-state';
import { InfrastructureStatusChip } from './infrastructure-status-chip';

const EXPECTED_WEBSOCKET_PATH = '/api/v1/admin/remnawave/node-ssh/ws';
const EXPECTED_WEBSOCKET_PROTOCOL = 'cybervpn-remnawave-ssh-v1';
const TICKET_PATTERN = /^[A-Za-z0-9_-]{32,96}$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const MAX_TERMINAL_OUTPUT_CHARS = 65_536;
const MAX_TERMINAL_INPUT_CHARS = 4_096;

type SessionPhase =
  | 'idle'
  | 'authenticating'
  | 'connecting'
  | 'connected'
  | 'disconnecting'
  | 'closed'
  | 'error';

interface SessionHandle {
  socket: WebSocket;
  ticket: string;
}

function getHttpStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null || !('response' in error)) return null;
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

function sanitizeTerminalOutput(value: string): string {
  return value.replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, '').replace(
    /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g,
    '',
  );
}

function buildWebSocketUrl(path: string): string {
  const url = new URL(path, window.location.origin);
  if (url.origin !== window.location.origin || url.pathname !== EXPECTED_WEBSOCKET_PATH) {
    throw new Error('invalid_node_ssh_websocket_path');
  }
  if (url.protocol === 'https:') url.protocol = 'wss:';
  else if (url.protocol === 'http:') url.protocol = 'ws:';
  else throw new Error('invalid_node_ssh_websocket_scheme');
  return url.toString();
}

async function messageToText(data: unknown): Promise<string | null> {
  if (typeof data === 'string') return data;
  if (data instanceof ArrayBuffer) return new TextDecoder().decode(data);
  if (typeof Blob !== 'undefined' && data instanceof Blob) return data.text();
  return null;
}

export function RemnawaveNodeSshConsole({ enabled }: { enabled: boolean }) {
  const t = useTranslations('Infrastructure.remnawave.nodeSsh');
  const mountedRef = useRef(true);
  const sessionRef = useRef<SessionHandle | null>(null);
  const [selectedNodeUuid, setSelectedNodeUuid] = useState('');
  const [reason, setReason] = useState('');
  const [command, setCommand] = useState('');
  const [phase, setPhase] = useState<SessionPhase>('idle');
  const [output, setOutput] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const diagnosticsQuery = useQuery({
    queryKey: ['infrastructure', 'remnawave', 'node-ssh', 'diagnostics'],
    queryFn: async () => (await adminRemnawaveStatusApi.getNodeDiagnostics()).data,
    enabled,
    retry: false,
    staleTime: 15_000,
  });

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      const session = sessionRef.current;
      sessionRef.current = null;
      if (!session) return;
      session.socket.onopen = null;
      session.socket.onmessage = null;
      session.socket.onerror = null;
      session.socket.onclose = null;
      session.socket.close(1000, 'admin_console_unmounted');
      void adminRemnawaveStatusApi
        .revokeNodeSshTicket(session.ticket, 'Admin console unmounted')
        .catch(() => undefined);
    };
  }, []);

  function appendOutput(value: string) {
    const safeValue = sanitizeTerminalOutput(value);
    if (!safeValue) return;
    setOutput((current) => `${current}${safeValue}`.slice(-MAX_TERMINAL_OUTPUT_CHARS));
  }

  async function revokeIssuedTicket(ticket: string, revokeReason: string) {
    try {
      await adminRemnawaveStatusApi.revokeNodeSshTicket(ticket, revokeReason);
    } catch {
      // The WebSocket relay also revokes on close; 404 after relay cleanup is expected.
    }
  }

  async function handleConnect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sessionRef.current || phase === 'authenticating' || phase === 'connecting') return;
    const normalizedReason = reason.trim();
    if (!UUID_PATTERN.test(selectedNodeUuid) || normalizedReason.length < 8) {
      setFeedback(t('feedback.validation'));
      return;
    }

    setFeedback(null);
    setOutput('');
    setPhase('authenticating');
    let issuedTicket: string | null = null;
    try {
      const freshAuthGrantId = await requestPasskeyFreshAuthGrant(
        `remnawave_node_ssh:issue:${selectedNodeUuid}`,
      );
      if (!mountedRef.current) return;

      setPhase('connecting');
      const response = await adminRemnawaveStatusApi.issueNodeSshTicket(
        selectedNodeUuid,
        normalizedReason,
        { freshAuthGrantId },
      );
      issuedTicket = response.data.ticket;
      if (!mountedRef.current) {
        await revokeIssuedTicket(issuedTicket, 'Admin console unmounted');
        return;
      }
      if (
        response.data.node_uuid.toLowerCase() !== selectedNodeUuid.toLowerCase()
        || response.data.websocket_path !== EXPECTED_WEBSOCKET_PATH
        || response.data.websocket_protocol !== EXPECTED_WEBSOCKET_PROTOCOL
        || !TICKET_PATTERN.test(issuedTicket)
        || response.data.expires_in_seconds < 1
        || response.data.expires_in_seconds > 15
      ) {
        await revokeIssuedTicket(issuedTicket, 'Invalid terminal contract');
        issuedTicket = null;
        throw new Error('invalid_node_ssh_ticket_contract');
      }

      const socket = new WebSocket(
        buildWebSocketUrl(response.data.websocket_path),
        [response.data.websocket_protocol, issuedTicket],
      );
      sessionRef.current = { socket, ticket: issuedTicket };
      issuedTicket = null;

      socket.onopen = () => {
        if (!mountedRef.current || sessionRef.current?.socket !== socket) return;
        setPhase('connected');
        setReason('');
        setFeedback(t('feedback.connected'));
      };
      socket.onmessage = (message) => {
        void messageToText(message.data).then((text) => {
          if (
            text !== null
            && mountedRef.current
            && sessionRef.current?.socket === socket
          ) {
            appendOutput(text);
          }
        });
      };
      socket.onerror = () => {
        if (!mountedRef.current || sessionRef.current?.socket !== socket) return;
        const failedSession = sessionRef.current;
        sessionRef.current = null;
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        socket.close(1011, 'terminal_relay_error');
        void revokeIssuedTicket(failedSession.ticket, 'Terminal relay failed');
        setPhase('error');
        setFeedback(t('feedback.relayError'));
      };
      socket.onclose = () => {
        if (!mountedRef.current || sessionRef.current?.socket !== socket) return;
        const closedSession = sessionRef.current;
        sessionRef.current = null;
        void revokeIssuedTicket(closedSession.ticket, 'Terminal relay closed');
        setPhase('closed');
        setCommand('');
        setFeedback(t('feedback.closed'));
      };
    } catch (error) {
      if (issuedTicket) await revokeIssuedTicket(issuedTicket, 'Terminal setup failed');
      if (!mountedRef.current) return;
      const status = getHttpStatus(error);
      setPhase('error');
      setFeedback(
        status === 403
          ? t('feedback.permissionDenied')
          : status === 404
            ? t('feedback.unavailable')
            : t('feedback.connectFailed'),
      );
    }
  }

  async function handleDisconnect() {
    const session = sessionRef.current;
    if (!session) return;
    sessionRef.current = null;
    setPhase('disconnecting');
    setCommand('');
    session.socket.onopen = null;
    session.socket.onmessage = null;
    session.socket.onerror = null;
    session.socket.onclose = null;
    session.socket.close(1000, 'admin_requested_disconnect');
    await revokeIssuedTicket(session.ticket, 'Admin requested disconnect');
    if (!mountedRef.current) return;
    setPhase('closed');
    setFeedback(t('feedback.revoked'));
  }

  function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const session = sessionRef.current;
    if (!session || phase !== 'connected' || session.socket.readyState !== WebSocket.OPEN) return;
    if (!command || command.length > MAX_TERMINAL_INPUT_CHARS) {
      setFeedback(t('feedback.commandInvalid'));
      return;
    }
    session.socket.send(`${command}\n`);
    setCommand('');
  }

  if (!enabled) {
    return (
      <section className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/70 p-5 md:p-6">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-1 h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <div>
            <h2 className="font-display text-xl text-white">{t('title')}</h2>
            <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">
              {t('disabled')}
            </p>
          </div>
        </div>
      </section>
    );
  }

  const nodes = (diagnosticsQuery.data?.nodes ?? []).filter((node) => UUID_PATTERN.test(node.uuid));
  const connected = phase === 'connected';
  const busy = phase === 'authenticating' || phase === 'connecting' || phase === 'disconnecting';
  const diagnosticsForbidden = getHttpStatus(diagnosticsQuery.error) === 403;

  return (
    <section
      aria-labelledby="remnawave-node-ssh-title"
      className="rounded-[1.5rem] border border-neon-pink/20 bg-terminal-bg/70 p-5 md:p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <SquareTerminal className="mt-1 h-5 w-5 text-neon-pink" aria-hidden="true" />
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-pink/80">
              {t('eyebrow')}
            </p>
            <h2 id="remnawave-node-ssh-title" className="mt-2 font-display text-xl text-white">
              {t('title')}
            </h2>
            <p className="mt-2 max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
              {t('description')}
            </p>
          </div>
        </div>
        <InfrastructureStatusChip
          label={t(`phases.${phase}`)}
          tone={connected ? 'success' : phase === 'error' ? 'danger' : busy ? 'warning' : 'neutral'}
        />
      </div>

      {feedback ? (
        <p role="status" aria-live="polite" className="mt-4 rounded-lg border border-grid-line/20 px-3 py-2 font-mono text-xs text-amber-100">
          {feedback}
        </p>
      ) : null}

      <div className="mt-6 grid gap-6 xl:grid-cols-12">
        <div className="xl:col-span-4">
          {diagnosticsQuery.isPending ? (
            <div role="status" className="h-40 animate-pulse rounded-xl bg-terminal-surface/35">
              <span className="sr-only">{t('loadingNodes')}</span>
            </div>
          ) : diagnosticsQuery.isError ? (
            <div role="alert" className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
              <p className="font-mono text-sm text-amber-100">
                {diagnosticsForbidden ? t('feedback.permissionDenied') : t('nodesError')}
              </p>
              {!diagnosticsForbidden ? (
                <Button magnetic={false} type="button" variant="outline" className="mt-3" onClick={() => void diagnosticsQuery.refetch()}>
                  <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                  {t('retry')}
                </Button>
              ) : null}
            </div>
          ) : nodes.length === 0 ? (
            <InfrastructureEmptyState label={t('nodesEmpty')} />
          ) : (
            <form onSubmit={(event) => void handleConnect(event)} className="grid gap-4 rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-4">
              <label className="grid gap-2 font-mono text-xs text-muted-foreground">
                {t('fields.node')}
                <select
                  value={selectedNodeUuid}
                  onChange={(event) => setSelectedNodeUuid(event.target.value)}
                  disabled={busy || connected}
                  required
                  className="min-h-11 rounded-lg border border-grid-line/30 bg-terminal-bg/80 px-3 text-sm text-white outline-hidden focus:border-neon-pink"
                >
                  <option value="">{t('selectNode')}</option>
                  {nodes.map((node) => (
                    <option key={node.uuid} value={node.uuid}>
                      {node.name} · {node.status}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid gap-2 font-mono text-xs text-muted-foreground">
                {t('fields.reason')}
                <textarea
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  minLength={8}
                  maxLength={256}
                  disabled={busy || connected}
                  required
                  className="min-h-24 rounded-lg border border-grid-line/30 bg-terminal-bg/80 px-3 py-2 text-sm text-white outline-hidden focus:border-neon-pink"
                />
              </label>
              {!connected ? (
                <Button magnetic={false} type="submit" disabled={busy}>
                  <SquareTerminal className="mr-2 h-4 w-4" aria-hidden="true" />
                  {busy ? t('connectPending') : t('connect')}
                </Button>
              ) : null}
            </form>
          )}
        </div>

        <div className="grid min-w-0 gap-3 xl:col-span-8">
          <div
            role="log"
            aria-live="polite"
            aria-label={t('terminalLabel')}
            tabIndex={0}
            className="min-h-72 max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-xl border border-grid-line/30 bg-black/80 p-4 font-mono text-sm leading-6 text-matrix-green focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-cyan"
          >
            {output || t('terminalEmpty')}
          </div>
          <form onSubmit={handleSend} className="flex flex-col gap-2 sm:flex-row">
            <label className="sr-only" htmlFor="remnawave-ssh-command">
              {t('fields.command')}
            </label>
            <input
              id="remnawave-ssh-command"
              value={command}
              onChange={(event) => setCommand(event.target.value.slice(0, MAX_TERMINAL_INPUT_CHARS))}
              autoComplete="off"
              spellCheck={false}
              disabled={!connected}
              className="min-h-11 min-w-0 flex-1 rounded-lg border border-grid-line/30 bg-terminal-bg/80 px-3 font-mono text-sm text-white outline-hidden focus:border-neon-cyan"
              placeholder={t('commandPlaceholder')}
            />
            <Button magnetic={false} type="submit" disabled={!connected || !command}>
              {t('send')}
            </Button>
            <Button magnetic={false} type="button" variant="outline" disabled={!connected && !busy} onClick={() => void handleDisconnect()}>
              <Unplug className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('disconnect')}
            </Button>
          </form>
          <p className="font-mono text-xs leading-5 text-muted-foreground">
            {t('privacyNote')}
          </p>
        </div>
      </div>
    </section>
  );
}
