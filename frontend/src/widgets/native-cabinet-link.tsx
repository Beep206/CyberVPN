'use client';

import type { ComponentProps, ReactNode } from 'react';
import { Link } from '@/i18n/navigation';
import { SafeCabinetLink } from '@/widgets/safe-cabinet-link';

type NativeCabinetLinkProps = Omit<ComponentProps<typeof Link>, 'href'> & {
  children: ReactNode;
  href: string;
};

export function NativeCabinetLink({
  children,
  href,
  ...props
}: NativeCabinetLinkProps) {
  return (
    <SafeCabinetLink href={href} {...props}>
      {children}
    </SafeCabinetLink>
  );
}
