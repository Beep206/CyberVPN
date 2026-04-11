import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type ResponsiveSplitShellVisualMode = 'column' | 'background';
type ResponsiveSplitShellMobileOrder = 'before-content' | 'after-content';

interface ResponsiveSplitShellProps {
  header?: ReactNode;
  content: ReactNode;
  visual?: ReactNode;
  visualMode?: ResponsiveSplitShellVisualMode;
  mobileVisualOrder?: ResponsiveSplitShellMobileOrder;
  pinVisualOnDesktop?: boolean;
  safeAreaPadding?: boolean;
  className?: string;
  containerClassName?: string;
  bodyClassName?: string;
  headerClassName?: string;
  contentPaneClassName?: string;
  contentStackClassName?: string;
  visualPaneClassName?: string;
}

const DEFAULT_SHELL_PADDING =
  'px-4 py-6 sm:px-6 md:py-8 lg:px-8 lg:py-10';

const SAFE_AREA_SHELL_PADDING =
  'pt-[calc(var(--safe-area-top)+1rem)] pr-[calc(var(--mobile-page-gutter)+var(--safe-area-right))] pb-[calc(var(--safe-area-bottom)+1.5rem)] pl-[calc(var(--mobile-page-gutter)+var(--safe-area-left))] md:px-6 md:py-8 lg:px-8 lg:py-10';

export function ResponsiveSplitShell({
  header,
  content,
  visual,
  visualMode = 'column',
  mobileVisualOrder = 'after-content',
  pinVisualOnDesktop = false,
  safeAreaPadding = false,
  className,
  containerClassName,
  bodyClassName,
  headerClassName,
  contentPaneClassName,
  contentStackClassName,
  visualPaneClassName,
}: ResponsiveSplitShellProps) {
  const contentOrderClass =
    mobileVisualOrder === 'before-content' ? 'order-2' : 'order-1';
  const visualOrderClass =
    mobileVisualOrder === 'before-content' ? 'order-1' : 'order-2';

  const hasVisual = Boolean(visual);

  return (
    <section
      data-testid="responsive-split-shell"
      data-mobile-order={mobileVisualOrder}
      data-safe-area={safeAreaPadding ? 'enabled' : 'disabled'}
      data-visual-mode={visualMode}
      className={cn('relative w-full overflow-hidden bg-black', className)}
    >
      <div
        data-testid="responsive-split-shell-container"
        className={cn(
          'relative mx-auto flex w-full flex-col',
          safeAreaPadding ? SAFE_AREA_SHELL_PADDING : DEFAULT_SHELL_PADDING,
          containerClassName,
        )}
      >
        <div
          data-testid="responsive-split-shell-body"
          className={cn(
            'relative flex flex-col gap-8',
            hasVisual && visualMode === 'column' && 'lg:grid lg:grid-cols-12 lg:items-start lg:gap-10',
            bodyClassName,
          )}
        >
          <div
            data-testid="responsive-split-shell-content"
            className={cn(
              contentOrderClass,
              'relative z-10 min-w-0',
              hasVisual && visualMode === 'column' && 'lg:col-span-6',
              contentPaneClassName,
            )}
          >
            <div className={cn('flex min-w-0 flex-col gap-8', contentStackClassName)}>
              {header ? (
                <div className={cn('min-w-0', headerClassName)}>{header}</div>
              ) : null}

              <div className="min-w-0">{content}</div>
            </div>
          </div>

          {hasVisual ? (
            <div
              data-testid="responsive-split-shell-visual"
              className={cn(
                visualOrderClass,
                'min-w-0 overflow-hidden',
                visualMode === 'column' &&
                  'relative min-h-[20rem] sm:min-h-[24rem] lg:col-span-6 lg:min-h-[calc(100dvh-4rem)]',
                visualMode === 'background' &&
                  'relative min-h-[20rem] sm:min-h-[24rem] lg:absolute lg:inset-0 lg:z-0 lg:min-h-0',
                pinVisualOnDesktop && visualMode === 'column' && 'lg:sticky lg:top-16 lg:self-start',
                visualPaneClassName,
              )}
            >
              {visual}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
