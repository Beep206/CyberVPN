'use client';

import { useEffect, useRef } from 'react';
import { useAuthStore } from '@/stores/auth-store';
import type { TelegramWidgetData } from '@/types/telegram.d';

interface TelegramLoginButtonProps {
  botUsername: string;
  buttonSize?: 'large' | 'medium' | 'small';
  cornerRadius?: number;
  showUserPhoto?: boolean;
  className?: string;
}

export function TelegramLoginButton({
  botUsername,
  buttonSize = 'large',
  cornerRadius = 8,
  showUserPhoto = true,
  className,
}: TelegramLoginButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const telegramAuth = useAuthStore((s) => s.telegramAuth);
  const isLoading = useAuthStore((s) => s.isLoading);

  useEffect(() => {
    // Define global callback
    window.TelegramLoginCallback = async (user: TelegramWidgetData) => {
      try {
        await telegramAuth(user);
      } catch (error) {
        console.error('Telegram auth failed:', error);
      }
    };

    // Load Telegram widget script
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.async = true;
    script.setAttribute('data-telegram-login', botUsername);
    script.setAttribute('data-size', buttonSize);
    script.setAttribute('data-radius', String(cornerRadius));
    script.setAttribute('data-onauth', 'TelegramLoginCallback(user)');
    script.setAttribute('data-request-access', 'write');
    if (showUserPhoto) {
      script.setAttribute('data-userpic', 'true');
    }

    const container = containerRef.current;
    if (container) {
      // Clear previous content safely
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
      container.appendChild(script);
    }

    // Cleanup on unmount
    return () => {
      delete window.TelegramLoginCallback;
      if (container) {
        while (container.firstChild) {
          container.removeChild(container.firstChild);
        }
      }
    };
  }, [botUsername, buttonSize, cornerRadius, showUserPhoto, telegramAuth]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ opacity: isLoading ? 0.5 : 1 }}
      aria-label="Sign in with Telegram"
    />
  );
}
