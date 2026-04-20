'use client';

import { useState, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/shared/ui/modal';
import type { AddonRecord, CreateAddonRequest, UpdateAddonRequest } from '@/lib/api/addons';

type AddonFormValues = {
  code: string;
  display_name: string;
  duration_mode: string;
  is_stackable: boolean;
  quantity_step: string;
  price_usd: string;
  price_rub: string;
  max_quantity_by_plan_json: string;
  delta_entitlements_json: string;
  requires_location: boolean;
  sale_channels: string;
  is_active: boolean;
};

interface AddonEditorModalProps {
  isOpen: boolean;
  mode: 'create' | 'edit';
  initialAddon?: AddonRecord | null;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: CreateAddonRequest | UpdateAddonRequest) => Promise<void> | void;
}

const EMPTY_VALUES: AddonFormValues = {
  code: '',
  display_name: '',
  duration_mode: 'inherits_subscription',
  is_stackable: true,
  quantity_step: '1',
  price_usd: '',
  price_rub: '',
  max_quantity_by_plan_json: '{\n  "basic": 2,\n  "plus": 3,\n  "pro": 5,\n  "max": 10\n}',
  delta_entitlements_json: '{\n  "device_limit": 1\n}',
  requires_location: false,
  sale_channels: 'web,miniapp,telegram_bot,admin',
  is_active: true,
};

function splitCsv(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildFormValues(initialAddon?: AddonRecord | null): AddonFormValues {
  if (!initialAddon) {
    return EMPTY_VALUES;
  }

  return {
    code: initialAddon.code,
    display_name: initialAddon.display_name,
    duration_mode: initialAddon.duration_mode,
    is_stackable: initialAddon.is_stackable,
    quantity_step: String(initialAddon.quantity_step),
    price_usd: String(initialAddon.price_usd),
    price_rub: typeof initialAddon.price_rub === 'number' ? String(initialAddon.price_rub) : '',
    max_quantity_by_plan_json: JSON.stringify(initialAddon.max_quantity_by_plan, null, 2),
    delta_entitlements_json: JSON.stringify(initialAddon.delta_entitlements, null, 2),
    requires_location: initialAddon.requires_location,
    sale_channels: initialAddon.sale_channels.join(','),
    is_active: initialAddon.is_active,
  };
}

export function AddonEditorModal({
  isOpen,
  mode,
  initialAddon,
  isSubmitting = false,
  onClose,
  onSubmit,
}: AddonEditorModalProps) {
  const t = useTranslations('Commerce');

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={mode === 'create' ? t('addons.createTitle') : t('addons.editTitle')}
    >
      <AddonEditorModalForm
        key={`${mode}:${initialAddon?.uuid ?? 'create'}`}
        initialAddon={initialAddon}
        isSubmitting={isSubmitting}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </Modal>
  );
}

function AddonEditorModalForm({
  initialAddon,
  isSubmitting,
  onClose,
  onSubmit,
}: Pick<AddonEditorModalProps, 'initialAddon' | 'isSubmitting' | 'onClose' | 'onSubmit'>) {
  const t = useTranslations('Commerce');
  const [values, setValues] = useState(() => buildFormValues(initialAddon));
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const quantityStep = Number(values.quantity_step);
      const priceUsd = Number(values.price_usd);
      const priceRub = values.price_rub ? Number(values.price_rub) : undefined;

      if (!values.code.trim() || !values.display_name.trim()) {
        setError(t('common.validation.nameRequired'));
        return;
      }

      if (!Number.isFinite(quantityStep) || quantityStep <= 0 || !Number.isFinite(priceUsd) || priceUsd < 0) {
        setError(t('addons.validation.numericInvalid'));
        return;
      }

      const payload: CreateAddonRequest | UpdateAddonRequest = {
        display_name: values.display_name.trim(),
        duration_mode: values.duration_mode.trim(),
        is_stackable: values.is_stackable,
        quantity_step: quantityStep,
        price_usd: priceUsd,
        price_rub: priceRub,
        max_quantity_by_plan: JSON.parse(values.max_quantity_by_plan_json) as Record<string, number>,
        delta_entitlements: JSON.parse(values.delta_entitlements_json) as Record<string, unknown>,
        requires_location: values.requires_location,
        sale_channels: splitCsv(values.sale_channels),
        is_active: values.is_active,
      };

      if (!initialAddon) {
        (payload as CreateAddonRequest).code = values.code.trim();
      }

      await onSubmit(payload);
    } catch {
      setError(t('addons.validation.jsonInvalid'));
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <div className="grid gap-4 md:grid-cols-2">
        {!initialAddon ? (
          <Field
            label={t('addons.fields.code')}
            value={values.code}
            onChange={(value) => setValues((current) => ({ ...current, code: value }))}
            placeholder="extra_device"
          />
        ) : null}
        <Field
          label={t('addons.fields.displayName')}
          value={values.display_name}
          onChange={(value) => setValues((current) => ({ ...current, display_name: value }))}
          placeholder="+1 device"
        />
        <Field
          label={t('addons.fields.durationMode')}
          value={values.duration_mode}
          onChange={(value) => setValues((current) => ({ ...current, duration_mode: value }))}
          placeholder="inherits_subscription"
        />
        <Field
          label={t('addons.fields.quantityStep')}
          type="number"
          value={values.quantity_step}
          onChange={(value) => setValues((current) => ({ ...current, quantity_step: value }))}
        />
        <Field
          label={t('addons.fields.priceUsd')}
          type="number"
          value={values.price_usd}
          onChange={(value) => setValues((current) => ({ ...current, price_usd: value }))}
        />
        <Field
          label={t('addons.fields.priceRub')}
          type="number"
          value={values.price_rub}
          onChange={(value) => setValues((current) => ({ ...current, price_rub: value }))}
          placeholder={t('common.optional')}
        />
        <Field
          label={t('addons.fields.saleChannels')}
          value={values.sale_channels}
          onChange={(value) => setValues((current) => ({ ...current, sale_channels: value }))}
          placeholder="web,miniapp,telegram_bot,admin"
        />
      </div>

      <label className="block space-y-2">
        <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
          {t('addons.fields.maxQuantityByPlan')}
        </span>
        <textarea
          value={values.max_quantity_by_plan_json}
          onChange={(event) =>
            setValues((current) => ({ ...current, max_quantity_by_plan_json: event.target.value }))
          }
          rows={6}
          className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
      </label>

      <label className="block space-y-2">
        <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
          {t('addons.fields.deltaEntitlements')}
        </span>
        <textarea
          value={values.delta_entitlements_json}
          onChange={(event) =>
            setValues((current) => ({ ...current, delta_entitlements_json: event.target.value }))
          }
          rows={6}
          className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
      </label>

      <div className="grid gap-3 md:grid-cols-3">
        <CheckboxField
          label={t('addons.fields.isStackable')}
          checked={values.is_stackable}
          onChange={(checked) => setValues((current) => ({ ...current, is_stackable: checked }))}
        />
        <CheckboxField
          label={t('addons.fields.requiresLocation')}
          checked={values.requires_location}
          onChange={(checked) =>
            setValues((current) => ({ ...current, requires_location: checked }))
          }
        />
        <CheckboxField
          label={t('common.isActive')}
          checked={values.is_active}
          onChange={(checked) => setValues((current) => ({ ...current, is_active: checked }))}
        />
      </div>

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

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="space-y-2">
      <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </span>
      <Input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}

function CheckboxField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-3 rounded-xl border border-grid-line/20 bg-terminal-surface/35 px-4 py-3">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-grid-line/30 bg-terminal-bg"
      />
      <span className="text-sm font-mono text-foreground">{label}</span>
    </label>
  );
}
