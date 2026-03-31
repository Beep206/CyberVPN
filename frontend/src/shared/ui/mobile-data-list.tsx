import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface MobileDataListField {
  label: ReactNode;
  value: ReactNode;
  emphasize?: boolean;
  fullWidth?: boolean;
}

export interface MobileDataListItem {
  id: string;
  title: ReactNode;
  subtitle?: ReactNode;
  status?: ReactNode;
  priority?: ReactNode;
  primaryFields: MobileDataListField[];
  secondaryFields?: MobileDataListField[];
  actions?: ReactNode;
}

interface MobileDataListProps {
  items: MobileDataListItem[];
  className?: string;
  itemClassName?: string;
  emptyState?: ReactNode;
}

export function MobileDataList({
  items,
  className,
  itemClassName,
  emptyState = null,
}: MobileDataListProps) {
  if (!items.length) {
    return emptyState ? <div className="rounded-2xl border border-grid-line/30 bg-terminal-surface/40 p-4">{emptyState}</div> : null;
  }

  return (
    <div className={cn('grid grid-cols-1 gap-3', className)}>
      {items.map((item) => (
        <article
          key={item.id}
          data-testid="mobile-data-list-item"
          className={cn(
            'rounded-2xl border border-grid-line/30 bg-terminal-surface/60 p-4 shadow-[0_0_20px_rgba(0,255,255,0.04)] backdrop-blur-md',
            itemClassName,
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 space-y-2">
              <div className="min-w-0 text-base font-display text-foreground">
                {item.title}
              </div>

              {item.subtitle ? (
                <div className="min-w-0 text-xs font-mono uppercase tracking-wider text-muted-foreground">
                  {item.subtitle}
                </div>
              ) : null}
            </div>

            {item.priority ? (
              <div className="shrink-0 text-right text-sm font-mono text-neon-cyan">
                {item.priority}
              </div>
            ) : null}
          </div>

          {item.status ? (
            <div className="mt-3 flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-muted-foreground">
              {item.status}
            </div>
          ) : null}

          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {item.primaryFields.map((field, index) => (
              <div
                key={`${item.id}-primary-${index}`}
                className={cn(field.fullWidth && 'sm:col-span-2')}
              >
                <div className="text-[10px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                  {field.label}
                </div>
                <div
                  className={cn(
                    'mt-1 text-sm font-mono text-foreground break-words',
                    field.emphasize && 'text-neon-cyan',
                  )}
                >
                  {field.value}
                </div>
              </div>
            ))}
          </div>

          {item.secondaryFields?.length ? (
            <div className="mt-4 grid grid-cols-1 gap-3 border-t border-grid-line/20 pt-4 sm:grid-cols-2">
              {item.secondaryFields.map((field, index) => (
                <div
                  key={`${item.id}-secondary-${index}`}
                  className={cn(field.fullWidth && 'sm:col-span-2')}
                >
                  <div className="text-[10px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
                    {field.label}
                  </div>
                  <div
                    className={cn(
                      'mt-1 text-sm font-mono text-foreground break-words',
                      field.emphasize && 'text-neon-cyan',
                    )}
                  >
                    {field.value}
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          {item.actions ? (
            <div className="mt-4 flex flex-wrap gap-2 border-t border-grid-line/20 pt-4">
              {item.actions}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}
