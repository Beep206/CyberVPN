'use client';

import { useEffect, useRef, useState, startTransition } from 'react';
import { Activity, RadioTower, Ticket } from 'lucide-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { monitoringApi } from '@/lib/api/monitoring';
import { integrationsApi } from '@/lib/api/integrations';
import { IntegrationsEmptyState } from '@/features/integrations/components/integrations-empty-state';
import { IntegrationsPageShell } from '@/features/integrations/components/integrations-page-shell';
import { IntegrationsStatusChip } from '@/features/integrations/components/integrations-status-chip';
import {
  formatBytes,
  formatDateTime,
  getErrorMessage,
  humanizeToken,
  socketStateTone,
  statusTone,
} from '@/features/integrations/lib/formatting';
import {
  buildMonitoringSocketUrl,
  MONITORING_TOPIC_OPTIONS,
  type MonitoringTopic,
} from '@/features/integrations/lib/realtime';

type LogEntry = {
  id: string;
  timestamp: string;
  label: string;
  payload: string;
  tone: 'neutral' | 'success' | 'info' | 'warning' | 'danger';
};

export function RealtimeOpsConsole() {
  const t = useTranslations('Integrations');
  const locale = useLocale();
  const socketRef = useRef<WebSocket | null>(null);
  const [socketState, setSocketState] = useState<
    'idle' | 'connecting' | 'open' | 'closed' | 'error'
  >('idle');
  const [selectedTopics, setSelectedTopics] = useState<MonitoringTopic[]>([
    'servers',
    'payments',
  ]);
  const [availableTopics, setAvailableTopics] = useState<string[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const healthQuery = useQuery({
    queryKey: ['integrations', 'realtime', 'health'],
    queryFn: async () => {
      const response = await monitoringApi.health();
      return response.data;
    },
    staleTime: 10_000,
  });

  const statsQuery = useQuery({
    queryKey: ['integrations', 'realtime', 'stats'],
    queryFn: async () => {
      const response = await monitoringApi.getStats();
      return response.data;
    },
    staleTime: 15_000,
  });

  const ticketMutation = useMutation({
    mutationFn: async () => {
      const response = await integrationsApi.createRealtimeTicket();
      return response.data;
    },
    onSuccess: (data) => {
      connectSocket(data.ticket);
    },
  });

  function appendLog(
    label: string,
    payload: unknown,
    tone: LogEntry['tone'] = 'info',
  ) {
    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      timestamp: new Date().toISOString(),
      label,
      payload:
        typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2),
      tone,
    };

    startTransition(() => {
      setLogs((current) => [entry, ...current].slice(0, 40));
    });
  }

  function disconnectSocket() {
    socketRef.current?.close();
    socketRef.current = null;
    setSocketState('closed');
  }

  function connectSocket(ticket: string) {
    try {
      disconnectSocket();
      setSocketState('connecting');
      const socket = new WebSocket(buildMonitoringSocketUrl(ticket));
      socketRef.current = socket;

      socket.addEventListener('open', () => {
        setSocketState('open');
        appendLog('socket_open', { ticket }, 'success');
      });

      socket.addEventListener('message', (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            type?: string;
            topics?: string[];
          };
          if (
            payload.type === 'available_topics'
            && Array.isArray(payload.topics)
          ) {
            setAvailableTopics(payload.topics);
          }
          appendLog(payload.type || 'message', payload, 'info');
        } catch {
          appendLog('message', event.data, 'info');
        }
      });

      socket.addEventListener('close', () => {
        setSocketState('closed');
        appendLog('socket_closed', 'Monitoring socket closed', 'warning');
      });

      socket.addEventListener('error', () => {
        setSocketState('error');
        appendLog('socket_error', 'Monitoring socket error', 'danger');
      });
    } catch (error) {
      setSocketState('error');
      appendLog('connect_failed', getErrorMessage(error), 'danger');
    }
  }

  function subscribeToSelectedTopics() {
    if (!socketRef.current || socketState !== 'open') {
      return;
    }

    socketRef.current.send(
      JSON.stringify({
        type: 'subscribe',
        topics: selectedTopics,
      }),
    );
    appendLog('subscribe', { topics: selectedTopics }, 'success');
  }

  function toggleTopic(topic: MonitoringTopic) {
    setSelectedTopics((current) =>
      current.includes(topic)
        ? current.filter((value) => value !== topic)
        : [...current, topic],
    );
  }

  useEffect(
    () => () => {
      disconnectSocket();
    },
    [],
  );

  return (
    <IntegrationsPageShell
      eyebrow={t('realtime.eyebrow')}
      title={t('realtime.title')}
      description={t('realtime.description')}
      icon={RadioTower}
      metrics={[
        {
          label: t('realtime.metrics.socket'),
          value: humanizeToken(socketState),
          hint: t('realtime.metrics.socketHint'),
          tone: socketStateTone(socketState),
        },
        {
          label: t('realtime.metrics.ticket'),
          value: ticketMutation.data?.expires_in
            ? `${ticketMutation.data.expires_in}s`
            : '--',
          hint: t('realtime.metrics.ticketHint'),
          tone: ticketMutation.data ? 'info' : 'neutral',
        },
        {
          label: t('realtime.metrics.availableTopics'),
          value: String(availableTopics.length),
          hint: t('realtime.metrics.availableTopicsHint'),
          tone: availableTopics.length ? 'success' : 'warning',
        },
        {
          label: t('realtime.metrics.traffic'),
          value: formatBytes(statsQuery.data?.total_traffic_bytes),
          hint: t('realtime.metrics.trafficHint'),
          tone: 'info',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Ticket className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('realtime.ticketTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('realtime.ticketDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => ticketMutation.mutate()}
              disabled={ticketMutation.isPending}
              className="rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-sm font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15"
            >
              {ticketMutation.isPending
                ? t('realtime.actions.requestingTicket')
                : t('realtime.actions.requestTicket')}
            </button>

            <button
              type="button"
              onClick={disconnectSocket}
              disabled={socketState !== 'open' && socketState !== 'connecting'}
              className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono uppercase tracking-[0.18em] text-white transition-colors hover:border-neon-cyan/35"
            >
              {t('realtime.actions.disconnect')}
            </button>
          </div>

          {ticketMutation.error ? (
            <div className="mt-4 rounded-2xl border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
              {getErrorMessage(ticketMutation.error)}
            </div>
          ) : null}

          <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                {t('realtime.connectionStatus')}
              </p>
              <IntegrationsStatusChip
                label={humanizeToken(socketState)}
                tone={socketStateTone(socketState)}
              />
            </div>
            <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
              {t('realtime.connectionSummary', {
                topics: String(selectedTopics.length),
              })}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('realtime.topicTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('realtime.topicDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {MONITORING_TOPIC_OPTIONS.map((topic) => {
              const selected = selectedTopics.includes(topic);
              const allowed = availableTopics.includes(topic);

              return (
                <button
                  key={topic}
                  type="button"
                  onClick={() => toggleTopic(topic)}
                  className={`rounded-2xl border p-4 text-left transition-colors ${
                    selected
                      ? 'border-neon-cyan/35 bg-neon-cyan/10'
                      : 'border-grid-line/20 bg-terminal-bg/45 hover:border-grid-line/40'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {t(`realtime.topics.${topic}`)}
                    </p>
                    <IntegrationsStatusChip
                      label={
                        allowed
                          ? t('common.allowed')
                          : t('common.unknown')
                      }
                      tone={allowed ? 'success' : 'neutral'}
                    />
                  </div>
                </button>
              );
            })}
          </div>

          <div className="mt-5">
            <button
              type="button"
              onClick={subscribeToSelectedTopics}
              disabled={socketState !== 'open' || selectedTopics.length === 0}
              className="rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-sm font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:bg-neon-cyan/15"
            >
              {t('realtime.actions.subscribe')}
            </button>
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('realtime.healthTitle')}
          </h2>
          <div className="mt-5 space-y-3">
            {healthQuery.data?.components ? (
              Object.entries(healthQuery.data.components).map(([key, component]) => (
                <div
                  key={key}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {humanizeToken(key)}
                    </p>
                    <IntegrationsStatusChip
                      label={humanizeToken(component.status)}
                      tone={statusTone(component.status)}
                    />
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {component.message}
                  </p>
                </div>
              ))
            ) : (
              <IntegrationsEmptyState label={t('common.empty')} />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('realtime.logTitle')}
          </h2>
          <div className="mt-5 space-y-3">
            {logs.length ? (
              logs.map((entry) => (
                <div
                  key={entry.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {entry.label}
                    </p>
                    <IntegrationsStatusChip
                      label={formatDateTime(entry.timestamp, locale)}
                      tone={entry.tone}
                    />
                  </div>
                  <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-all text-xs font-mono leading-5 text-muted-foreground">
                    {entry.payload}
                  </pre>
                </div>
              ))
            ) : (
              <IntegrationsEmptyState label={t('realtime.emptyLog')} />
            )}
          </div>
        </article>
      </div>
    </IntegrationsPageShell>
  );
}
