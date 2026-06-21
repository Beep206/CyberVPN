import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AxiosError, AxiosHeaders } from 'axios';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

const apiMocks = vi.hoisted(() => ({
  changeWorkspaceCodeLifecycle: vi.fn(),
  createWorkspaceCode: vi.fn(),
  createWorkspaceCodeLink: vi.fn(),
  createWorkspaceCodeQr: vi.fn(),
}));

const mockRuntimeState = vi.fn<
  () => {
    state: PartnerPortalState;
    activeWorkspace: { id: string; display_name: string } | null;
    queries: {
      workspaceCodesQuery: {
        data: unknown;
        error: unknown;
        isError: boolean;
        isLoading: boolean;
      };
      workspaceCommercialCapabilitiesQuery: {
        data: {
          can_write_codes: boolean;
          available_actions: string[];
        } | null;
        isLoading: boolean;
      };
    };
  }
>(() => ({
  state: {
    ...createPartnerPortalScenarioState('active', 'creator_affiliate', 'workspace_owner', 'R4'),
    codes: [
      {
        id: 'code-1',
        label: 'ALPHA42',
        kind: 'starter_code',
        status: 'active',
        destination: '/register',
        shareUrl: 'https://cyber-vpn.net/p/alpha42',
        destinationPath: '/register',
        version: 7,
        createdAt: '2026-06-20T10:00:00Z',
        updatedAt: '2026-06-21T10:00:00Z',
        availableActions: ['create_link', 'download_qr', 'revoke', 'archive'],
        notes: [],
      },
    ],
  },
  activeWorkspace: { id: 'workspace-1', display_name: 'Workspace One' },
  queries: {
    workspaceCodesQuery: {
      data: [],
      error: null,
      isError: false,
      isLoading: false,
    },
    workspaceCommercialCapabilitiesQuery: {
      data: {
        can_write_codes: true,
        available_actions: ['list_codes', 'create_link', 'download_qr', 'revoke', 'archive'],
      },
      isLoading: false,
    },
  },
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string, values?: Record<string, string>) => {
    if (!values) return key;
    return `${key}:${Object.entries(values).map(([name, value]) => `${name}=${value}`).join(',')}`;
  },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...props
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => <a href={href} {...props}>{children}</a>,
}));

vi.mock('@/lib/api/partner-portal', () => ({
  partnerPortalApi: apiMocks,
}));

vi.mock('@/features/partner-portal-state/components/partner-route-guard', () => ({
  PartnerRouteGuard: ({
    children,
  }: {
    children: (access: 'read' | 'write' | 'admin' | 'none') => ReactNode;
  }) => <>{children('write')}</>,
}));

vi.mock('@/features/partner-portal-state/lib/use-partner-portal-runtime-state', () => ({
  usePartnerPortalRuntimeState: () => mockRuntimeState(),
}));

vi.mock('@/shared/ui/admin-action-dialog', () => ({
  AdminActionDialog: ({
    isOpen,
    title,
    confirmLabel,
    onConfirm,
  }: {
    isOpen: boolean;
    title: string;
    confirmLabel: string;
    onConfirm: () => Promise<void>;
  }) => (
    isOpen
      ? (
        <div role="dialog" aria-label={title}>
          <button type="button" onClick={() => void onConfirm()}>
            {confirmLabel}
          </button>
        </div>
      )
      : null
  ),
}));

import { CodesTrackingPage } from './codes-tracking-page';

function renderCodesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <CodesTrackingPage />
    </QueryClientProvider>,
  );
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

describe('CodesTrackingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.createWorkspaceCodeLink.mockResolvedValue({
      data: {
        share_url: 'https://cyber-vpn.net/p/generated-alpha42',
      },
    });
    apiMocks.createWorkspaceCodeQr.mockResolvedValue({
      data: {
        qr_svg: '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10" /></svg>',
      },
    });
    apiMocks.changeWorkspaceCodeLifecycle.mockResolvedValue({ data: {} });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: undefined,
    });
  });

  it('uses backend capabilities and shows clipboard success feedback', async () => {
    renderCodesPage();

    expect(screen.getByText('capabilities.backendAction:value=create_link')).toBeInTheDocument();
    expect(screen.queryByText('capabilities.items.starter_code')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'buttons.copy' }));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('https://cyber-vpn.net/p/alpha42');
    expect(await screen.findByRole('status')).toHaveTextContent('feedback.copySuccess');
    expect(screen.getByText('inventory.audit:value=2026-06-21T10:00:00Z')).toBeInTheDocument();
  });

  it('uses Web Share API when available and reports share success', async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: share,
    });

    renderCodesPage();

    await userEvent.click(screen.getByRole('button', { name: 'buttons.share' }));

    await waitFor(() => {
      expect(share).toHaveBeenCalledWith({
        title: 'share.title:code=ALPHA42',
        text: 'share.text:code=ALPHA42',
        url: 'https://cyber-vpn.net/p/alpha42',
      });
    });
    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
    expect(await screen.findByRole('status')).toHaveTextContent('feedback.shareSuccess');
  });

  it('falls back to clipboard sharing when Web Share API is unavailable', async () => {
    renderCodesPage();

    await userEvent.click(screen.getByRole('button', { name: 'buttons.share' }));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('https://cyber-vpn.net/p/alpha42');
    expect(await screen.findByRole('status')).toHaveTextContent('feedback.copySuccess');
  });

  it('creates a QR code and downloads the generated SVG', async () => {
    const createObjectURL = vi.fn(() => 'blob:qr-alpha42');
    const revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectURL,
    });

    renderCodesPage();

    await userEvent.click(screen.getByRole('button', { name: 'buttons.qr' }));

    await waitFor(() => {
      expect(apiMocks.createWorkspaceCodeQr).toHaveBeenCalledWith('workspace-1', 'code-1', {
        destination_path: '/register',
        size: 256,
      });
    });
    expect(await screen.findByRole('status')).toHaveTextContent('feedback.qrSuccess');

    await userEvent.click(screen.getByRole('button', { name: 'buttons.downloadQr' }));

    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:qr-alpha42');
    expect(await screen.findByRole('status')).toHaveTextContent('feedback.qrDownloadSuccess');
  });

  it('keeps pending state scoped to the link mutation for one code', async () => {
    const pendingLink = deferred<{ data: { share_url: string } }>();
    apiMocks.createWorkspaceCodeLink.mockReturnValue(pendingLink.promise);

    renderCodesPage();

    const linkButton = screen.getByRole('button', { name: 'buttons.link' });
    const qrButton = screen.getByRole('button', { name: 'buttons.qr' });

    await userEvent.click(linkButton);

    expect(linkButton).toBeDisabled();
    expect(qrButton).not.toBeDisabled();

    pendingLink.resolve({
      data: {
        share_url: 'https://cyber-vpn.net/p/generated-alpha42',
      },
    });

    await waitFor(() => {
      expect(linkButton).not.toBeDisabled();
    });
  });

  it('confirms archive with the correct lifecycle mutation reason', async () => {
    renderCodesPage();

    await userEvent.click(screen.getByRole('button', { name: 'buttons.archive' }));
    const dialog = screen.getByRole('dialog', { name: 'confirm.archive.title' });
    expect(dialog).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole('button', { name: 'buttons.archive' }));

    await waitFor(() => {
      expect(apiMocks.changeWorkspaceCodeLifecycle).toHaveBeenCalledWith(
        'workspace-1',
        'code-1',
        'archive',
        { reason: 'partner_portal_archive' },
        7,
      );
    });
  });

  it('confirms revoke and recovers from version conflicts', async () => {
    apiMocks.changeWorkspaceCodeLifecycle.mockRejectedValueOnce(
      new AxiosError('conflict', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 409,
        statusText: 'Conflict',
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: {},
      }),
    );

    renderCodesPage();

    await userEvent.click(screen.getByRole('button', { name: 'buttons.revoke' }));
    const dialog = screen.getByRole('dialog', { name: 'confirm.revoke.title' });
    expect(dialog).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole('button', { name: 'buttons.revoke' }));

    await waitFor(() => {
      expect(apiMocks.changeWorkspaceCodeLifecycle).toHaveBeenCalledWith(
        'workspace-1',
        'code-1',
        'revoke',
        { reason: 'partner_portal_revoke' },
        7,
      );
    });
    expect(await screen.findByRole('alert')).toHaveTextContent('feedback.versionConflict');
  });
});
