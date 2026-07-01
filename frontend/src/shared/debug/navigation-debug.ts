'use client';

type NavigationDebugSnapshot = {
  button?: number;
  defaultPrevented: boolean;
  hrefPath: string | null;
  pointClass: string | null;
  pointTag: string | null;
  targetTag: string | null;
  type: string;
  viewportPath: string;
};

function getSafePath(anchor: HTMLAnchorElement | null): string | null {
  if (!anchor) {
    return null;
  }

  return anchor.pathname || null;
}

function getElementClassName(element: Element | null): string | null {
  const className = element?.getAttribute('class');
  return className ? className.slice(0, 240) : null;
}

function snapshotNavigationEvent(
  event: MouseEvent | PointerEvent,
): NavigationDebugSnapshot {
  const target = event.target instanceof Element ? event.target : null;
  const anchor = target?.closest('a[href]') as HTMLAnchorElement | null;
  const pointTarget = document.elementFromPoint(event.clientX, event.clientY);

  return {
    button: 'button' in event ? event.button : undefined,
    defaultPrevented: event.defaultPrevented,
    hrefPath: getSafePath(anchor),
    pointClass: getElementClassName(pointTarget),
    pointTag: pointTarget?.tagName ?? null,
    targetTag: target?.tagName ?? null,
    type: event.type,
    viewportPath: window.location.pathname,
  };
}

export function installNavigationDebugLogger() {
  if (process.env.NEXT_PUBLIC_NAV_DEBUG !== 'true') {
    return () => {};
  }

  if (typeof document === 'undefined') {
    return () => {};
  }

  const handler = (event: MouseEvent | PointerEvent) => {
    // eslint-disable-next-line no-console -- explicit NEXT_PUBLIC_NAV_DEBUG diagnostic output.
    console.debug('[nav-debug]', snapshotNavigationEvent(event));
  };

  document.addEventListener('pointerdown', handler, true);
  document.addEventListener('click', handler, true);

  return () => {
    document.removeEventListener('pointerdown', handler, true);
    document.removeEventListener('click', handler, true);
  };
}
