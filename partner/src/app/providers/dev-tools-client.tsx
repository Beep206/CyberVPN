'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { DevToolsBootstrap } from '@/app/providers/dev-tools-bootstrap';
import { DevButton } from '@/features/dev/dev-button';

const LazyDevPanel = dynamic(
  () => import('@/features/dev/dev-panel').then((module) => module.DevPanel),
  {
    ssr: false,
  },
);

export function DevToolsClient() {
  const [isPanelEnabled, setPanelEnabled] = useState(false);

  return (
    <>
      <DevToolsBootstrap />
      {isPanelEnabled ? (
        <LazyDevPanel defaultOpen />
      ) : (
        <DevButton onClick={() => setPanelEnabled(true)} />
      )}
    </>
  );
}
