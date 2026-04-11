import type { ReactNode } from 'react';
import { InfrastructureSubnav } from '@/features/infrastructure/components/infrastructure-subnav';

export default function InfrastructureLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="space-y-6">
      <InfrastructureSubnav />
      {children}
    </div>
  );
}
