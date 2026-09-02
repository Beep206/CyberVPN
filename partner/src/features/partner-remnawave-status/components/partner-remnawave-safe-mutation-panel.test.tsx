import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PartnerRemnawaveResource } from '@/lib/api/remnawave-status';

const {
  updateIntegrationMetadata,
  updateProfileTags,
} = vi.hoisted(() => ({
  updateIntegrationMetadata: vi.fn(),
  updateProfileTags: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/lib/api/remnawave-status', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api/remnawave-status')>();
  return {
    ...original,
    partnerRemnawaveStatusApi: {
      ...original.partnerRemnawaveStatusApi,
      updateIntegrationMetadata,
      updateProfileTags,
    },
  };
});

import { PartnerRemnawaveSafeMutationPanel } from './partner-remnawave-safe-mutation-panel';

const WORKSPACE_UUID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const PROFILE_UUID = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const INTEGRATION_UUID = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
const IDEMPOTENCY_UUID = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
const ATTEMPT_UUID = 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee';

function profileResource(overrides: Partial<PartnerRemnawaveResource> = {}): PartnerRemnawaveResource {
  return {
    workspace_id: WORKSPACE_UUID,
    resource_type: 'profile',
    resource_uuid: PROFILE_UUID,
    effective_permissions: ['remnawave_read', 'remnawave_write'],
    available_operations: ['inspect_assignment', 'mutate_resource'],
    unavailable_operations: ['execute_resource'],
    forbidden_operations: ['browser_ssh'],
    provider_details_available: false,
    safe_mutations: ['profile_tags'],
    ...overrides,
  };
}

function integrationResource(): PartnerRemnawaveResource {
  return {
    workspace_id: WORKSPACE_UUID,
    resource_type: 'integration',
    resource_uuid: INTEGRATION_UUID,
    effective_permissions: ['remnawave_read', 'remnawave_write'],
    available_operations: ['inspect_assignment', 'mutate_resource'],
    unavailable_operations: ['execute_resource'],
    forbidden_operations: ['browser_ssh'],
    provider_details_available: false,
    safe_mutations: ['integration_metadata'],
  };
}

function renderPanel(resource: PartnerRemnawaveResource, roleCanWrite = true) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries');
  const refetchQueries = vi.spyOn(queryClient, 'refetchQueries');
  render(
    <QueryClientProvider client={queryClient}>
      <PartnerRemnawaveSafeMutationPanel resource={resource} roleCanWrite={roleCanWrite} />
    </QueryClientProvider>,
  );
  return { invalidateQueries, refetchQueries };
}

describe('PartnerRemnawaveSafeMutationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(crypto, 'randomUUID').mockReturnValue(IDEMPOTENCY_UUID);
  });

  it('does not expose mutation controls unless role and exact grant advertise the safe mutation', () => {
    const { rerender } = render(
      <QueryClientProvider client={new QueryClient()}>
        <PartnerRemnawaveSafeMutationPanel resource={profileResource()} roleCanWrite={false} />
      </QueryClientProvider>,
    );

    expect(screen.getByRole('note')).toHaveTextContent('permission.title');
    expect(screen.queryByRole('button', { name: 'profile.submit' })).not.toBeInTheDocument();

    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <PartnerRemnawaveSafeMutationPanel
          resource={profileResource({
            effective_permissions: ['remnawave_read'],
            available_operations: ['inspect_assignment'],
            unavailable_operations: ['mutate_resource', 'execute_resource'],
            safe_mutations: [],
          })}
          roleCanWrite
        />
      </QueryClientProvider>,
    );

    expect(screen.getByRole('note')).toHaveTextContent('permission.description');
    expect(screen.queryByRole('button', { name: 'profile.submit' })).not.toBeInTheDocument();
    expect(updateProfileTags).not.toHaveBeenCalled();
  });

  it('submits one exact profile-tags request with a fresh browser UUID and refreshes authoritative state', async () => {
    updateProfileTags.mockResolvedValue({
      kind: 'completed',
      value: { resource_uuid: PROFILE_UUID, tags: ['EDGE:RU', 'VISION'] },
    });
    const user = userEvent.setup();
    const { invalidateQueries, refetchQueries } = renderPanel(profileResource());

    await user.type(screen.getByLabelText('profile.label'), 'EDGE:RU, VISION');
    await user.click(screen.getByRole('button', { name: 'profile.submit' }));

    await waitFor(() => {
      expect(updateProfileTags).toHaveBeenCalledWith(
        WORKSPACE_UUID,
        PROFILE_UUID,
        { tags: ['EDGE:RU', 'VISION'] },
        IDEMPOTENCY_UUID,
      );
    });
    expect(updateProfileTags).toHaveBeenCalledTimes(1);
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
    expect(await screen.findByText('success.title')).toBeInTheDocument();
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['partner-remnawave-resources', WORKSPACE_UUID],
    });
    expect(refetchQueries).toHaveBeenCalledWith({
      queryKey: ['partner-remnawave-resource', WORKSPACE_UUID, 'profile', PROFILE_UUID],
      type: 'active',
    });
  });

  it('validates profile tags locally and never sends an unsafe payload', async () => {
    const user = userEvent.setup();
    renderPanel(profileResource());

    await user.type(screen.getByLabelText('profile.label'), 'vision, VISION');
    await user.click(screen.getByRole('button', { name: 'profile.submit' }));

    expect(await screen.findByText('profile.validation.format')).toBeInTheDocument();
    expect(updateProfileTags).not.toHaveBeenCalled();
    expect(crypto.randomUUID).not.toHaveBeenCalled();
  });

  it('locks the form after a 202 reconciliation receipt and never retries automatically', async () => {
    updateProfileTags.mockResolvedValue({
      kind: 'reconciliation_required',
      receipt: {
        attempt_id: ATTEMPT_UUID,
        state: 'reconciliation_required',
        resource_type: 'profile',
        resource_uuid: PROFILE_UUID,
        requires_reconciliation: true,
      },
    });
    const user = userEvent.setup();
    renderPanel(profileResource());

    await user.type(screen.getByLabelText('profile.label'), 'VISION');
    await user.click(screen.getByRole('button', { name: 'profile.submit' }));

    expect(await screen.findByText('reconciliation.title')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'profile.submit' })).toBeDisabled();
    expect(screen.getByLabelText('profile.label')).toBeDisabled();
    expect(updateProfileTags).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('button', { name: 'retrySameKey' })).not.toBeInTheDocument();
  });

  it('replays an ambiguous browser failure only after a click and with the same key', async () => {
    updateProfileTags
      .mockRejectedValueOnce(new Error('network response lost'))
      .mockResolvedValueOnce({
        kind: 'accepted',
        receipt: {
          attempt_id: ATTEMPT_UUID,
          state: 'accepted',
          resource_type: 'profile',
          resource_uuid: PROFILE_UUID,
          requires_reconciliation: false,
        },
      });
    const user = userEvent.setup();
    renderPanel(profileResource());

    await user.type(screen.getByLabelText('profile.label'), 'VISION');
    await user.click(screen.getByRole('button', { name: 'profile.submit' }));
    const retryButton = await screen.findByRole('button', { name: 'retrySameKey' });

    expect(updateProfileTags).toHaveBeenCalledTimes(1);
    await user.click(retryButton);
    await waitFor(() => expect(updateProfileTags).toHaveBeenCalledTimes(2));
    expect(updateProfileTags.mock.calls[1]).toEqual(updateProfileTags.mock.calls[0]);
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
    expect(await screen.findByText('success.title')).toBeInTheDocument();
  });

  it('sends integration name and description only, including an explicit description clear', async () => {
    updateIntegrationMetadata.mockResolvedValue({
      kind: 'completed',
      value: {
        resource_uuid: INTEGRATION_UUID,
        name: 'Usage relay',
        description: null,
      },
    });
    const user = userEvent.setup();
    renderPanel(integrationResource());

    await user.type(screen.getByLabelText('integration.nameLabel'), 'Usage relay');
    await user.click(screen.getByRole('checkbox', { name: 'integration.clearDescription' }));
    await user.click(screen.getByRole('button', { name: 'integration.submit' }));

    await waitFor(() => {
      expect(updateIntegrationMetadata).toHaveBeenCalledWith(
        WORKSPACE_UUID,
        INTEGRATION_UUID,
        { name: 'Usage relay', description: null },
        IDEMPOTENCY_UUID,
      );
    });
    const serializedCall = JSON.stringify(updateIntegrationMetadata.mock.calls[0]);
    expect(serializedCall).not.toContain('config');
    expect(serializedCall).not.toContain('restart');
    expect(serializedCall).not.toContain('topology');
    expect(serializedCall).not.toContain('ssh');
    expect(await screen.findByText('success.completed')).toBeInTheDocument();
  });
});
