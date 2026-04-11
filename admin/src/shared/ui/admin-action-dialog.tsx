'use client';

import { useState, type ReactNode } from 'react';
import { AlertTriangle, ShieldAlert } from 'lucide-react';
import type { ButtonProps } from '@/components/ui/button';
import { Button } from '@/components/ui/button';
import { Modal } from '@/shared/ui/modal';

type ActionTone = 'warning' | 'danger';

interface AdminActionDialogProps {
  isOpen: boolean;
  isPending?: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel: string;
  onClose: () => void;
  onConfirm: (reason?: string) => Promise<void> | void;
  confirmVariant?: ButtonProps['variant'];
  tone?: ActionTone;
  subject?: ReactNode;
  subjectLabel?: string;
  reasonLabel?: string;
  reasonPlaceholder?: string;
  reasonRequired?: boolean;
  reasonValidationMessage?: string;
}

const toneIconMap = {
  warning: AlertTriangle,
  danger: ShieldAlert,
} as const;

const toneClassMap = {
  warning: 'border-amber-400/30 bg-amber-400/10 text-amber-200',
  danger: 'border-neon-pink/30 bg-neon-pink/10 text-neon-pink',
} as const;

export function AdminActionDialog({
  isOpen,
  isPending = false,
  title,
  description,
  confirmLabel,
  cancelLabel,
  onClose,
  onConfirm,
  confirmVariant = 'destructive',
  tone = 'danger',
  subject,
  subjectLabel,
  reasonLabel,
  reasonPlaceholder,
  reasonRequired = false,
  reasonValidationMessage,
}: AdminActionDialogProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      {isOpen ? (
        <AdminActionDialogBody
          isPending={isPending}
          description={description}
          confirmLabel={confirmLabel}
          cancelLabel={cancelLabel}
          onClose={onClose}
          onConfirm={onConfirm}
          confirmVariant={confirmVariant}
          tone={tone}
          subject={subject}
          subjectLabel={subjectLabel}
          reasonLabel={reasonLabel}
          reasonPlaceholder={reasonPlaceholder}
          reasonRequired={reasonRequired}
          reasonValidationMessage={reasonValidationMessage}
        />
      ) : null}
    </Modal>
  );
}

function AdminActionDialogBody({
  isPending = false,
  description,
  confirmLabel,
  cancelLabel,
  onClose,
  onConfirm,
  confirmVariant = 'destructive',
  tone = 'danger',
  subject,
  subjectLabel,
  reasonLabel,
  reasonPlaceholder,
  reasonRequired = false,
  reasonValidationMessage,
}: Omit<AdminActionDialogProps, 'isOpen' | 'title'>) {
  const [reason, setReason] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const ToneIcon = toneIconMap[tone];
  const showsReasonField = Boolean(reasonLabel);

  async function handleConfirm() {
    const nextReason = reason.trim();

    if (reasonRequired && !nextReason) {
      setLocalError(reasonValidationMessage ?? 'Reason is required.');
      return;
    }

    setLocalError(null);
    await onConfirm(nextReason || undefined);
  }

  return (
    <div className="space-y-5">
      <div className={`rounded-2xl border p-4 ${toneClassMap[tone]}`}>
        <div className="flex items-start gap-3">
          <div className="mt-0.5 shrink-0">
            <ToneIcon className="h-5 w-5" />
          </div>
          <div className="space-y-2">
            <p className="text-sm font-mono leading-6">{description}</p>
            {subject ? (
              <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3 text-sm font-mono text-white">
                {subjectLabel ? (
                  <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {subjectLabel}
                  </p>
                ) : null}
                <div className={subjectLabel ? 'mt-2' : undefined}>
                  {subject}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {showsReasonField ? (
        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {reasonLabel}
          </span>
          <textarea
            value={reason}
            onChange={(event) => {
              setReason(event.target.value);
              if (localError) {
                setLocalError(null);
              }
            }}
            rows={4}
            placeholder={reasonPlaceholder}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
      ) : null}

      {localError ? (
        <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
          {localError}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button
          type="button"
          variant="ghost"
          magnetic={false}
          onClick={onClose}
          disabled={isPending}
        >
          {cancelLabel}
        </Button>
        <Button
          type="button"
          variant={confirmVariant}
          magnetic={false}
          onClick={() => {
            void handleConfirm();
          }}
          disabled={isPending}
        >
          {confirmLabel}
        </Button>
      </div>
    </div>
  );
}
