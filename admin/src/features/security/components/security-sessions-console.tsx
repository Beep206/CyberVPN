'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Laptop,
  Monitor,
  RefreshCw,
  Smartphone,
  Trash2,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { authApi } from '@/lib/api/auth';
import { SecurityEmptyState } from '@/features/security/components/security-empty-state';
import { SecurityPageShell } from '@/features/security/components/security-page-shell';
import { SecurityStatusChip } from '@/features/security/components/security-status-chip';
import {
  describeUserAgent,
  formatDateTime,
  getDeviceKind,
  getErrorMessage,
  shortId,
} from '@/features/security/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';
import { AdminActionDialog } from '@/shared/ui/admin-action-dialog';

function DeviceIcon({ userAgent }: { userAgent: string | null | undefined }) {
  const kind = getDeviceKind(userAgent);
  if (kind === 'mobile') {
    return <Smartphone className="h-5 w-5" />;
  }
  if (kind === 'tablet') {
    return <Monitor className="h-5 w-5" />;
  }
  return <Laptop className="h-5 w-5" />;
}

export function SecuritySessionsConsole() {
  const t = useTranslations('AdminSecurity');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string | null>(null);
  const [logoutAllOpen, setLogoutAllOpen] = useState(false);
  const [deviceToRevoke, setDeviceToRevoke] = useState<{
    device_id: string | null;
    user_agent: string | null;
    ip_address: string | null;
  } | null>(null);

  const devicesQuery = useQuery({
    queryKey: ['security', 'devices'],
    queryFn: async () => {
      const response = await authApi.listDevices();
      return response.data;
    },
    staleTime: 15_000,
  });

  const revokeMutation = useMutation({
    mutationFn: (deviceId: string) => authApi.logoutDevice(deviceId),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['security', 'devices'] });
      setFeedback(response.data.message || t('sessions.revokeSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const logoutAllMutation = useMutation({
    mutationFn: () => authApi.logoutAllDevices(),
    onSuccess: async (response) => {
      setFeedback(
        t('sessions.logoutAllSuccess', {
          count: response.data.sessions_revoked,
        }),
      );
      window.location.assign(`/${locale}/login`);
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const devices = devicesQuery.data?.devices ?? [];
  const currentDevice = devices.find((device) => device.is_current);

  return (
    <SecurityPageShell
      eyebrow={t('sessions.eyebrow')}
      title={t('sessions.title')}
      description={t('sessions.description')}
      icon={Smartphone}
      actions={
        <>
          <Button
            magnetic={false}
            variant="ghost"
            onClick={() => {
              void queryClient.invalidateQueries({ queryKey: ['security', 'devices'] });
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('common.refresh')}
          </Button>
          <Button
            magnetic={false}
            variant="ghost"
            disabled={logoutAllMutation.isPending || devices.length === 0}
            onClick={() => setLogoutAllOpen(true)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            {t('common.logoutAll')}
          </Button>
        </>
      }
      metrics={[
        {
          label: t('sessions.metrics.total'),
          value: String(devices.length),
          hint: t('sessions.metrics.totalHint'),
          tone: devices.length > 3 ? 'warning' : 'info',
        },
        {
          label: t('sessions.metrics.remote'),
          value: String(devices.filter((device) => !device.is_current).length),
          hint: t('sessions.metrics.remoteHint'),
          tone: 'warning',
        },
        {
          label: t('sessions.metrics.current'),
          value: currentDevice?.ip_address ?? '--',
          hint: t('sessions.metrics.currentHint'),
          tone: 'success',
        },
        {
          label: t('sessions.metrics.lastSeen'),
          value: formatDateTime(currentDevice?.last_used_at, locale),
          hint: t('sessions.metrics.lastSeenHint'),
          tone: 'neutral',
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

          {devicesQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : devices.length === 0 ? (
            <SecurityEmptyState label={t('sessions.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.sessions')}</TableHead>
                  <TableHead>{t('common.ipAddress')}</TableHead>
                  <TableHead>{t('common.lastUsed')}</TableHead>
                  <TableHead>{t('common.createdAt')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.map((device) => (
                  <TableRow key={device.device_id ?? device.created_at}>
                    <TableCell>
                      <div className="flex items-start gap-3">
                        <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-pink">
                          <DeviceIcon userAgent={device.user_agent} />
                        </div>
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-display uppercase tracking-[0.14em] text-white">
                              {describeUserAgent(device.user_agent)}
                            </p>
                            {device.is_current ? (
                              <SecurityStatusChip
                                label={t('common.current')}
                                tone="success"
                              />
                            ) : null}
                          </div>
                          <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                            #{shortId(device.device_id)} / {device.user_agent ?? '--'}
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{device.ip_address ?? '--'}</TableCell>
                    <TableCell>{formatDateTime(device.last_used_at, locale)}</TableCell>
                    <TableCell>{formatDateTime(device.created_at, locale)}</TableCell>
                    <TableCell>
                      {device.is_current ? (
                        <SecurityStatusChip
                          label={t('sessions.currentDevice')}
                          tone="info"
                        />
                      ) : (
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          magnetic={false}
                          disabled={revokeMutation.isPending}
                          onClick={() => {
                            if (!device.device_id) return;
                            setDeviceToRevoke({
                              device_id: device.device_id,
                              user_agent: device.user_agent ?? null,
                              ip_address: device.ip_address ?? null,
                            });
                          }}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          {t('common.logoutDevice')}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>

        <section className="space-y-6 xl:col-span-4">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('sessions.currentTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('sessions.currentDescription')}
            </p>

            {currentDevice ? (
              <div className="mt-5 space-y-3">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.ipAddress')}
                  </p>
                  <p className="mt-3 text-sm font-mono leading-6 text-white">
                    {currentDevice.ip_address ?? '--'}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.lastUsed')}
                  </p>
                  <p className="mt-3 text-sm font-mono leading-6 text-white">
                    {formatDateTime(currentDevice.last_used_at, locale)}
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-5">
                <SecurityEmptyState label={t('sessions.empty')} />
              </div>
            )}
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('sessions.hardStopTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('sessions.hardStopDescription')}
            </p>
            <Button
              type="button"
              magnetic={false}
              className="mt-5"
              disabled={logoutAllMutation.isPending}
              onClick={() => setLogoutAllOpen(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {t('common.logoutAll')}
            </Button>
          </article>
        </section>
      </div>

      <AdminActionDialog
        isOpen={logoutAllOpen}
        isPending={logoutAllMutation.isPending}
        title={t('sessions.logoutAllTitle')}
        description={t('sessions.logoutAllConfirm')}
        confirmLabel={t('common.logoutAll')}
        cancelLabel={t('common.cancel')}
        onClose={() => setLogoutAllOpen(false)}
        onConfirm={async () => {
          await logoutAllMutation.mutateAsync();
          setLogoutAllOpen(false);
        }}
      />

      <AdminActionDialog
        isOpen={Boolean(deviceToRevoke)}
        isPending={revokeMutation.isPending}
        title={t('sessions.revokeTitle')}
        description={t('sessions.revokeConfirm')}
        confirmLabel={t('common.logoutDevice')}
        cancelLabel={t('common.cancel')}
        subjectLabel={t('common.sessions')}
        subject={
          deviceToRevoke ? (
            <div className="space-y-1">
              <p>{describeUserAgent(deviceToRevoke.user_agent)}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {deviceToRevoke.ip_address ?? '--'}
              </p>
            </div>
          ) : null
        }
        onClose={() => setDeviceToRevoke(null)}
        onConfirm={async () => {
          if (!deviceToRevoke?.device_id) {
            return;
          }
          await revokeMutation.mutateAsync(deviceToRevoke.device_id);
          setDeviceToRevoke(null);
        }}
      />
    </SecurityPageShell>
  );
}
