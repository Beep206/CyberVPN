'use client';

import { useAuthStore } from '@/stores/auth-store';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import clsx from 'clsx';
import { useTranslations } from 'next-intl';

interface TelegramLoginButtonProps {
  botUsername: string; // Keep interface for backward compatibility
  buttonSize?: 'large' | 'medium' | 'small';
  cornerRadius?: number;
  showUserPhoto?: boolean;
  className?: string;
}

export function TelegramLoginButton({
  className,
}: TelegramLoginButtonProps) {
  const telegramMagicLinkAuth = useAuthStore((s) => s.telegramMagicLinkAuth);
  const isLoading = useAuthStore((s) => s.isLoading);
  const user = useAuthStore((s) => s.user);

  // We might not have translations locally if called from certain places, 
  // but let's try (assuming next-intl is available for the "Auth" namespace or common)
  // If not, we can hardcode for fallback.
  // Actually, we'd probably use standard text like "Войти через Telegram"
  
  const handleTelegramClick = async () => {
    try {
      await telegramMagicLinkAuth();
    } catch (error) {
      console.error('Magic link auth failed:', error);
    }
  };

  const t = useTranslations('Auth');

  if (user) return null; // hide if logged in

  return (
    <Button
      variant="outline"
      size="lg"
      className={clsx('w-full flex gap-2', className)}
      onClick={handleTelegramClick}
      disabled={isLoading}
      type="button"
    >
      {isLoading ? (
        <Loader2 className="h-5 w-5 animate-spin" />
      ) : (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          fill="none"
          viewBox="0 0 24 24"
        >
          <path
            fill="#2AABEE"
            d="M12 24c6.627 0 12-5.373 12-12S18.627 0 12 0 0 5.373 0 12s5.373 12 12 12Z"
          />
          <path
            fill="#fff"
            d="m5.44 11.516 11.697-4.502c.542-.204 1.018.12.846.953l-1.996 9.403c-.143.642-.524.8-1.054.5l-2.915-2.149-1.406 1.355c-.156.155-.286.285-.586.285l.208-2.973 5.421-4.897c.236-.21-.051-.326-.367-.116L6.58 13.918l-2.887-.905c-.628-.195-.64-.627.13-.93l1.617-.567Z"
          />
        </svg>
      )}
      {t('continue-with-telegram')}
    </Button>
  );
}
