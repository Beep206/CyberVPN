import type { ChangeEvent, ReactNode } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AntiphishingModal } from '../AntiphishingModal';
import { ChangePasswordModal } from '../ChangePasswordModal';
import { TwoFactorModal } from '../TwoFactorModal';

const apiMocks = vi.hoisted(() => ({
  getAntiphishingCode: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useTranslations: (namespace: string) => (key: string, params?: Record<string, unknown>) =>
    params ? `${namespace}.${key} ${JSON.stringify(params)}` : `${namespace}.${key}`,
}));

vi.mock('@/shared/ui/modal', () => ({
  Modal: ({
    children,
    isOpen,
    title,
  }: {
    children: ReactNode;
    isOpen: boolean;
    title?: string;
  }) => (isOpen ? <section aria-label={title}>{children}</section> : null),
}));

vi.mock('@/features/auth/components/CyberInput', () => ({
  CyberInput: ({
    disabled,
    error,
    label,
    onChange,
    placeholder,
    type = 'text',
    value,
  }: {
    disabled?: boolean;
    error?: string;
    label: string;
    onChange: (event: ChangeEvent<HTMLInputElement>) => void;
    placeholder?: string;
    type?: string;
    value: string;
  }) => (
    <label>
      {label}
      <input
        disabled={disabled}
        onChange={onChange}
        placeholder={placeholder}
        type={type}
        value={value}
      />
      {error ? <span role="alert">{error}</span> : null}
    </label>
  ),
}));

vi.mock('@/features/auth/components/PasswordStrengthMeter', () => ({
  PasswordStrengthMeter: () => <div data-testid="password-strength-meter" />,
}));

vi.mock('@/lib/api/security', () => ({
  securityApi: {
    getAntiphishingCode: apiMocks.getAntiphishingCode,
  },
}));

vi.mock('@/lib/api/twofa', () => ({
  twofaApi: {
    disable: vi.fn(),
    reauth: vi.fn(),
    setup: vi.fn(),
    verify: vi.fn(),
  },
}));

describe('settings security modals i18n', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getAntiphishingCode.mockResolvedValue({ data: { code: null } });
  });

  it('renders 2FA enable and disable copy from the settings security flow namespace', () => {
    const noop = () => undefined;

    const { rerender } = render(
      <TwoFactorModal isEnabled={false} isOpen onClose={noop} onSuccess={noop} />,
    );

    expect(
      screen.getByRole('region', {
        name: 'Settings.cabinet.securityFlows.twoFactor.modalTitleEnable',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Settings.cabinet.securityFlows.twoFactor.reauth.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Settings.cabinet.securityFlows.twoFactor.password.label'),
    ).toHaveAttribute(
      'placeholder',
      'Settings.cabinet.securityFlows.twoFactor.password.placeholder',
    );
    expect(
      screen.getByRole('button', {
        name: 'Settings.cabinet.securityFlows.twoFactor.actions.continue',
      }),
    ).toBeInTheDocument();

    rerender(<TwoFactorModal isEnabled isOpen onClose={noop} onSuccess={noop} />);

    expect(
      screen.getByRole('region', {
        name: 'Settings.cabinet.securityFlows.twoFactor.modalTitleDisable',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Settings.cabinet.securityFlows.twoFactor.disable.title'),
    ).toBeInTheDocument();
  });

  it('renders password change copy from settings and password-strength namespaces', () => {
    const noop = () => undefined;

    render(<ChangePasswordModal isOpen onClose={noop} onSuccess={noop} />);

    expect(
      screen.getByRole('region', {
        name: 'Settings.cabinet.securityFlows.password.modalTitle',
      }),
    ).toBeInTheDocument();
    expect(screen.getByText('Settings.cabinet.securityFlows.password.title')).toBeInTheDocument();
    expect(
      screen.getByLabelText('Settings.cabinet.securityFlows.password.current.label'),
    ).toHaveAttribute(
      'placeholder',
      'Settings.cabinet.securityFlows.password.current.placeholder',
    );
    expect(screen.getByTestId('password-strength-meter')).toBeInTheDocument();
  });

  it('renders anti-phishing states from the settings security flow namespace', async () => {
    const noop = () => undefined;

    render(<AntiphishingModal isOpen onClose={noop} onSuccess={noop} />);

    expect(
      screen.getByRole('region', {
        name: 'Settings.cabinet.securityFlows.antiphishing.modalTitle',
      }),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.getByText('Settings.cabinet.securityFlows.antiphishing.empty.title'),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole('button', {
        name: 'Settings.cabinet.securityFlows.antiphishing.actions.create',
      }),
    ).toBeInTheDocument();
  });
});
