import type { AnchorHTMLAttributes, ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { FeatureMatrix } from '../feature-matrix';
import { TierCards } from '../tier-cards';
import type { PricingAddon, PricingPlanFamily } from '../types';

vi.mock('next-intl', () => ({
  useLocale: () => 'ru-RU',
  useTranslations: () => (key: string, values?: Record<string, string | number>) => {
    const labels: Record<string, string> = {
      'addons.dedicated_ip.availability': 'Available on request',
      'addons.dedicated_ip.description': 'Dedicated address',
      'addons.dedicated_ip.title': 'Dedicated IP',
      'addons.extra_device.availability': '{limits}',
      'addons.extra_device.description': 'Extra device',
      'addons.extra_device.title': 'Extra device',
      'addons.priceLabel': '{price}',
      'addons.subtitle': 'Optional extras',
      'addons.title': 'Add-ons',
      'labels.chargedInBillingCurrency': 'Charged in {currency}',
      'labels.dedicatedIpAddon': 'Dedicated IP add-on',
      'labels.devices': '{count} devices',
      'labels.inviteBundle': '{count} invites',
      'labels.inviteNone': 'No invites',
      'labels.monthlyEquivalent': '{price} / month',
      'labels.perSelectedTerm': '{days} days',
      'labels.trafficFairUse': 'Fair use',
      'matrix.rows.capability': 'Capability',
      'matrix.rows.dedicatedIp': 'Dedicated IP',
      'matrix.rows.devices': 'Devices',
      'matrix.rows.invites': 'Invites',
      'matrix.rows.modes': 'Modes',
      'matrix.rows.serverPool': 'Server pool',
      'matrix.rows.support': 'Support',
      'matrix.rows.traffic': 'Traffic',
      'matrix.subtitle': 'Compare plans',
      'matrix.title': 'Plan matrix',
      'modeNames.standard': 'Standard',
      'poolNames.shared': 'Shared',
      'summary.noInviteBonus': 'No invite bonus',
      'summary.selectedTerm': '{days} days',
      'supportNames.standard': 'Standard support',
      'tiers.basic.audience': 'Individual',
      'tiers.basic.badge': 'Starter',
      'tiers.basic.button': 'Start',
      'tiers.basic.description': 'Basic access',
      'tiers.basic.eyebrow': 'Entry',
    };
    const template = labels[key] ?? key;
    if (!values) return template;
    return Object.entries(values).reduce(
      (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
      template,
    );
  },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...props
  }: { children: ReactNode; href: string } & AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

const basicPlan: PricingPlanFamily = {
  code: 'basic',
  display_name: 'Basic',
  devices_included: 2,
  traffic_policy: {
    mode: 'fair_use',
    display_label: 'Fair use',
    enforcement_profile: 'consumer_entry',
  },
  connection_modes: ['standard'],
  server_pool: ['shared'],
  support_sla: 'standard',
  dedicated_ip: { included: 0, eligible: true },
  features: {},
  periods: [
    {
      uuid: 'basic-30',
      name: 'basic_30',
      duration_days: 30,
      price_usd: 5.99,
      price_rub: 599,
      invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 },
      trial_eligible: false,
      sort_order: 20,
    },
  ],
  sort_order: 20,
  is_active: true,
};

const extraDeviceAddon: PricingAddon = {
  uuid: 'addon-extra-device',
  code: 'extra_device',
  display_name: '+1 device',
  duration_mode: 'inherits_subscription',
  is_stackable: true,
  quantity_step: 1,
  price_usd: 6,
  price_rub: 600,
  max_quantity_by_plan: {
    basic: 2,
  },
  delta_entitlements: {
    device_limit: 1,
  },
  requires_location: false,
  sale_channels: ['web'],
  is_active: true,
};

describe('public pricing copy', () => {
  it('does not render display-only local estimates in public tier cards', () => {
    render(
      <TierCards
        hoveredTier="basic"
        onHover={vi.fn()}
        plans={[basicPlan]}
        selectedPeriod={30}
      />,
    );

    expect(screen.getByText(/Charged in RUB/i)).toBeInTheDocument();
    expect(screen.queryByText(/display only/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/approx/i)).not.toBeInTheDocument();
  });

  it('does not render display-only local estimates in public add-on matrix', () => {
    render(
      <FeatureMatrix
        plans={[basicPlan]}
        addons={[extraDeviceAddon]}
        selectedPeriod={30}
      />,
    );

    expect(screen.getByText('Add-ons')).toBeInTheDocument();
    expect(screen.getAllByText('Extra device').length).toBeGreaterThan(0);
    expect(screen.queryByText(/display only/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/approx/i)).not.toBeInTheDocument();
  });
});
