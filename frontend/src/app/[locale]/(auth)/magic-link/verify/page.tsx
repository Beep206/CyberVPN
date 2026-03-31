import { Suspense } from 'react';
import { MagicLinkVerifyClient } from './magic-link-verify-client';

export default function MagicLinkVerifyPage() {
  return (
    <Suspense fallback={null}>
      <MagicLinkVerifyClient />
    </Suspense>
  );
}
