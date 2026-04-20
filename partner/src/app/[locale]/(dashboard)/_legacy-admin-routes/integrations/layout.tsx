import type { ReactNode } from 'react';
import { IntegrationsSubnav } from '@/features/integrations/components/integrations-subnav';

export default function IntegrationsLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="space-y-6">
      <IntegrationsSubnav />
      {children}
    </div>
  );
}
