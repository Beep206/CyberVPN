'use client';

import dynamic from 'next/dynamic';
import { usePathname } from 'next/navigation';

const FastTrackScene3D = dynamic(() => import('@/3d/scenes/FastTrackScene3D'), {
  ssr: false,
});

export function QuickStartScene() {
  const pathname = usePathname();

  return <FastTrackScene3D key={pathname} />;
}
