'use client';

import { useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';

/**
 * Blank page for rendering Telegram Widget safely away from main React DOM.
 * The widget will redirect postMessage to opener after successful login.
 */
export default function TelegramWidgetPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();
  const botUsername = searchParams.get('bot') || process.env.NEXT_PUBLIC_TELEGRAM_BOT_NAME || '';

  useEffect(() => {
    if (!containerRef.current || !botUsername) return;

    // Set callback globally
    window.TelegramLoginCallback = (user: unknown) => {
      if (window.opener) {
        window.opener.postMessage({ type: 'TELEGRAM_AUTH_SUCCESS', payload: user }, window.location.origin);
      }
    };

    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.async = true;
    script.setAttribute('data-telegram-login', botUsername);
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-request-access', 'write');
    script.setAttribute('data-onauth', 'TelegramLoginCallback(user)');

    const container = containerRef.current;

    container.replaceChildren(script);

    return () => {
      // Cleanup global callback
      delete window.TelegramLoginCallback;
      container.replaceChildren();
    };
  }, [botUsername]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#09090b', color: '#fff' }}>
      {!botUsername ? (
        <p>Error: Bot username not configured.</p>
      ) : (
        <div ref={containerRef} />
      )}
    </div>
  );
}
