'use client';

import dynamic from 'next/dynamic';

const FeaturesScene3D = dynamic(
  () => import('@/3d/scenes/FeaturesScene3D').then((mod) => mod.FeaturesScene3D),
  { ssr: false },
);

export function LandingFeaturesScene() {
  return <FeaturesScene3D activeFeature="quantum" />;
}
