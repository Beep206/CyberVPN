'use client';

import dynamic from 'next/dynamic';

const FastTrackScene3D = dynamic(() => import('@/3d/scenes/FastTrackScene3D'), {
  ssr: false,
});

export function QuickStartScene() {
  return <FastTrackScene3D />;
}
