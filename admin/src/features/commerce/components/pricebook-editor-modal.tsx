'use client';

import { useRef, useState, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/shared/ui/modal';
import type {
  CreatePricebookRequest,
  PricebookEntryRequest,
} from '@/lib/api/pricebooks';

type PricebookFormValues = {
  pricebook_key: string;
  display_name: string;
  storefront_id: string;
  merchant_profile_id: string;
  currency_code: string;
  region_code: string;
  version_status: string;
  effective_from: string;
  effective_to: string;
  discount_rules_json: string;
  renewal_pricing_policy_json: string;
  entries_json: string;
  is_active: boolean;
};

interface PricebookEditorModalProps {
  isOpen: boolean;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: CreatePricebookRequest) => Promise<void> | void;
}

const EMPTY_VALUES: PricebookFormValues = {
  pricebook_key: '',
  display_name: '',
  storefront_id: '',
  merchant_profile_id: '',
  currency_code: 'USD',
  region_code: '',
  version_status: 'draft',
  effective_from: '',
  effective_to: '',
  discount_rules_json: '{}',
  renewal_pricing_policy_json: '{}',
  entries_json:
    '[\n  {\n    "offer_id": "00000000-0000-0000-0000-000000000000",\n    "visible_price": 79,\n    "compare_at_price": null,\n    "included_addon_codes": [],\n    "display_order": 10\n  }\n]',
  is_active: true,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseJsonObject(value: string): Record<string, unknown> {
  if (!value.trim()) {
    return {};
  }

  const parsed = JSON.parse(value) as unknown;

  if (!isRecord(parsed)) {
    throw new Error('Expected JSON object');
  }

  return parsed;
}

function parseStringArray(value: unknown): string[] {
  if (value == null) {
    return [];
  }

  if (!Array.isArray(value)) {
    throw new Error('Expected string array');
  }

  return value.map((item) => {
    if (typeof item !== 'string') {
      throw new Error('Expected string array');
    }

    return item.trim();
  }).filter(Boolean);
}

function nullableNumber(value: unknown): number | null {
  if (value == null || value === '') {
    return null;
  }

  const parsed = Number(value);

  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error('Expected non-negative number');
  }

  return parsed;
}

function parseEntries(value: string): PricebookEntryRequest[] {
  const parsed = JSON.parse(value) as unknown;

  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error('Expected non-empty entries array');
  }

  return parsed.map((entry) => {
    if (!isRecord(entry) || typeof entry.offer_id !== 'string') {
      throw new Error('Entry offer_id is required');
    }

    const visiblePrice = Number(entry.visible_price);
    const displayOrder = Number(entry.display_order ?? 0);

    if (!Number.isFinite(visiblePrice) || visiblePrice < 0) {
      throw new Error('Entry visible_price is invalid');
    }

    if (!Number.isFinite(displayOrder) || displayOrder < 0) {
      throw new Error('Entry display_order is invalid');
    }

    return {
      offer_id: entry.offer_id.trim(),
      visible_price: visiblePrice,
      compare_at_price: nullableNumber(entry.compare_at_price),
      included_addon_codes: parseStringArray(entry.included_addon_codes),
      display_order: displayOrder,
    };
  });
}

function normalizeOptionalDateTime(value: string) {
  const trimmed = value.trim();

  if (!trimmed) {
    return null;
  }

  const parsed = new Date(trimmed);

  return Number.isNaN(parsed.getTime()) ? trimmed : parsed.toISOString();
}

function errorDetail(error: unknown) {
  return error instanceof Error ? error.message : '';
}

export function PricebookEditorModal({
  isOpen,
  isSubmitting = false,
  onClose,
  onSubmit,
}: PricebookEditorModalProps) {
  const t = useTranslations('Commerce');

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('pricebooks.createTitle')}
    >
      <PricebookEditorModalForm
        key={isOpen ? 'open' : 'closed'}
        isSubmitting={isSubmitting}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </Modal>
  );
}

function PricebookEditorModalForm({
  isSubmitting,
  onClose,
  onSubmit,
}: Pick<PricebookEditorModalProps, 'isSubmitting' | 'onClose' | 'onSubmit'>) {
  const t = useTranslations('Commerce');
  const [values, setValues] = useState<PricebookFormValues>(EMPTY_VALUES);
  const [error, setError] = useState<string | null>(null);
  const entriesRef = useRef<HTMLTextAreaElement>(null);
  const discountRulesRef = useRef<HTMLTextAreaElement>(null);
  const renewalPolicyRef = useRef<HTMLTextAreaElement>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const currencyCode = values.currency_code.trim().toUpperCase();

      if (
        !values.pricebook_key.trim()
        || !values.display_name.trim()
        || !values.storefront_id.trim()
      ) {
        setError(t('pricebooks.validation.required'));
        return;
      }

      if (currencyCode.length !== 3) {
        setError(t('pricebooks.validation.currencyInvalid'));
        return;
      }

      let discountRules: Record<string, unknown>;
      let renewalPricingPolicy: Record<string, unknown>;
      let entries: PricebookEntryRequest[];

      try {
        discountRules = parseJsonObject(values.discount_rules_json);
      } catch (error) {
        setError(
          t('pricebooks.validation.jsonInvalidDetail', {
            detail: `${t('pricebooks.fields.discountRules')}: ${errorDetail(error)}`,
          }),
        );
        discountRulesRef.current?.focus();
        return;
      }

      try {
        renewalPricingPolicy = parseJsonObject(
          values.renewal_pricing_policy_json,
        );
      } catch (error) {
        setError(
          t('pricebooks.validation.jsonInvalidDetail', {
            detail: `${t('pricebooks.fields.renewalPricingPolicy')}: ${errorDetail(error)}`,
          }),
        );
        renewalPolicyRef.current?.focus();
        return;
      }

      try {
        entries = parseEntries(values.entries_json);
      } catch (error) {
        setError(
          t('pricebooks.validation.jsonInvalidDetail', {
            detail: `${t('pricebooks.fields.entriesJson')}: ${errorDetail(error)}`,
          }),
        );
        entriesRef.current?.focus();
        return;
      }

      const payload: CreatePricebookRequest = {
        pricebook_key: values.pricebook_key.trim(),
        display_name: values.display_name.trim(),
        storefront_id: values.storefront_id.trim(),
        merchant_profile_id: values.merchant_profile_id.trim() || null,
        currency_code: currencyCode,
        region_code: values.region_code.trim().toUpperCase() || null,
        discount_rules: discountRules,
        renewal_pricing_policy: renewalPricingPolicy,
        version_status: values.version_status.trim() || 'draft',
        effective_from: normalizeOptionalDateTime(values.effective_from),
        effective_to: normalizeOptionalDateTime(values.effective_to),
        is_active: values.is_active,
        entries,
      };

      await onSubmit(payload);
    } catch {
      setError(t('pricebooks.validation.jsonInvalid'));
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label={t('pricebooks.fields.pricebookKey')}
          value={values.pricebook_key}
          onChange={(value) =>
            setValues((current) => ({ ...current, pricebook_key: value }))
          }
          placeholder="web_usd_v1"
        />
        <Field
          label={t('pricebooks.fields.displayName')}
          value={values.display_name}
          onChange={(value) =>
            setValues((current) => ({ ...current, display_name: value }))
          }
          placeholder="Web USD V1"
        />
        <Field
          label={t('pricebooks.fields.storefrontId')}
          value={values.storefront_id}
          onChange={(value) =>
            setValues((current) => ({ ...current, storefront_id: value }))
          }
          placeholder="550e8400-e29b-41d4-a716-446655440000"
        />
        <Field
          label={t('pricebooks.fields.merchantProfileId')}
          value={values.merchant_profile_id}
          onChange={(value) =>
            setValues((current) => ({ ...current, merchant_profile_id: value }))
          }
          placeholder={t('common.optional')}
        />
        <Field
          label={t('pricebooks.fields.currencyCode')}
          value={values.currency_code}
          onChange={(value) =>
            setValues((current) => ({ ...current, currency_code: value }))
          }
          placeholder="USD"
        />
        <Field
          label={t('pricebooks.fields.regionCode')}
          value={values.region_code}
          onChange={(value) =>
            setValues((current) => ({ ...current, region_code: value }))
          }
          placeholder={t('common.optional')}
        />
        <SelectField
          label={t('pricebooks.fields.versionStatus')}
          value={values.version_status}
          onChange={(value) =>
            setValues((current) => ({ ...current, version_status: value }))
          }
          options={[
            { value: 'draft', label: t('pricebooks.status.draft') },
            { value: 'scheduled', label: t('pricebooks.status.scheduled') },
            { value: 'active', label: t('pricebooks.status.active') },
            { value: 'archived', label: t('pricebooks.status.archived') },
          ]}
        />
        <Field
          label={t('pricebooks.fields.effectiveFrom')}
          type="datetime-local"
          value={values.effective_from}
          onChange={(value) =>
            setValues((current) => ({ ...current, effective_from: value }))
          }
        />
        <Field
          label={t('pricebooks.fields.effectiveTo')}
          type="datetime-local"
          value={values.effective_to}
          onChange={(value) =>
            setValues((current) => ({ ...current, effective_to: value }))
          }
        />
      </div>

      <label className="block space-y-2">
        <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
          {t('pricebooks.fields.entriesJson')}
        </span>
        <textarea
          value={values.entries_json}
          ref={entriesRef}
          onChange={(event) =>
            setValues((current) => ({
              ...current,
              entries_json: event.target.value,
            }))
          }
          rows={9}
          className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
      </label>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('pricebooks.fields.discountRules')}
          </span>
          <textarea
            value={values.discount_rules_json}
            ref={discountRulesRef}
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                discount_rules_json: event.target.value,
              }))
            }
            rows={5}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('pricebooks.fields.renewalPricingPolicy')}
          </span>
          <textarea
            value={values.renewal_pricing_policy_json}
            ref={renewalPolicyRef}
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                renewal_pricing_policy_json: event.target.value,
              }))
            }
            rows={5}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
      </div>

      <CheckboxField
        label={t('common.isActive')}
        checked={values.is_active}
        onChange={(checked) =>
          setValues((current) => ({ ...current, is_active: checked }))
        }
      />

      {error ? (
        <div
          className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
          role="alert"
          aria-live="assertive"
        >
          {error}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button
          type="button"
          variant="ghost"
          magnetic={false}
          onClick={onClose}
          aria-label={t('common.cancel')}
        >
          {t('common.cancel')}
        </Button>
        <Button
          type="submit"
          magnetic={false}
          disabled={isSubmitting}
          aria-label={isSubmitting ? t('common.saving') : t('common.save')}
        >
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
