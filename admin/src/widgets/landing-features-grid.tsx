'use client';

import { EyeOff, Globe, Infinity as InfinityIcon, Layers, Shield, Zap } from 'lucide-react';
import { FeatureCard3D } from '@/shared/ui/feature-card-3d';

const ICON_MAP = {
  backbone: Zap,
  multiplatform: Layers,
  protocols: InfinityIcon,
  ram: Shield,
  routing: Globe,
  stealth: EyeOff,
} as const;

interface LandingFeatureItem {
  bgColor: string;
  colSpan: string;
  color: string;
  description: string;
  iconKey: keyof typeof ICON_MAP;
  id: string;
  title: string;
}

interface LandingFeaturesGridProps {
  features: LandingFeatureItem[];
}

export function LandingFeaturesGrid({ features }: LandingFeaturesGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16 items-stretch">
      {features.map((feature, index) => (
        <FeatureCard3D
          key={feature.id}
          icon={ICON_MAP[feature.iconKey]}
          title={feature.title}
          description={feature.description}
          color={feature.color}
          bgColor={feature.bgColor}
          index={index}
          colSpan={feature.colSpan}
        />
      ))}
    </div>
  );
}
