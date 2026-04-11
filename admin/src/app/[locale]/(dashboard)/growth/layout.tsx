import type { ReactNode } from 'react';
import { GrowthSubnav } from '@/features/growth/components/growth-subnav';

export default function GrowthLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="space-y-6">
      <GrowthSubnav />
      {children}
    </div>
  );
}
