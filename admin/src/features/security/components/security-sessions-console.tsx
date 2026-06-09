'use client';

import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Laptop,
  LogOut,
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
  getUniqueDeviceCount,
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

type DeviceActionKind = 'logout-all' | 'logout-others' | 'revoke-device';

interface SecurityDeviceRow {
  device_id?: string | null;
  user_agent?: string | null;
  ip_address?: string | null;
  last_used_at: string;
  created_at: string;
  is_current: boolean;
}

interface DeviceRevokeCandidate {
  device_id: string;
  user_agent: string | null;
  ip_address: string | null;
}

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

function getDeviceRowKey(device: SecurityDeviceRow, index: number) {
  return device.device_id ?? `missing-device-id-${index}`;
}

export function SecuritySessionsConsole() {
  const t = useTranslations('AdminSecurity');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const actionLockRef = useRef<DeviceActionKind | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [logoutAllOpen, setLogoutAllOpen] = useState(false);
  const [logoutOthersOpen, setLogoutOthersOpen] = useState(false);
  const [deviceToRevoke, setDeviceToRevoke] =
    useState<DeviceRevokeCandidate | null>(null);

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

  const logoutOthersMutation = useMutation({
    mutationFn: () => authApi.logoutOtherDevices(),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['security', 'devices'] });
      setFeedback(
        t('sessions.logoutOthersSuccess', {
          count: response.data.sessions_revoked,
        }),
      );
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
  const deviceCount = getUniqueDeviceCount(devicesQuery.data);
  const currentDeviceIndex = devices.findIndex((device) => device.is_current);
  const currentDevice =
    currentDeviceIndex >= 0 ? devices[currentDeviceIndex] : undefined;
  const currentDeviceCount = currentDevice ? 1 : 0;
  const remoteDeviceCount = Math.max(deviceCount - currentDeviceCount, 0);
  const deviceLimit = devicesQuery.data?.device_limit ?? null;
  const remainingDevices = devicesQuery.data?.remaining_devices ?? null;
  const hasDevices = deviceCount > 0;
  const limitValue =
    deviceLimit === null
      ? t('sessions.metrics.unlimited')
      : `${deviceCount}/${deviceLimit}`;
  const limitHint =
    deviceLimit === null
      ? t('sessions.metrics.limitUnlimitedHint')
      : t('sessions.metrics.limitHint', {
        remaining: remainingDevices ?? 0,
      });

  async function runDeviceAction(
    kind: DeviceActionKind,
    action: () => Promise<void>,
  ) {
    if (actionLockRef.current) {
      return;
    }

    actionLockRef.current = kind;
    try {
      await action();
    } finally {
      actionLockRef.current = null;
    }
  }

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
            aria-label={t('common.refresh')}
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
            aria-label={t('common.logoutOthers')}
            disabled={logoutOthersMutation.isPending || remoteDeviceCount === 0}
            onClick={() => setLogoutOthersOpen(true)}
          >
            <LogOut className="mr-2 h-4 w-4" />
            {t('common.logoutOthers')}
          </Button>
          <Button
            magnetic={false}
            variant="ghost"
            aria-label={t('common.logoutAll')}
            disabled={logoutAllMutation.isPending || !hasDevices}
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
          value: String(deviceCount),
          hint: t('sessions.metrics.totalHint'),
          tone: deviceCount > 3 ? 'warning' : 'info',
        },
        {
          label: t('sessions.metrics.remote'),
          value: String(remoteDeviceCount),
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
          label: t('sessions.metrics.limit'),
          value: limitValue,
          hint: limitHint,
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
              <caption className="sr-only">{t('sessions.tableCaption')}</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.devices')}</TableHead>
                  <TableHead>{t('common.ipAddress')}</TableHead>
                  <TableHead>{t('common.lastUsed')}</TableHead>
                  <TableHead>{t('common.createdAt')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.map((device, index) => {
                  const isCurrentDevice = index === currentDeviceIndex;

                  return (
                    <TableRow key={getDeviceRowKey(device, index)}>
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
                              {isCurrentDevice ? (
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
                        {isCurrentDevice ? (
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
                            aria-label={t('common.logoutDevice')}
                            disabled={revokeMutation.isPending || !device.device_id}
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
                  );
                })}
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
              aria-label={t('common.logoutAll')}
              disabled={logoutAllMutation.isPending || !hasDevices}
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
          await runDeviceAction('logout-all', async () => {
            await logoutAllMutation.mutateAsync();
            setLogoutAllOpen(false);
          });
        }}
      />

      <AdminActionDialog
        isOpen={logoutOthersOpen}
        isPending={logoutOthersMutation.isPending}
        title={t('sessions.logoutOthersTitle')}
        description={t('sessions.logoutOthersConfirm', {
          count: remoteDeviceCount,
        })}
        confirmLabel={t('common.logoutOthers')}
        cancelLabel={t('common.cancel')}
        onClose={() => setLogoutOthersOpen(false)}
        onConfirm={async () => {
          await runDeviceAction('logout-others', async () => {
            await logoutOthersMutation.mutateAsync();
            setLogoutOthersOpen(false);
          });
        }}
      />

      <AdminActionDialog
        isOpen={Boolean(deviceToRevoke)}
        isPending={revokeMutation.isPending}
        title={t('sessions.revokeTitle')}
        description={t('sessions.revokeConfirm')}
        confirmLabel={t('common.logoutDevice')}
        cancelLabel={t('common.cancel')}
        subjectLabel={t('common.devices')}
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
          await runDeviceAction('revoke-device', async () => {
            await revokeMutation.mutateAsync(deviceToRevoke.device_id);
            setDeviceToRevoke(null);
          });
        }}
      />
    </SecurityPageShell>
  );
}
