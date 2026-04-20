'use client';

import { useState, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/shared/ui/modal';

interface SubscriptionTemplateFormValues {
  name: string;
  template_type: string;
  host_uuid: string;
  inbound_tag: string;
  flow: string;
  config_data: string;
}

interface EditableSubscriptionTemplate {
  uuid: string;
  name: string;
  templateType: string;
  hostUuid?: string | null;
  inboundTag?: string | null;
  flow?: string | null;
  configData?: Record<string, unknown> | null;
}

interface SubscriptionTemplateEditorModalProps {
  isOpen: boolean;
  mode: 'create' | 'edit';
  initialTemplate?: EditableSubscriptionTemplate | null;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    template_type: string;
    host_uuid?: string;
    inbound_tag?: string;
    flow?: string;
    config_data?: Record<string, unknown>;
  }) => Promise<void> | void;
}

const EMPTY_VALUES: SubscriptionTemplateFormValues = {
  name: '',
  template_type: '',
  host_uuid: '',
  inbound_tag: '',
  flow: '',
  config_data: '',
};

function buildFormValues(
  initialTemplate?: EditableSubscriptionTemplate | null,
): SubscriptionTemplateFormValues {
  if (!initialTemplate) {
    return EMPTY_VALUES;
  }

  return {
    name: initialTemplate.name,
    template_type: initialTemplate.templateType,
    host_uuid: initialTemplate.hostUuid ?? '',
    inbound_tag: initialTemplate.inboundTag ?? '',
    flow: initialTemplate.flow ?? '',
    config_data: initialTemplate.configData
      ? JSON.stringify(initialTemplate.configData, null, 2)
      : '',
  };
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
        initialTemplate={initialTemplate}
        isSubmitting={isSubmitting}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </Modal>
  );
}

function SubscriptionTemplateEditorModalForm({
  initialTemplate,
  isSubmitting = false,
  onClose,
  onSubmit,
}: Pick<
  SubscriptionTemplateEditorModalProps,
  'initialTemplate' | 'isSubmitting' | 'onClose' | 'onSubmit'
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

    if (!values.template_type.trim()) {
      setError(t('common.validation.templateTypeRequired'));
      return;
    }

    let parsedConfigData: Record<string, unknown> | undefined;
    if (values.config_data.trim()) {
      try {
        parsedConfigData = JSON.parse(values.config_data) as Record<string, unknown>;
      } catch {
        setError(t('common.validation.configJsonInvalid'));
        return;
      }
    }

    await onSubmit({
      name: values.name.trim(),
      template_type: values.template_type.trim(),
      host_uuid: values.host_uuid.trim() || undefined,
      inbound_tag: values.inbound_tag.trim() || undefined,
      flow: values.flow.trim() || undefined,
      config_data: parsedConfigData,
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
            <Input
              value={values.template_type}
              onChange={(event) =>
                setValues((current) => ({ ...current, template_type: event.target.value }))
              }
              placeholder="vless"
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('common.hostUuid')}
            </span>
            <Input
              value={values.host_uuid}
              onChange={(event) =>
                setValues((current) => ({ ...current, host_uuid: event.target.value }))
              }
              placeholder={t('common.optional')}
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('common.inboundTag')}
            </span>
            <Input
              value={values.inbound_tag}
              onChange={(event) =>
                setValues((current) => ({ ...current, inbound_tag: event.target.value }))
              }
              placeholder={t('common.optional')}
            />
          </label>
        </div>

        <label className="space-y-2 block">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('common.flow')}
          </span>
          <Input
            value={values.flow}
            onChange={(event) => setValues((current) => ({ ...current, flow: event.target.value }))}
            placeholder="xtls-rprx-vision"
          />
        </label>

        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('common.configData')}
          </span>
          <textarea
            value={values.config_data}
            onChange={(event) =>
              setValues((current) => ({ ...current, config_data: event.target.value }))
            }
            rows={8}
            placeholder={t('subscriptionTemplates.form.configPlaceholder')}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
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
