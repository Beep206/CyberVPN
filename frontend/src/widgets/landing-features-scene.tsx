'use client';

import dynamic from 'next/dynamic';
import { usePathname } from 'next/navigation';

const FeaturesScene3D = dynamic(
  () => import('@/3d/scenes/FeaturesScene3D').then((mod) => mod.FeaturesScene3D),
  { ssr: false },
);

export function LandingFeaturesScene() {
  const pathname = usePathname();

  return <FeaturesScene3D key={pathname} activeFeature="quantum" />;
}
