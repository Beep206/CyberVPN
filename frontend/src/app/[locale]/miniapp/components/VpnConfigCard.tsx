'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { subscriptionsApi } from '@/lib/api';
import { useAuthStore } from '@/stores/auth-store';
import { motion } from 'motion/react';
import {
  Download,
  Copy,
  QrCode,
  ExternalLink,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';
import { MiniAppBottomSheet } from './MiniAppBottomSheet';
import QRCodeComponent from 'react-qr-code';

interface VpnConfigCardProps {
  colorScheme?: 'light' | 'dark';
}

/**
 * VPN Config card component
 * Displays VPN configuration with copy, QR code, and deep link actions
 */
export function VpnConfigCard({ colorScheme = 'dark' }: VpnConfigCardProps) {
  const t = useTranslations('MiniApp.home');
  const { haptic, webApp } = useTelegramWebApp();
  const user = useAuthStore((s) => s.user);
  const [qrSheetOpen, setQrSheetOpen] = useState(false);

  // Fetch VPN config
  const { data: configData, isLoading, isError } = useQuery({
    queryKey: ['vpn-config', user?.id],
    queryFn: async () => {
      if (!user?.id) return null;
      const { data } = await subscriptionsApi.getConfig(user.id);
      return data;
    },
    enabled: !!user?.id,
  });

  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  const copyConfig = async () => {
    haptic('medium');
    if (configData?.config) {
      try {
        await navigator.clipboard.writeText(configData.config);
        webApp?.showAlert(t('configCopied'));
      } catch {
        webApp?.showAlert('Failed to copy config');
      }
    }
  };

  const openInApp = () => {
    haptic('medium');
    // Use subscriptionUrl if available, otherwise use config
    const linkUrl = configData?.subscriptionUrl || configData?.config;
    if (linkUrl) {
      // Try to open in mobile VPN app via deep link
      webApp?.openLink(linkUrl);
    }
  };

  const showQRCode = () => {
    haptic('medium');
    setQrSheetOpen(true);
  };

  if (isLoading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-neon-cyan" />
        </div>
      </motion.div>
    );
  }

  if (isError || !configData) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-display text-sm mb-1">{t('noConfigAvailable')}</h3>
            <p className="text-xs text-muted-foreground font-mono">{t('noConfigDescription')}</p>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-center gap-2 mb-3">
          <Download className="h-5 w-5 text-neon-cyan" />
          <h3 className="font-display text-sm">{t('vpnConfigTitle')}</h3>
        </div>

        <p className="text-xs text-muted-foreground font-mono mb-4">
          {t('vpnConfigDescription')}
        </p>

        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={copyConfig}
            className="py-2 px-3 bg-neon-cyan text-black rounded-lg hover:bg-neon-cyan/90 transition-colors touch-manipulation flex flex-col items-center justify-center gap-1"
          >
            <Copy className="h-4 w-4" />
            <span className="text-xs font-mono">{t('copyConfig')}</span>
          </button>

          <button
            onClick={showQRCode}
            className="py-2 px-3 bg-neon-purple text-white rounded-lg hover:bg-neon-purple/90 transition-colors touch-manipulation flex flex-col items-center justify-center gap-1"
          >
            <QrCode className="h-4 w-4" />
            <span className="text-xs font-mono">{t('viewQR')}</span>
          </button>

          <button
            onClick={openInApp}
            className="py-2 px-3 bg-muted border border-border rounded-lg hover:bg-muted/70 transition-colors touch-manipulation flex flex-col items-center justify-center gap-1"
          >
            <ExternalLink className="h-4 w-4" />
            <span className="text-xs font-mono">{t('openInApp')}</span>
          </button>
        </div>
      </motion.div>

      {/* QR Code Bottom Sheet */}
      <MiniAppBottomSheet
        isOpen={qrSheetOpen}
        onClose={() => setQrSheetOpen(false)}
        title={t('configQRTitle')}
        colorScheme={colorScheme}
      >
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground font-mono text-center">
            {t('configQRDescription')}
          </p>

          {configData?.config && (
            <div className="flex justify-center p-6 bg-white rounded-lg">
              <QRCodeComponent
                value={configData.config}
                size={250}
                level="M"
                fgColor="#000000"
                bgColor="#FFFFFF"
              />
            </div>
          )}
        </div>
      </MiniAppBottomSheet>
    </>
  );
}
