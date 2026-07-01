'use client';

import type {
  AnchorHTMLAttributes,
  MouseEvent,
  ReactNode,
} from 'react';
import { useRouter } from 'next/navigation';
import { useLocale } from 'next-intl';
import { defaultLocale, locales } from '@/i18n/config';
import { toLocalizedPath } from '@/shared/lib/seo-route-policy';

const SPA_NAVIGATION_FALLBACK_DELAY_MS = 10_000;

type Locale = (typeof locales)[number];

type NativeCabinetLinkProps = Omit<
  AnchorHTMLAttributes<HTMLAnchorElement>,
  'href'
> & {
  children: ReactNode;
  href: string;
};

function resolveLocale(locale: string): Locale {
  return locales.includes(locale as Locale) ? (locale as Locale) : defaultLocale;
}

function isPlainPrimaryClick(event: MouseEvent<HTMLAnchorElement>): boolean {
  return (
    event.button === 0 &&
    !event.altKey &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.shiftKey
  );
}

function isSameWindowTarget(target: string | undefined): boolean {
  return !target || target === '_self';
}

export function NativeCabinetLink({
  children,
  href,
  onClick,
  target,
  ...props
}: NativeCabinetLinkProps) {
  const router = useRouter();
  const locale = resolveLocale(useLocale());
  const localizedHref = toLocalizedPath(locale, href);

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    const targetHref = event.currentTarget.href;

    onClick?.(event);

    if (
      event.defaultPrevented ||
      !isPlainPrimaryClick(event) ||
      !isSameWindowTarget(target)
    ) {
      return;
    }

    event.preventDefault();

    if (window.location.href === targetHref) {
      return;
    }

    router.push(localizedHref);

    window.setTimeout(() => {
      if (window.location.href !== targetHref) {
        window.location.assign(targetHref);
      }
    }, SPA_NAVIGATION_FALLBACK_DELAY_MS);
  };

  return (
    <a href={localizedHref} onClick={handleClick} target={target} {...props}>
      {children}
    </a>
  );
}
