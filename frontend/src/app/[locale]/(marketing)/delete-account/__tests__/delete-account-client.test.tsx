import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DeleteAccountClient } from '@/widgets/delete-account/delete-account-client';

const apiMocks = vi.hoisted(() => ({
  isAuthenticated: true,
  requestPrivacyAction: vi.fn(),
}));

const messages = {
  DeleteAccount: {
    contact: {
      description: 'Contact privacy support.',
      email: 'Email',
      emailAddress: 'privacy@cyber-vpn.net',
      title: 'Need help?',
    },
    error: {
      message: 'Request failed.',
      unauthenticated: 'You must be logged in to request account deletion.',
    },
    form: {
      cancel: 'Cancel',
      cancelToSettings: 'Back to settings',
      description: 'Type DELETE and confirm manual review.',
      fields: {
        confirmation: {
          error: 'You must confirm manual review.',
          label: 'I understand this starts a permanent deletion review.',
        },
        confirmInput: {
          error: 'Type DELETE to continue.',
          keyword: 'DELETE',
          label: 'Type DELETE to confirm',
          placeholder: 'DELETE',
        },
        feedback: {
          label: 'Additional feedback',
          placeholder: 'Add context for privacy support',
        },
        reason: {
          label: 'Reason for deletion',
          options: {
            foundAlternative: 'Found an alternative',
            notUsing: 'Not using the service',
            other: 'Other',
            privacyConcerns: 'Privacy concerns',
            technicalIssues: 'Technical issues',
            tooExpensive: 'Too expensive',
          },
          placeholder: 'Select a reason',
        },
      },
      submit: 'Submit deletion request',
      submitting: 'Submitting...',
      title: 'Delete account request',
    },
    sections: {
      alternativeOptions: {
        description: 'Try these first.',
        items: {
          changeSettings: 'Change settings',
          contactSupport: 'Contact support',
          pauseSubscription: 'Pause subscription',
        },
        title: 'Alternative options',
      },
      beforeDelete: {
        items: {
          cancelSubscriptions: 'Cancel subscriptions',
          exportData: 'Export data',
          saveConfigs: 'Save configs',
          useReferrals: 'Use rewards',
        },
        title: 'Before you delete',
      },
      consequences: {
        items: {
          accountData: 'Account data',
          configs: 'VPN configurations',
          referrals: 'Referral data',
          subscriptions: 'Subscription handling follows provider rules',
          support: 'Support history',
        },
        title: 'What will be deleted',
      },
    },
    subtitle: 'Submit a manual deletion review',
    success: {
      details: 'Target fulfillment is within {days} days after verification.',
      message: 'Your account deletion request is queued for manual privacy review.',
      reference: 'Reference: {reference}',
      returnHome: 'Return home',
      returnSettings: 'Return to settings',
      title: 'Deletion request submitted',
    },
    title: 'Delete account request',
    warning: {
      message: 'Verified deletion requests are reviewed before final processing.',
      title: 'Manual review before deletion',
    },
  },
};

function readMessage(path: string) {
  return path.split('.').reduce<unknown>((current, segment) => {
    if (current && typeof current === 'object' && segment in current) {
      return (current as Record<string, unknown>)[segment];
    }

    return undefined;
  }, messages);
}

vi.mock('next-intl', () => ({
  useTranslations: (namespace: string) => (key: string, params?: Record<string, string | number>) => {
    const value = readMessage(`${namespace}.${key}`);
    const template = typeof value === 'string' ? value : key;

    return Object.entries(params ?? {}).reduce(
      (result, [paramKey, paramValue]) => result.replace(`{${paramKey}}`, String(paramValue)),
      template,
    );
  },
}));

vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: { children: ReactNode }) => <div {...props}>{children}</div>,
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
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('@/lib/api', () => ({
  authApi: {
    requestPrivacyAction: apiMocks.requestPrivacyAction,
  },
}));

vi.mock('@/stores/auth-store', () => ({
  useIsAuthenticated: () => apiMocks.isAuthenticated,
}));

describe('DeleteAccountClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.isAuthenticated = true;
    apiMocks.requestPrivacyAction.mockResolvedValue({
      data: {
        manual_fulfillment_target_days: 30,
        ticket_reference: 's1sup-web-p1-account_deletion',
      },
    });
  });

  it('submits account deletion as a manual privacy request with localized outcome', async () => {
    const user = userEvent.setup();
    render(<DeleteAccountClient />);

    await user.selectOptions(screen.getByLabelText('Reason for deletion'), 'privacyConcerns');
    await user.type(screen.getByLabelText('Additional feedback'), 'Please remove my account data.');
    await user.type(screen.getByLabelText('Type DELETE to confirm'), 'DELETE');
    await user.click(screen.getByRole('checkbox', {
      name: 'I understand this starts a permanent deletion review.',
    }));
    await user.click(screen.getByRole('button', { name: 'Submit deletion request' }));

    await waitFor(() => {
      expect(apiMocks.requestPrivacyAction).toHaveBeenCalledWith({
        notes: 'reason=privacyConcerns\nfeedback=Please remove my account data.',
        request_type: 'account_deletion',
      });
    });
    expect(await screen.findByText('Deletion request submitted')).toBeInTheDocument();
    expect(screen.getByText('Target fulfillment is within 30 days after verification.')).toBeInTheDocument();
    expect(screen.getByText('Reference: s1sup-web-p1-account_deletion')).toBeInTheDocument();
  });

  it('blocks unauthenticated deletion requests before calling the API', async () => {
    apiMocks.isAuthenticated = false;
    const user = userEvent.setup();
    render(<DeleteAccountClient />);

    await user.type(screen.getByLabelText('Type DELETE to confirm'), 'DELETE');
    await user.click(screen.getByRole('checkbox', {
      name: 'I understand this starts a permanent deletion review.',
    }));
    await user.click(screen.getByRole('button', { name: 'Submit deletion request' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'You must be logged in to request account deletion.',
    );
    expect(apiMocks.requestPrivacyAction).not.toHaveBeenCalled();
  });

  it('keeps cabinet deletion flow inside settings navigation', async () => {
    const user = userEvent.setup();
    render(<DeleteAccountClient cancelHref="/settings" returnHref="/settings" surface="cabinet" />);

    expect(screen.getByRole('link', { name: 'Back to settings' })).toHaveAttribute(
      'href',
      '/settings',
    );

    await user.type(screen.getByLabelText('Type DELETE to confirm'), 'DELETE');
    await user.click(screen.getByRole('checkbox', {
      name: 'I understand this starts a permanent deletion review.',
    }));
    await user.click(screen.getByRole('button', { name: 'Submit deletion request' }));

    expect(await screen.findByRole('link', { name: 'Return to settings' })).toHaveAttribute(
      'href',
      '/settings',
    );
  });
});
