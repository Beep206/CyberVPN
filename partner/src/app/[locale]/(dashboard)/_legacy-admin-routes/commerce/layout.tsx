import type { ReactNode } from 'react';
import { CommerceSubnav } from '@/features/commerce/components/commerce-subnav';

export default function CommerceLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="space-y-6">
      <CommerceSubnav />
      {children}
    </div>
  );
}
