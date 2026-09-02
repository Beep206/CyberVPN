import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { createTemplate, listTemplates, removeTemplate, updateTemplate } = vi.hoisted(() => ({
  createTemplate: vi.fn(),
  listTemplates: vi.fn(),
  removeTemplate: vi.fn(),
  updateTemplate: vi.fn(),
}));

vi.mock('next-intl', () => ({ useTranslations: () => (key: string) => key }));
vi.mock('@/lib/api/subscriptions', () => ({
  subscriptionsApi: {
    create: createTemplate,
    list: listTemplates,
    remove: removeTemplate,
    update: updateTemplate,
  },
}));

import { SubscriptionTemplatesConsole } from './subscription-templates-console';

const template = {
  uuid: '550e8400-e29b-41d4-a716-446655440200',
  viewPosition: 1,
  name: 'Primary Xray',
  tags: ['DEFAULT'],
  templateType: 'XRAY_JSON' as const,
  templateJson: { outbounds: [] },
  encodedTemplateYaml: null,
};

function renderConsole() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <SubscriptionTemplatesConsole />
    </QueryClientProvider>,
  );
}

describe('SubscriptionTemplatesConsole Remnawave 3.4.3 boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listTemplates.mockResolvedValue({ data: { total: 1, templates: [template] } });
    updateTemplate.mockResolvedValue({ data: undefined, status: 202 });
    removeTemplate.mockResolvedValue({ data: undefined, status: 204 });
  });

  it('keeps duplicate-prone creation visibly disabled', async () => {
    renderConsole();
    expect(await screen.findByText('Primary Xray')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'subscriptionTemplates.createAction' })).toBeDisabled();
    expect(createTemplate).not.toHaveBeenCalled();
  });

  it('updates only name, templateJson, and encodedTemplateYaml and reports pending', async () => {
    const user = userEvent.setup();
    renderConsole();
    await user.click(await screen.findByRole('button', { name: 'common.edit' }));

    const name = screen.getByLabelText('common.name', { selector: 'input' });
    fireEvent.change(name, { target: { value: 'Primary Xray 3.4' } });
    const templateJson = screen.getByLabelText('subscriptionTemplates.fields.templateJson', { selector: 'textarea' });
    fireEvent.change(templateJson, { target: { value: '{"outbounds":[{"tag":"direct"}]}' } });
    const yaml = screen.getByLabelText('subscriptionTemplates.fields.encodedTemplateYaml', { selector: 'textarea' });
    fireEvent.change(yaml, { target: { value: 'bWl4ZWQtcG9ydDogNzg5MA==' } });
    await user.click(screen.getByRole('button', { name: 'common.save' }));

    await waitFor(() => expect(updateTemplate).toHaveBeenCalledTimes(1));
    expect(updateTemplate).toHaveBeenCalledWith(template.uuid, {
      name: 'Primary Xray 3.4',
      templateJson: { outbounds: [{ tag: 'direct' }] },
      encodedTemplateYaml: 'bWl4ZWQtcG9ydDogNzg5MA==',
    });
    expect(await screen.findByRole('status')).toHaveTextContent('subscriptionTemplates.updatePending');
  });

  it('rejects non-object template JSON before any mutation', async () => {
    const user = userEvent.setup();
    renderConsole();
    await user.click(await screen.findByRole('button', { name: 'common.edit' }));
    const templateJson = screen.getByLabelText('subscriptionTemplates.fields.templateJson', { selector: 'textarea' });
    fireEvent.change(templateJson, { target: { value: '[]' } });
    await user.click(screen.getByRole('button', { name: 'common.save' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('subscriptionTemplates.validation.jsonObjectRequired');
    expect(updateTemplate).not.toHaveBeenCalled();
  });
});
