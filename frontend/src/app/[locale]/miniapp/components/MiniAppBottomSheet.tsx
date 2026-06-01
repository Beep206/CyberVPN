'use client';

import { motion, AnimatePresence, useReducedMotion } from 'motion/react';
import { X } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { lockDocumentScroll } from '@/shared/lib/scroll-lock';

interface MiniAppBottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  closeLabel?: string;
  children: React.ReactNode;
  colorScheme?: 'light' | 'dark';
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
    .filter((element) => element.getAttribute('aria-hidden') !== 'true');
}

/**
 * Reusable bottom sheet modal for Mini App
 * Telegram-styled sliding sheet with backdrop and header
 */
export function MiniAppBottomSheet({
  isOpen,
  onClose,
  title,
  closeLabel = 'Close',
  children,
}: MiniAppBottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement | null>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);
  const shouldReduceMotion = useReducedMotion();
  const sheetBg = 'miniapp-sheet';
  const borderColor = 'border';

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    return lockDocumentScroll();
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    previouslyFocusedElementRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    const focusTimeoutId = window.setTimeout(() => {
      const sheet = sheetRef.current;
      if (!sheet) {
        return;
      }

      const [firstFocusable] = getFocusableElements(sheet);
      (firstFocusable ?? sheet).focus();
    }, 0);

    const handleKeyDown = (event: KeyboardEvent) => {
      const sheet = sheetRef.current;
      if (!sheet) {
        return;
      }

      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== 'Tab') {
        return;
      }

      const focusableElements = getFocusableElements(sheet);
      if (focusableElements.length === 0) {
        event.preventDefault();
        sheet.focus();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements.at(-1);
      const activeElement = document.activeElement;

      if (!lastElement) {
        return;
      }

      if (event.shiftKey) {
        if (activeElement === firstElement || !sheet.contains(activeElement)) {
          event.preventDefault();
          lastElement.focus();
        }
        return;
      }

      if (activeElement === lastElement || !sheet.contains(activeElement)) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      window.clearTimeout(focusTimeoutId);
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocusedElementRef.current?.focus();
      previouslyFocusedElementRef.current = null;
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-50"
            aria-hidden="true"
          />

          {/* Bottom Sheet */}
          <motion.div
            ref={sheetRef}
            initial={shouldReduceMotion ? { opacity: 0 } : { y: '100%' }}
            animate={shouldReduceMotion ? { opacity: 1 } : { y: 0 }}
            exit={shouldReduceMotion ? { opacity: 0 } : { y: '100%' }}
            transition={
              shouldReduceMotion
                ? { duration: 0.01 }
                : { type: 'spring', damping: 30, stiffness: 300 }
            }
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            className={`fixed bottom-0 left-0 right-0 z-50 ${sheetBg} ${borderColor} border-t rounded-t-2xl max-h-[90vh] overflow-hidden flex flex-col pb-[var(--safe-area-bottom)] outline-none`}
          >
            {/* Header */}
            <div className={`flex items-center justify-between p-4 ${borderColor} border-b`}>
              <h2 className="text-lg font-display">{title}</h2>
              <button
                type="button"
                onClick={onClose}
                className="p-2 hover:bg-muted rounded-lg transition-colors touch-manipulation"
                aria-label={closeLabel}
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>

            {/* Content */}
            <div className="overflow-y-auto p-4 pb-[calc(1rem+var(--safe-area-bottom))] flex-1">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
