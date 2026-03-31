const SCROLL_LOCK_ATTRIBUTE = 'data-scroll-locked';

let activeScrollLocks = 0;
let originalBodyOverflow = '';
let originalDocumentOverflow = '';

function canUseDocument(): boolean {
  return typeof window !== 'undefined' && typeof document !== 'undefined';
}

function dispatchLenisEvent(name: 'lenis:start' | 'lenis:stop'): void {
  if (!canUseDocument()) {
    return;
  }

  window.dispatchEvent(new Event(name));
}

function applyDocumentScrollLock(): void {
  originalBodyOverflow = document.body.style.overflow;
  originalDocumentOverflow = document.documentElement.style.overflow;

  document.body.style.overflow = 'hidden';
  document.documentElement.style.overflow = 'hidden';
  document.body.setAttribute(SCROLL_LOCK_ATTRIBUTE, 'true');
  document.documentElement.setAttribute(SCROLL_LOCK_ATTRIBUTE, 'true');
  dispatchLenisEvent('lenis:stop');
}

function restoreDocumentScrollLock(): void {
  document.body.style.overflow = originalBodyOverflow;
  document.documentElement.style.overflow = originalDocumentOverflow;
  document.body.removeAttribute(SCROLL_LOCK_ATTRIBUTE);
  document.documentElement.removeAttribute(SCROLL_LOCK_ATTRIBUTE);

  originalBodyOverflow = '';
  originalDocumentOverflow = '';

  dispatchLenisEvent('lenis:start');
}

function releaseDocumentScroll(): void {
  if (!canUseDocument() || activeScrollLocks === 0) {
    return;
  }

  activeScrollLocks -= 1;

  if (activeScrollLocks === 0) {
    restoreDocumentScrollLock();
  }
}

export function lockDocumentScroll(): () => void {
  if (!canUseDocument()) {
    return () => {};
  }

  if (activeScrollLocks === 0) {
    applyDocumentScrollLock();
  }

  activeScrollLocks += 1;

  let released = false;

  return () => {
    if (released) {
      return;
    }

    released = true;
    releaseDocumentScroll();
  };
}

export function getActiveScrollLockCount(): number {
  return activeScrollLocks;
}

export function resetScrollLockForTests(): void {
  if (!canUseDocument()) {
    activeScrollLocks = 0;
    originalBodyOverflow = '';
    originalDocumentOverflow = '';
    return;
  }

  activeScrollLocks = 0;
  document.body.style.overflow = originalBodyOverflow;
  document.documentElement.style.overflow = originalDocumentOverflow;
  document.body.removeAttribute(SCROLL_LOCK_ATTRIBUTE);
  document.documentElement.removeAttribute(SCROLL_LOCK_ATTRIBUTE);
  originalBodyOverflow = '';
  originalDocumentOverflow = '';
}
