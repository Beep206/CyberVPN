import { Suspense } from 'react';
import { OAuthCallbackClient } from './oauth-callback-client';

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={null}>
      <OAuthCallbackClient />
    </Suspense>
  );
}
