'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { authApi } from '@/lib/api/auth';
import { motion } from 'motion/react';
import { Smartphone, Monitor, Laptop, Trash2, AlertCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { AxiosError } from 'axios';

export function DevicesSection() {
  const t = useTranslations('Settings');

  const [loggingOut, setLoggingOut] = useState<string | null>(null);
  const [error, setError] = useState('');

  // Fetch devices
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['devices'],
    queryFn: async () => {
      const response = await authApi.listDevices();
      return response.data;
    },
    staleTime: 1 * 60 * 1000,
  });

  // Get device icon based on user agent
  const getDeviceIcon = (userAgent: string) => {
    const ua = userAgent.toLowerCase();
    if (ua.includes('mobile') || ua.includes('android') || ua.includes('iphone')) {
      return Smartphone;
    }
    if (ua.includes('tablet') || ua.includes('ipad')) {
      return Monitor;
    }
    return Laptop;
  };

  // Parse user agent for display
  const parseUserAgent = (ua: string): string => {
    // Simple parsing - extract browser and OS
    const parts = ua.split(' ');
    const browser = parts.find(p => p.includes('Chrome') || p.includes('Firefox') || p.includes('Safari') || p.includes('Edge'));
    const os = parts.find(p => p.includes('Windows') || p.includes('Mac') || p.includes('Linux') || p.includes('Android') || p.includes('iOS'));

    if (browser && os) {
      return `${browser.split('/')[0]} on ${os.split('/')[0]}`;
    }
    return ua.substring(0, 50) + (ua.length > 50 ? '...' : '');
  };

  // Handle device logout
  const handleLogout = async (deviceId: string) => {
    setLoggingOut(deviceId);
    setError('');

    try {
      await authApi.logoutDevice(deviceId);
      await refetch();
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to logout device');
      } else {
        setError('An error occurred');
      }
    } finally {
      setLoggingOut(null);
    }
  };

  // Handle logout all other devices
  const handleLogoutAllOthers = async () => {
    if (!data?.devices) return;

    const otherDevices = data.devices.filter(d => !d.is_current);
    if (otherDevices.length === 0) return;

    setError('');

    try {
      await Promise.all(otherDevices.map(d => authApi.logoutDevice(d.device_id)));
      await refetch();
    } catch {
      setError('Failed to logout some devices');
    }
  };

  if (isLoading) {
    return (
      <section className="cyber-card p-6 animate-pulse">
        <div className="h-6 bg-grid-line/30 rounded w-1/4 mb-4" />
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-20 bg-grid-line/20 rounded" />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-display text-neon-purple pl-2 border-l-4 border-neon-purple">
          {t('devices') || 'Active Devices'}
        </h2>

        {data?.devices && data.devices.length > 1 && (
          <button
            onClick={handleLogoutAllOthers}
            className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400 font-mono text-sm rounded transition-colors"
          >
            Logout All Others
          </button>
        )}
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded text-red-500 text-sm font-mono flex items-center gap-2"
        >
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </motion.div>
      )}

      <div className="space-y-3">
        {data?.devices && data.devices.length > 0 ? (
          data.devices.map((device, i) => {
            const Icon = getDeviceIcon(device.user_agent);

            return (
              <motion.div
                key={device.device_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className={`cyber-card p-4 ${
                  device.is_current
                    ? 'border-matrix-green shadow-[0_0_15px_rgba(0,255,136,0.2)]'
                    : 'border-grid-line/30'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1">
                    <div className={`p-3 rounded-lg ${
                      device.is_current
                        ? 'bg-matrix-green/10 border border-matrix-green/30'
                        : 'bg-neon-cyan/10 border border-neon-cyan/30'
                    }`}>
                      <Icon className={`h-5 w-5 ${
                        device.is_current ? 'text-matrix-green' : 'text-neon-cyan'
                      }`} />
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-mono text-sm text-foreground">
                          {parseUserAgent(device.user_agent)}
                        </h3>
                        {device.is_current && (
                          <span className="px-2 py-0.5 bg-matrix-green/20 text-matrix-green text-xs font-mono rounded">
                            Current
                          </span>
                        )}
                      </div>

                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground font-mono">
                          IP: {device.ip_address}
                        </p>
                        <p className="text-xs text-muted-foreground font-mono">
                          Last active: {new Date(device.last_used_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>

                  {!device.is_current && (
                    <button
                      onClick={() => handleLogout(device.device_id)}
                      disabled={loggingOut === device.device_id}
                      className="p-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="Logout device"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })
        ) : (
          <div className="cyber-card p-8 text-center">
            <p className="text-muted-foreground font-mono">
              No active devices found
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
