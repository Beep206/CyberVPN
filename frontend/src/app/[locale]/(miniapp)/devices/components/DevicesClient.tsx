'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/lib/api';
import { motion } from 'motion/react';
import { Smartphone, Monitor, Tablet, LogOut, CheckCircle, XCircle } from 'lucide-react';
import { useState } from 'react';

/**
 * Devices Client Component
 * Displays list of active devices/sessions with remote logout functionality
 */
export function DevicesClient() {
  const queryClient = useQueryClient();
  const [logoutError, setLogoutError] = useState<string | null>(null);

  // Fetch active devices
  const { data: devicesData, isLoading } = useQuery({
    queryKey: ['active-devices'],
    queryFn: async () => {
      const response = await authApi.listDevices();
      return response.data;
    },
    staleTime: 30 * 1000,
  });

  // Logout device mutation
  const logoutMutation = useMutation({
    mutationFn: (deviceId: string) => authApi.logoutDevice(deviceId),
    onSuccess: () => {
      // Refetch devices after logout
      queryClient.invalidateQueries({ queryKey: ['active-devices'] });
      setLogoutError(null);
    },
    onError: (error: any) => {
      setLogoutError(error.response?.data?.detail || 'Failed to logout device');
    },
  });

  const getDeviceIcon = (userAgent: string) => {
    const ua = userAgent.toLowerCase();
    if (ua.includes('mobile') || ua.includes('android') || ua.includes('iphone')) {
      return <Smartphone className="h-5 w-5 text-neon-cyan" />;
    }
    if (ua.includes('tablet') || ua.includes('ipad')) {
      return <Tablet className="h-5 w-5 text-neon-purple" />;
    }
    return <Monitor className="h-5 w-5 text-matrix-green" />;
  };

  const parseUserAgent = (userAgent: string) => {
    // Simple UA parsing - extract browser and OS
    const browsers = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera'];
    const os = ['Windows', 'Mac', 'Linux', 'Android', 'iOS'];

    let browser = 'Unknown Browser';
    let operatingSystem = 'Unknown OS';

    for (const b of browsers) {
      if (userAgent.includes(b)) {
        browser = b;
        break;
      }
    }

    for (const o of os) {
      if (userAgent.includes(o)) {
        operatingSystem = o;
        break;
      }
    }

    return { browser, operatingSystem };
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-neon-cyan" />
      </div>
    );
  }

  const devices = devicesData?.devices || [];

  if (devices.length === 0) {
    return (
      <div className="cyber-card p-8 text-center">
        <p className="text-muted-foreground">No active devices found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {logoutError && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="cyber-card p-4 border-red-500/50 bg-red-500/10"
        >
          <div className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-500" />
            <p className="text-sm text-red-500">{logoutError}</p>
          </div>
        </motion.div>
      )}

      {devices.map((device, index) => {
        const { browser, operatingSystem } = parseUserAgent(device.user_agent);
        const lastUsed = new Date(device.last_used_at);
        const isRecent = Date.now() - lastUsed.getTime() < 5 * 60 * 1000; // Active in last 5 min

        return (
          <motion.div
            key={device.device_id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`cyber-card p-4 ${
              device.is_current
                ? 'border-matrix-green/50 bg-matrix-green/5'
                : 'border-grid-line/30'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <div className="mt-1">{getDeviceIcon(device.user_agent)}</div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-mono text-foreground truncate">
                      {browser} on {operatingSystem}
                    </h3>
                    {device.is_current && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-matrix-green/20 border border-matrix-green/30 rounded text-xs text-matrix-green">
                        <CheckCircle className="h-3 w-3" />
                        Current
                      </span>
                    )}
                    {isRecent && !device.is_current && (
                      <span className="inline-flex h-2 w-2 rounded-full bg-neon-cyan animate-pulse" />
                    )}
                  </div>

                  <div className="space-y-1 text-xs text-muted-foreground">
                    <p className="truncate">IP: {device.ip_address}</p>
                    <p>
                      Last active:{' '}
                      {lastUsed.toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>
              </div>

              {!device.is_current && (
                <button
                  onClick={() => logoutMutation.mutate(device.device_id)}
                  disabled={logoutMutation.isPending}
                  className="flex items-center gap-2 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 hover:border-red-500/50 text-red-500 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Logout this device"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="text-xs font-mono hidden sm:inline">Logout</span>
                </button>
              )}
            </div>
          </motion.div>
        );
      })}

      <div className="cyber-card p-4 bg-terminal-surface/50">
        <p className="text-xs text-muted-foreground">
          <strong>Security tip:</strong> If you see a device you don't recognize, logout that
          device immediately and change your password.
        </p>
      </div>
    </div>
  );
}
