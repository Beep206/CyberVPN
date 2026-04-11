'use client';

import { useState, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/shared/ui/modal';
import { parseFeatureLines } from '@/features/commerce/lib/formatting';

interface PlanFormValues {
  name: string;
  price: string;
  currency: string;
  duration_days: string;
  data_limit_gb: string;
  max_devices: string;
  features: string;
  is_active: boolean;
}

interface EditablePlan {
  uuid: string;
  name: string;
  price: number;
  currency: string;
  durationDays: number;
  dataLimitGb?: number | null;
  maxDevices?: number | null;
  features?: string[] | null;
  isActive: boolean;
}

interface PlanEditorModalProps {
  isOpen: boolean;
  mode: 'create' | 'edit';
  initialPlan?: EditablePlan | null;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    price: number;
    currency: string;
    duration_days: number;
    data_limit_gb?: number;
    max_devices?: number;
    features?: string[];
    is_active: boolean;
  }) => Promise<void> | void;
}

const EMPTY_VALUES: PlanFormValues = {
  name: '',
  price: '',
  currency: 'USD',
  duration_days: '30',
  data_limit_gb: '',
  max_devices: '',
  features: '',
  is_active: true,
};

function buildFormValues(initialPlan?: EditablePlan | null): PlanFormValues {
  if (!initialPlan) {
    return EMPTY_VALUES;
  }

  return {
    name: initialPlan.name,
    price: String(initialPlan.price),
    currency: initialPlan.currency,
    duration_days: String(initialPlan.durationDays),
    data_limit_gb:
      typeof initialPlan.dataLimitGb === 'number' ? String(initialPlan.dataLimitGb) : '',
    max_devices:
      typeof initialPlan.maxDevices === 'number' ? String(initialPlan.maxDevices) : '',
    features: initialPlan.features?.join('\n') ?? '',
    is_active: initialPlan.isActive,
  };
}

export function PlanEditorModal({
  isOpen,
  mode,
  initialPlan,
  isSubmitting = false,
  onClose,
  onSubmit,
}: PlanEditorModalProps) {
  const t = useTranslations('Commerce');

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={mode === 'create' ? t('plans.createTitle') : t('plans.editTitle')}
    >
      <PlanEditorModalForm
        key={`${mode}:${initialPlan?.uuid ?? 'create'}`}
        initialPlan={initialPlan}
        isSubmitting={isSubmitting}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </Modal>
  );
}

function PlanEditorModalForm({
  initialPlan,
  isSubmitting = false,
  onClose,
  onSubmit,
}: Pick<
  PlanEditorModalProps,
  'initialPlan' | 'isSubmitting' | 'onClose' | 'onSubmit'
>) {
  const t = useTranslations('Commerce');
  const [values, setValues] = useState<PlanFormValues>(() => buildFormValues(initialPlan));
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const price = Number(values.price);
    const durationDays = Number(values.duration_days);
    const dataLimitGb = values.data_limit_gb ? Number(values.data_limit_gb) : undefined;
    const maxDevices = values.max_devices ? Number(values.max_devices) : undefined;

    if (!values.name.trim()) {
      setError(t('common.validation.nameRequired'));
      return;
    }

    if (!values.currency.trim()) {
      setError(t('common.validation.currencyRequired'));
      return;
    }

    if (!Number.isFinite(price) || price < 0) {
      setError(t('common.validation.priceInvalid'));
      return;
    }

    if (!Number.isFinite(durationDays) || durationDays <= 0) {
      setError(t('common.validation.durationInvalid'));
      return;
    }

    if (typeof dataLimitGb === 'number' && (!Number.isFinite(dataLimitGb) || dataLimitGb < 0)) {
      setError(t('common.validation.dataLimitInvalid'));
      return;
    }

    if (typeof maxDevices === 'number' && (!Number.isFinite(maxDevices) || maxDevices <= 0)) {
      setError(t('common.validation.maxDevicesInvalid'));
      return;
    }

    await onSubmit({
      name: values.name.trim(),
      price,
      currency: values.currency.trim().toUpperCase(),
      duration_days: durationDays,
      data_limit_gb: dataLimitGb,
      max_devices: maxDevices,
      features: parseFeatureLines(values.features),
      is_active: values.is_active,
    });
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('common.name')}
            </span>
            <Input
              value={values.name}
              onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))}
              placeholder={t('plans.form.namePlaceholder')}
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('common.currency')}
            </span>
            <Input
              value={values.currency}
              onChange={(event) =>
                setValues((current) => ({ ...current, currency: event.target.value }))
              }
              placeholder="USD"
              maxLength={3}
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('common.price')}
            </span>
            <Input
              type="number"
              min="0"
              step="0.01"
              value={values.price}
              onChange={(event) => setValues((current) => ({ ...current, price: event.target.value }))}
              placeholder="9.99"
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('common.durationDays')}
            </span>
            <Input
              type="number"
              min="1"
              step="1"
              value={values.duration_days}
              onChange={(event) =>
                setValues((current) => ({ ...current, duration_days: event.target.value }))
              }
              placeholder="30"
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('common.dataLimitGb')}
            </span>
            <Input
              type="number"
              min="0"
              step="1"
              value={values.data_limit_gb}
              onChange={(event) =>
                setValues((current) => ({ ...current, data_limit_gb: event.target.value }))
              }
              placeholder={t('common.optional')}
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('common.maxDevices')}
            </span>
            <Input
              type="number"
              min="1"
              step="1"
              value={values.max_devices}
              onChange={(event) =>
                setValues((current) => ({ ...current, max_devices: event.target.value }))
              }
              placeholder={t('common.optional')}
            />
          </label>
        </div>

        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('common.features')}
          </span>
          <textarea
            value={values.features}
            onChange={(event) =>
              setValues((current) => ({ ...current, features: event.target.value }))
            }
            rows={5}
            placeholder={t('plans.form.featuresPlaceholder')}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>

        <label className="flex items-center gap-3 rounded-xl border border-grid-line/20 bg-terminal-surface/35 px-4 py-3">
          <input
            type="checkbox"
            checked={values.is_active}
            onChange={(event) =>
              setValues((current) => ({ ...current, is_active: event.target.checked }))
            }
            className="h-4 w-4 rounded border-grid-line/30 bg-terminal-bg"
          />
          <span className="text-sm font-mono text-foreground">{t('common.isActive')}</span>
        </label>

        {error ? (
          <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
            {error}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-end gap-3">
          <Button type="button" variant="ghost" magnetic={false} onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button type="submit" magnetic={false} disabled={isSubmitting}>
            {isSubmitting ? t('common.saving') : t('common.save')}
          </Button>
        </div>
      </form>
  );
}
