'use client';

import type { ComponentProps, MouseEvent, ReactNode } from 'react';
import { Link } from '@/i18n/navigation';

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
    (!anchor.target || anchor.target === '_self') &&
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
  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(event);

    if (event.defaultPrevented || !isPlainLeftClick(event)) {
      return;
    }

    const anchor = event.currentTarget;
    if (!canUseDocumentFallback(anchor)) {
      return;
    }

    const before = window.location.pathname;
    window.setTimeout(() => {
      if (
        window.location.pathname === before &&
        anchor.href !== window.location.href
      ) {
        // eslint-disable-next-line no-console -- rare production navigation fallback diagnostic.
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
