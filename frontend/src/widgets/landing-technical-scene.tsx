'use client';

import dynamic from 'next/dynamic';
import { usePathname } from 'next/navigation';

const AntiDPIScene3D = dynamic(() => import('@/3d/scenes/AntiDPIScene3D'), {
  ssr: false,
});

export function LandingTechnicalScene() {
  const pathname = usePathname();

  return <AntiDPIScene3D key={pathname} />;
}
