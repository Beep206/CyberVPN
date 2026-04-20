import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockSelectionState = vi.fn();

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/features/partner-portal-state/lib/use-partner-workspace-selection', () => ({
  usePartnerWorkspaceSelection: () => mockSelectionState(),
}));

import { PartnerWorkspaceSwitcher } from './partner-workspace-switcher';

describe('PartnerWorkspaceSwitcher', () => {
  beforeEach(() => {
    mockSelectionState.mockReset();
    mockSelectionState.mockReturnValue({
      workspaces: [
        {
          id: 'workspace_001',
          display_name: 'North Star Growth Studio',
          account_key: 'north-star',
          status: 'active',
        },
        {
          id: 'workspace_002',
          display_name: 'Nebula Performance Lab',
          account_key: 'nebula',
          status: 'restricted',
        },
      ],
      activeWorkspace: {
        id: 'workspace_001',
        display_name: 'North Star Growth Studio',
        account_key: 'north-star',
        status: 'active',
      },
      isSwitching: false,
      selectWorkspace: vi.fn(),
      workspacesQuery: {
        isLoading: false,
      },
    });
  });

  it('renders the canonical workspace selector and current workspace posture', () => {
    render(<PartnerWorkspaceSwitcher />);

    expect(screen.getByText('label')).toBeInTheDocument();
    expect(
      screen.getByRole('combobox', {
        name: 'inputLabel',
      }),
    ).toHaveValue('workspace_001');
    expect(screen.getByText('north-star')).toBeInTheDocument();
    expect(screen.getByText('workspaceStatuses.active')).toBeInTheDocument();
  });

  it('submits explicit workspace changes from the selector', async () => {
    const user = userEvent.setup();
    const selectWorkspace = vi.fn();

    mockSelectionState.mockReturnValue({
      workspaces: [
        {
          id: 'workspace_001',
          display_name: 'North Star Growth Studio',
          account_key: 'north-star',
          status: 'active',
        },
        {
          id: 'workspace_002',
          display_name: 'Nebula Performance Lab',
          account_key: 'nebula',
          status: 'restricted',
        },
      ],
      activeWorkspace: {
        id: 'workspace_001',
        display_name: 'North Star Growth Studio',
        account_key: 'north-star',
        status: 'active',
      },
      isSwitching: false,
      selectWorkspace,
      workspacesQuery: {
        isLoading: false,
      },
    });

    render(<PartnerWorkspaceSwitcher compact />);

    await user.selectOptions(
      screen.getByRole('combobox', {
        name: 'inputLabel',
      }),
      'workspace_002',
    );

    expect(selectWorkspace).toHaveBeenCalledWith('workspace_002');
  });

  it('stays hidden when only one canonical workspace is available', () => {
    mockSelectionState.mockReturnValue({
      workspaces: [
        {
          id: 'workspace_001',
          display_name: 'North Star Growth Studio',
          account_key: 'north-star',
          status: 'active',
        },
      ],
      activeWorkspace: {
        id: 'workspace_001',
        display_name: 'North Star Growth Studio',
        account_key: 'north-star',
        status: 'active',
      },
      isSwitching: false,
      selectWorkspace: vi.fn(),
      workspacesQuery: {
        isLoading: false,
      },
    });

    const { container } = render(<PartnerWorkspaceSwitcher />);

    expect(container).toBeEmptyDOMElement();
  });
});
