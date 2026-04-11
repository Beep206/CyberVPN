'use client';

import dynamic from 'next/dynamic';

const AntiDPIScene3D = dynamic(() => import('@/3d/scenes/AntiDPIScene3D'), {
  ssr: false,
});

export function LandingTechnicalScene() {
  return <AntiDPIScene3D />;
}
