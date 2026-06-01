'use client';

import { AdminSecondaryNav } from '@/features/admin-shell/components/admin-secondary-nav';

export function CommerceSubnav() {
  return (
    <AdminSecondaryNav
      groupId="commerce"
      className="min-w-0 max-w-full overflow-x-auto overscroll-x-contain"
    />
  );
}
