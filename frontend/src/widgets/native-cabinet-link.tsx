'use client';

import type { ComponentProps, ReactNode } from 'react';
import { Link } from '@/i18n/navigation';

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
    <Link href={href} {...props}>
      {children}
    </Link>
  );
}
