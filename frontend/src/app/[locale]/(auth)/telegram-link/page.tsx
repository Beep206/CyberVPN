import { Suspense } from 'react';
import { TelegramLinkClient } from './telegram-link-client';

export default function TelegramLinkPage() {
  return (
    <Suspense fallback={null}>
      <TelegramLinkClient />
    </Suspense>
  );
}
