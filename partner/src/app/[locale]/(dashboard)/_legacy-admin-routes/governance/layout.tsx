import type { ReactNode } from 'react';
import { GovernanceSubnav } from '@/features/governance/components/governance-subnav';

export default function GovernanceLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="space-y-6">
      <GovernanceSubnav />
      {children}
    </div>
  );
}
