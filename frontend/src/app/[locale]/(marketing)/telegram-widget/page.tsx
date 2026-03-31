import { Suspense } from 'react';
import { TelegramWidgetClient } from './telegram-widget-client';

function TelegramWidgetFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-terminal-bg px-6 text-foreground">
      <p className="font-mono text-xs uppercase tracking-[0.32em] text-muted-foreground">
        Initializing Telegram widget...
      </p>
    </div>
  );
}

export default function TelegramWidgetPage() {
  return (
    <Suspense fallback={<TelegramWidgetFallback />}>
      <TelegramWidgetClient />
    </Suspense>
  );
}
