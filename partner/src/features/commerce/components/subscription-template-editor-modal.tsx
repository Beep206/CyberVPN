'use client';

import { useState, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/shared/ui/modal';

interface SubscriptionTemplateFormValues {
  name: string;
  templateType: TemplateType;
  templateJson: string;
  encodedTemplateYaml: string;
}

type CreateTemplatePayload = Parameters<typeof import('@/lib/api/subscriptions').subscriptionsApi.create>[0];
type TemplateType = CreateTemplatePayload['templateType'];

interface EditableSubscriptionTemplate {
  uuid: string;
  name: string;
  templateType: TemplateType;
  templateJson: Record<string, unknown> | null;
  encodedTemplateYaml: string | null;
}

interface SubscriptionTemplateEditorModalProps {
  isOpen: boolean;
  mode: 'create' | 'edit';
  initialTemplate?: EditableSubscriptionTemplate | null;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    templateType: TemplateType;
    templateJson: Record<string, unknown> | null;
    encodedTemplateYaml: string | null;
  }) => Promise<void> | void;
}

const TEMPLATE_TYPES: readonly TemplateType[] = [
  'XRAY_JSON',
  'XRAY_BASE64',
  'MIHOMO',
  'STASH',
  'CLASH',
  'SINGBOX',
];

const EMPTY_VALUES: SubscriptionTemplateFormValues = {
  name: '',
  templateType: 'XRAY_JSON',
  templateJson: '',
  encodedTemplateYaml: '',
};

function buildFormValues(
  initialTemplate?: EditableSubscriptionTemplate | null,
): SubscriptionTemplateFormValues {
  if (!initialTemplate) {
    return EMPTY_VALUES;
  }

  return {
    name: initialTemplate.name,
    templateType: initialTemplate.templateType,
    templateJson: initialTemplate.templateJson
      ? JSON.stringify(initialTemplate.templateJson, null, 2)
      : '',
    encodedTemplateYaml: initialTemplate.encodedTemplateYaml ?? '',
  };
}

function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function SubscriptionTemplateEditorModal({
  isOpen,
  mode,
  initialTemplate,
  isSubmitting = false,
  onClose,
  onSubmit,
}: SubscriptionTemplateEditorModalProps) {
  const t = useTranslations('Commerce');

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        mode === 'create'
          ? t('subscriptionTemplates.createTitle')
          : t('subscriptionTemplates.editTitle')
      }
    >
      <SubscriptionTemplateEditorModalForm
        key={`${mode}:${initialTemplate?.uuid ?? 'create'}`}
        mode={mode}
        initialTemplate={initialTemplate}
        isSubmitting={isSubmitting}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </Modal>
  );
}

function SubscriptionTemplateEditorModalForm({
  mode,
  initialTemplate,
  isSubmitting = false,
  onClose,
  onSubmit,
}: Pick<
  SubscriptionTemplateEditorModalProps,
  'mode' | 'initialTemplate' | 'isSubmitting' | 'onClose' | 'onSubmit'
>) {
  const t = useTranslations('Commerce');
  const [values, setValues] = useState<SubscriptionTemplateFormValues>(() =>
    buildFormValues(initialTemplate),
  );
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!values.name.trim()) {
      setError(t('common.validation.nameRequired'));
      return;
    }

    let parsedTemplateJson: Record<string, unknown> | null = null;
    if (mode === 'edit' && values.templateJson.trim()) {
      try {
        const parsed = JSON.parse(values.templateJson) as unknown;
        if (!isJsonObject(parsed)) {
          setError(t('common.validation.configJsonInvalid'));
          return;
        }
        parsedTemplateJson = parsed;
      } catch {
        setError(t('common.validation.configJsonInvalid'));
        return;
      }
    }

    await onSubmit({
      name: values.name.trim(),
      templateType: values.templateType,
      templateJson: parsedTemplateJson,
      encodedTemplateYaml:
        mode === 'edit' ? values.encodedTemplateYaml.trim() || null : null,
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
              placeholder={t('subscriptionTemplates.form.namePlaceholder')}
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('common.templateType')}
            </span>
            <select
              value={values.templateType}
              disabled={mode === 'edit'}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  templateType: event.target.value as TemplateType,
                }))
              }
              className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            >
              {TEMPLATE_TYPES.map((templateType) => (
                <option key={templateType} value={templateType}>
                  {templateType}
                </option>
              ))}
            </select>
          </label>
        </div>

        {mode === 'edit' ? (
          <>
            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.configData')}
              </span>
              <textarea
                value={values.templateJson}
                onChange={(event) =>
                  setValues((current) => ({ ...current, templateJson: event.target.value }))
                }
                rows={8}
                placeholder={t('subscriptionTemplates.form.configPlaceholder')}
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('subscriptionTemplates.form.encodedYaml')}
              </span>
              <textarea
                value={values.encodedTemplateYaml}
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    encodedTemplateYaml: event.target.value,
                  }))
                }
                rows={6}
                placeholder={t('subscriptionTemplates.form.encodedYamlPlaceholder')}
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </label>
          </>
        ) : null}

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
