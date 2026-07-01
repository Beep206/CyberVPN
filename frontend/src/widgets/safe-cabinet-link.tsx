'use client';

import type { ComponentProps, MouseEvent, ReactNode } from 'react';
import { Link, usePathname } from '@/i18n/navigation';

type SafeCabinetLinkProps = Omit<ComponentProps<typeof Link>, 'href'> & {
  children: ReactNode;
  href: string;
};

function isPlainLeftClick(event: MouseEvent<HTMLAnchorElement>) {
  return (
    event.button === 0 &&
    !event.metaKey &&
    !event.altKey &&
    !event.ctrlKey &&
    !event.shiftKey
  );
}

function canUseDocumentFallback(anchor: HTMLAnchorElement) {
  return (
    process.env.NEXT_PUBLIC_SAFE_CABINET_LINK_FALLBACK === 'true' &&
    anchor.target !== '_blank' &&
    !anchor.hasAttribute('download') &&
    anchor.origin === window.location.origin
  );
}

export function SafeCabinetLink({
  children,
  href,
  onClick,
  ...props
}: SafeCabinetLinkProps) {
  const pathname = usePathname();

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(event);

    if (event.defaultPrevented || !isPlainLeftClick(event)) {
      return;
    }

    const anchor = event.currentTarget;
    if (!canUseDocumentFallback(anchor)) {
      return;
    }

    const before = pathname ?? window.location.pathname;
    window.setTimeout(() => {
      if (
        window.location.pathname === before &&
        anchor.href !== window.location.href
      ) {
        // eslint-disable-next-line no-console -- explicit opt-in navigation fallback diagnostic.
        console.info('[safe-cabinet-link] document navigation fallback', {
          hrefPath: anchor.pathname,
        });
        window.location.assign(anchor.href);
      }
    }, 400);
  };

  return (
    <Link href={href} onClick={handleClick} {...props}>
      {children}
    </Link>
  );
}
