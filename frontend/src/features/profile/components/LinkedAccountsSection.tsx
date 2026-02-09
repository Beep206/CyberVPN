'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Link2, Unlink, Send, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useUser } from '@/stores/auth-store';
import { authApi } from '@/lib/api/auth';
import type { TelegramWidgetData } from '@/types/telegram.d';
import { Modal } from '@/shared/ui/modal';

type LinkStatus = 'idle' | 'linking' | 'unlinking' | 'success' | 'error';

export function LinkedAccountsSection() {
  const t = useTranslations('Auth.profile');
  const user = useUser();
  const [status, setStatus] = useState<LinkStatus>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showUnlinkDialog, setShowUnlinkDialog] = useState(false);

  const isTelegramLinked = !!user?.telegram_id;
  // Check if user has alternative login methods (email/password)
  const hasAlternativeLogin = !!user?.email && user.is_email_verified;
  const canUnlink = isTelegramLinked && hasAlternativeLogin;

  const handleLinkTelegram = () => {
    // Load Telegram Login Widget callback
    window.TelegramLoginCallback = async (widgetData: TelegramWidgetData) => {
      setStatus('linking');
      setErrorMsg(null);
      setSuccessMsg(null);

      try {
        // Get authorize URL to obtain state token
        const redirectUri = `${window.location.origin}/settings`;
        const { data: authData } = await authApi.telegramLinkAuthorize(redirectUri);

        // Submit callback with state token
        await authApi.telegramLinkCallback({
          ...widgetData,
          state: authData.state,
        });

        setStatus('success');
        setSuccessMsg(t('linkSuccess'));
        // Reload user data to reflect the linked account
        window.location.reload();
      } catch (error: unknown) {
        setStatus('error');
        const axiosError = error as { response?: { data?: { detail?: string } } };
        setErrorMsg(axiosError?.response?.data?.detail ?? 'Failed to link Telegram');
      }
    };

    // Create and inject Telegram widget script
    const container = document.getElementById('telegram-widget-container');
    if (!container) return;

    // Clear previous widget
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.async = true;
    script.setAttribute('data-telegram-login', process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? 'CyberVPNBot');
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-radius', '8');
    script.setAttribute('data-onauth', 'TelegramLoginCallback(user)');
    script.setAttribute('data-request-access', 'write');
    container.appendChild(script);
  };

  const handleUnlinkTelegram = async () => {
    setShowUnlinkDialog(false);
    setStatus('unlinking');
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await authApi.unlinkProvider('telegram');
      setStatus('success');
      setSuccessMsg(t('unlinkSuccess'));
      // Reload user data to reflect the unlinked account
      window.location.reload();
    } catch (error: unknown) {
      setStatus('error');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      setErrorMsg(axiosError?.response?.data?.detail ?? 'Failed to unlink Telegram');
    }
  };

  const isProcessing = status === 'linking' || status === 'unlinking';

  return (
    <section className="relative border border-neon-cyan/30 bg-terminal-surface/50 rounded-lg overflow-hidden">
      {/* Section Header */}
      <div className="flex items-center gap-2 p-4 border-b border-grid-line/30">
        <Link2 className="w-5 h-5 text-neon-cyan" />
        <h2 className="text-lg font-display text-neon-cyan tracking-wider">
          {t('linkedAccounts')}
        </h2>
      </div>

      {/* Provider List */}
      <div className="p-4 space-y-3">
        {/* Telegram Provider (always first, highlighted) */}
        <div className="flex items-center justify-between p-3 rounded-md border border-neon-cyan/20 bg-terminal-bg/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#2AABEE]/20 flex items-center justify-center">
              <Send className="w-5 h-5 text-[#2AABEE]" />
            </div>
            <div>
              <span className="text-foreground font-medium">Telegram</span>
              {isTelegramLinked && (
                <p className="text-sm text-neon-cyan/70">
                  {t('telegramLinked', { username: String(user?.telegram_id ?? '') })}
                </p>
              )}
              {!isTelegramLinked && (
                <p className="text-sm text-grid-line">Not linked</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isProcessing && (
              <Loader2 className="w-4 h-4 text-neon-cyan animate-spin" />
            )}

            {!isTelegramLinked && !isProcessing && (
              <button
                onClick={handleLinkTelegram}
                className="px-4 py-2 text-sm font-medium text-terminal-bg bg-neon-cyan rounded-md hover:bg-neon-cyan/90 transition-colors"
                aria-label={t('linkTelegram')}
              >
                {t('linkTelegram')}
              </button>
            )}

            {isTelegramLinked && !isProcessing && (
              <button
                onClick={() => canUnlink ? setShowUnlinkDialog(true) : undefined}
                disabled={!canUnlink}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  canUnlink
                    ? 'text-neon-pink border border-neon-pink/50 hover:bg-neon-pink/10'
                    : 'text-grid-line/50 border border-grid-line/20 cursor-not-allowed'
                }`}
                title={!canUnlink ? t('cantUnlinkOnly') : undefined}
                aria-label={t('unlinkTelegram')}
              >
                <span className="flex items-center gap-1.5">
                  <Unlink className="w-3.5 h-3.5" />
                  {t('unlinkTelegram')}
                </span>
              </button>
            )}
          </div>
        </div>

        {/* Cannot unlink message */}
        {isTelegramLinked && !canUnlink && (
          <p className="text-xs text-amber-400/80 px-1">
            {t('cantUnlinkOnly')}
          </p>
        )}

        {/* Telegram widget container (hidden until link button is clicked) */}
        <div id="telegram-widget-container" className="flex justify-center" />
      </div>

      {/* Status Messages */}
      <AnimatePresence>
        {(successMsg || errorMsg) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-4 pb-4"
          >
            {successMsg && (
              <div className="p-3 rounded-md border border-matrix-green/30 bg-matrix-green/10 text-matrix-green text-sm">
                {successMsg}
              </div>
            )}
            {errorMsg && (
              <div className="p-3 rounded-md border border-neon-pink/30 bg-neon-pink/10 text-neon-pink text-sm">
                {errorMsg}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Unlink Confirmation Dialog */}
      <Modal
        isOpen={showUnlinkDialog}
        onClose={() => setShowUnlinkDialog(false)}
        title="CONFIRM_UNLINK"
      >
        <div className="space-y-4">
          <p className="text-foreground">{t('unlinkConfirm')}</p>
          <div className="flex gap-3 justify-end">
            <button
              onClick={() => setShowUnlinkDialog(false)}
              className="px-4 py-2 text-sm text-grid-line border border-grid-line/30 rounded-md hover:bg-terminal-surface/50 transition-colors"
              aria-label="Cancel"
            >
              Cancel
            </button>
            <button
              onClick={handleUnlinkTelegram}
              className="px-4 py-2 text-sm text-terminal-bg bg-neon-pink rounded-md hover:bg-neon-pink/90 transition-colors"
              aria-label={t('unlinkTelegram')}
            >
              {t('unlinkTelegram')}
            </button>
          </div>
        </div>
      </Modal>

      {/* Corner decorations */}
      <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-neon-cyan/50" />
      <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-neon-cyan/50" />
      <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-neon-cyan/50" />
      <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-neon-cyan/50" />
    </section>
  );
}
