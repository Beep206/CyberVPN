'use client';

import { useState, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/shared/ui/modal';
import type { CreatePlanRequest, PlanRecord, UpdatePlanRequest } from '@/lib/api/plans';

type PlanFormValues = {
  name: string;
  plan_code: string;
  display_name: string;
  catalog_visibility: string;
  duration_days: string;
  devices_included: string;
  price_usd: string;
  price_rub: string;
  traffic_mode: string;
  traffic_label: string;
  traffic_enforcement_profile: string;
  traffic_limit_bytes: string;
  connection_modes: string;
  server_pool: string;
  support_sla: string;
  dedicated_ip_included: string;
  dedicated_ip_eligible: boolean;
  sale_channels: string;
  invite_count: string;
  invite_friend_days: string;
  invite_expiry_days: string;
  trial_eligible: boolean;
  sort_order: string;
  features_json: string;
  is_active: boolean;
};

interface PlanEditorModalProps {
  isOpen: boolean;
  mode: 'create' | 'edit';
  initialPlan?: PlanRecord | null;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: CreatePlanRequest | UpdatePlanRequest) => Promise<void> | void;
}

const EMPTY_VALUES: PlanFormValues = {
  name: '',
  plan_code: '',
  display_name: '',
  catalog_visibility: 'public',
  duration_days: '365',
  devices_included: '5',
  price_usd: '',
  price_rub: '',
  traffic_mode: 'fair_use',
  traffic_label: 'Unlimited',
  traffic_enforcement_profile: '',
  traffic_limit_bytes: '',
  connection_modes: 'standard,stealth',
  server_pool: 'shared_plus',
  support_sla: 'standard',
  dedicated_ip_included: '0',
  dedicated_ip_eligible: true,
  sale_channels: 'web,miniapp,telegram_bot,admin',
  invite_count: '0',
  invite_friend_days: '0',
  invite_expiry_days: '0',
  trial_eligible: false,
  sort_order: '0',
  features_json: '{\n  "marketing_badge": "Most Popular"\n}',
  is_active: true,
};

function splitCsv(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseJsonObject(value: string) {
  if (!value.trim()) {
    return {};
  }

  return JSON.parse(value) as Record<string, unknown>;
}

function buildFormValues(initialPlan?: PlanRecord | null): PlanFormValues {
  if (!initialPlan) {
    return EMPTY_VALUES;
  }

  return {
    name: initialPlan.name,
    plan_code: initialPlan.plan_code,
    display_name: initialPlan.display_name,
    catalog_visibility: initialPlan.catalog_visibility,
    duration_days: String(initialPlan.duration_days),
    devices_included: String(initialPlan.devices_included),
    price_usd: String(initialPlan.price_usd),
    price_rub:
      typeof initialPlan.price_rub === 'number' ? String(initialPlan.price_rub) : '',
    traffic_mode: initialPlan.traffic_policy.mode,
    traffic_label: initialPlan.traffic_policy.display_label,
    traffic_enforcement_profile: initialPlan.traffic_policy.enforcement_profile ?? '',
    traffic_limit_bytes:
      typeof initialPlan.traffic_limit_bytes === 'number'
        ? String(initialPlan.traffic_limit_bytes)
        : '',
    connection_modes: initialPlan.connection_modes.join(','),
    server_pool: initialPlan.server_pool.join(','),
    support_sla: initialPlan.support_sla,
    dedicated_ip_included: String(initialPlan.dedicated_ip.included),
    dedicated_ip_eligible: initialPlan.dedicated_ip.eligible,
    sale_channels: initialPlan.sale_channels.join(','),
    invite_count: String(initialPlan.invite_bundle.count),
    invite_friend_days: String(initialPlan.invite_bundle.friend_days),
    invite_expiry_days: String(initialPlan.invite_bundle.expiry_days),
    trial_eligible: initialPlan.trial_eligible,
    sort_order: String(initialPlan.sort_order),
    features_json: JSON.stringify(initialPlan.features ?? {}, null, 2),
    is_active: initialPlan.is_active,
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
  isSubmitting,
  onClose,
  onSubmit,
}: Pick<PlanEditorModalProps, 'initialPlan' | 'isSubmitting' | 'onClose' | 'onSubmit'>) {
  const t = useTranslations('Commerce');
  const [values, setValues] = useState<PlanFormValues>(() => buildFormValues(initialPlan));
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const durationDays = Number(values.duration_days);
      const devicesIncluded = Number(values.devices_included);
      const priceUsd = Number(values.price_usd);
      const priceRub = values.price_rub ? Number(values.price_rub) : undefined;
      const trafficLimitBytes = values.traffic_limit_bytes
        ? Number(values.traffic_limit_bytes)
        : undefined;
      const dedicatedIpIncluded = Number(values.dedicated_ip_included);
      const inviteCount = Number(values.invite_count);
      const inviteFriendDays = Number(values.invite_friend_days);
      const inviteExpiryDays = Number(values.invite_expiry_days);
      const sortOrder = Number(values.sort_order);

      if (!values.name.trim() || !values.plan_code.trim() || !values.display_name.trim()) {
        setError(t('common.validation.nameRequired'));
        return;
      }

      if (
        !Number.isFinite(durationDays)
        || durationDays <= 0
        || !Number.isFinite(devicesIncluded)
        || devicesIncluded <= 0
        || !Number.isFinite(priceUsd)
        || priceUsd < 0
      ) {
        setError(t('plans.validation.numericInvalid'));
        return;
      }

      const payload: CreatePlanRequest | UpdatePlanRequest = {
        name: values.name.trim(),
        plan_code: values.plan_code.trim(),
        display_name: values.display_name.trim(),
        catalog_visibility: values.catalog_visibility,
        duration_days: durationDays,
        devices_included: devicesIncluded,
        price_usd: priceUsd,
        price_rub: priceRub,
        traffic_limit_bytes: trafficLimitBytes,
        traffic_policy: {
          mode: values.traffic_mode.trim(),
          display_label: values.traffic_label.trim(),
          enforcement_profile: values.traffic_enforcement_profile.trim() || null,
        },
        connection_modes: splitCsv(values.connection_modes),
        server_pool: splitCsv(values.server_pool),
        support_sla: values.support_sla,
        dedicated_ip: {
          included: Number.isFinite(dedicatedIpIncluded) ? dedicatedIpIncluded : 0,
          eligible: values.dedicated_ip_eligible,
        },
        sale_channels: splitCsv(values.sale_channels),
        invite_bundle: {
          count: Number.isFinite(inviteCount) ? inviteCount : 0,
          friend_days: Number.isFinite(inviteFriendDays) ? inviteFriendDays : 0,
          expiry_days: Number.isFinite(inviteExpiryDays) ? inviteExpiryDays : 0,
        },
        trial_eligible: values.trial_eligible,
        sort_order: Number.isFinite(sortOrder) ? sortOrder : 0,
        features: parseJsonObject(values.features_json),
        is_active: values.is_active,
      };

      await onSubmit(payload);
    } catch {
      setError(t('plans.validation.jsonInvalid'));
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label={t('common.name')}
          value={values.name}
          onChange={(value) => setValues((current) => ({ ...current, name: value }))}
          placeholder={t('plans.form.namePlaceholder')}
        />
        <Field
          label={t('plans.fields.planCode')}
          value={values.plan_code}
          onChange={(value) => setValues((current) => ({ ...current, plan_code: value }))}
          placeholder="plus"
        />
        <Field
          label={t('plans.fields.displayName')}
          value={values.display_name}
          onChange={(value) => setValues((current) => ({ ...current, display_name: value }))}
          placeholder="Plus"
        />
        <SelectField
          label={t('plans.fields.visibility')}
          value={values.catalog_visibility}
          onChange={(value) => setValues((current) => ({ ...current, catalog_visibility: value }))}
          options={[
            { value: 'public', label: t('plans.visibility.public') },
            { value: 'hidden', label: t('plans.visibility.hidden') },
          ]}
        />
        <Field
          label={t('common.durationDays')}
          type="number"
          value={values.duration_days}
          onChange={(value) => setValues((current) => ({ ...current, duration_days: value }))}
        />
        <Field
          label={t('plans.fields.devicesIncluded')}
          type="number"
          value={values.devices_included}
          onChange={(value) => setValues((current) => ({ ...current, devices_included: value }))}
        />
        <Field
          label={t('plans.fields.priceUsd')}
          type="number"
          value={values.price_usd}
          onChange={(value) => setValues((current) => ({ ...current, price_usd: value }))}
          placeholder="79"
        />
        <Field
          label={t('plans.fields.priceRub')}
          type="number"
          value={values.price_rub}
          onChange={(value) => setValues((current) => ({ ...current, price_rub: value }))}
          placeholder={t('common.optional')}
        />
        <Field
          label={t('plans.fields.trafficMode')}
          value={values.traffic_mode}
          onChange={(value) => setValues((current) => ({ ...current, traffic_mode: value }))}
          placeholder="fair_use"
        />
        <Field
          label={t('plans.fields.trafficLabel')}
          value={values.traffic_label}
          onChange={(value) => setValues((current) => ({ ...current, traffic_label: value }))}
          placeholder="Unlimited"
        />
        <Field
          label={t('plans.fields.trafficProfile')}
          value={values.traffic_enforcement_profile}
          onChange={(value) =>
            setValues((current) => ({ ...current, traffic_enforcement_profile: value }))
          }
          placeholder="mainstream"
        />
        <Field
          label={t('plans.fields.trafficLimitBytes')}
          type="number"
          value={values.traffic_limit_bytes}
          onChange={(value) =>
            setValues((current) => ({ ...current, traffic_limit_bytes: value }))
          }
          placeholder={t('common.optional')}
        />
        <Field
          label={t('plans.fields.connectionModes')}
          value={values.connection_modes}
          onChange={(value) =>
            setValues((current) => ({ ...current, connection_modes: value }))
          }
          placeholder="standard,stealth"
        />
        <Field
          label={t('plans.fields.serverPool')}
          value={values.server_pool}
          onChange={(value) => setValues((current) => ({ ...current, server_pool: value }))}
          placeholder="shared_plus"
        />
        <SelectField
          label={t('plans.fields.supportSla')}
          value={values.support_sla}
          onChange={(value) => setValues((current) => ({ ...current, support_sla: value }))}
          options={[
            { value: 'standard', label: 'standard' },
            { value: 'priority', label: 'priority' },
            { value: 'vip', label: 'vip' },
            { value: 'internal', label: 'internal' },
          ]}
        />
        <Field
          label={t('plans.fields.dedicatedIpIncluded')}
          type="number"
          value={values.dedicated_ip_included}
          onChange={(value) =>
            setValues((current) => ({ ...current, dedicated_ip_included: value }))
          }
        />
        <Field
          label={t('plans.fields.saleChannels')}
          value={values.sale_channels}
          onChange={(value) => setValues((current) => ({ ...current, sale_channels: value }))}
          placeholder="web,miniapp,telegram_bot,admin"
        />
        <Field
          label={t('plans.fields.inviteCount')}
          type="number"
          value={values.invite_count}
          onChange={(value) => setValues((current) => ({ ...current, invite_count: value }))}
        />
        <Field
          label={t('plans.fields.inviteFriendDays')}
          type="number"
          value={values.invite_friend_days}
          onChange={(value) =>
            setValues((current) => ({ ...current, invite_friend_days: value }))
          }
        />
        <Field
          label={t('plans.fields.inviteExpiryDays')}
          type="number"
          value={values.invite_expiry_days}
          onChange={(value) =>
            setValues((current) => ({ ...current, invite_expiry_days: value }))
          }
        />
        <Field
          label={t('plans.fields.sortOrder')}
          type="number"
          value={values.sort_order}
          onChange={(value) => setValues((current) => ({ ...current, sort_order: value }))}
        />
      </div>

      <label className="block space-y-2">
        <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
          {t('plans.fields.featuresJson')}
        </span>
        <textarea
          value={values.features_json}
          onChange={(event) =>
            setValues((current) => ({ ...current, features_json: event.target.value }))
          }
          rows={7}
          className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
      </label>

      <div className="grid gap-3 md:grid-cols-3">
        <CheckboxField
          label={t('plans.fields.dedicatedIpEligible')}
          checked={values.dedicated_ip_eligible}
          onChange={(checked) =>
            setValues((current) => ({ ...current, dedicated_ip_eligible: checked }))
          }
        />
        <CheckboxField
          label={t('plans.fields.trialEligible')}
          checked={values.trial_eligible}
          onChange={(checked) => setValues((current) => ({ ...current, trial_eligible: checked }))}
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

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="space-y-2">
      <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
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
