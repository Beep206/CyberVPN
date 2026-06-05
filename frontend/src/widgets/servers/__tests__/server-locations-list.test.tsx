import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ServerLocationsList } from '../server-locations-list';

vi.mock('next-intl', () => ({
  useLocale: () => 'en-US',
  useTranslations: () => (key: string) => {
    const labels: Record<string, string> = {
      'telemetry.regionsUnavailableTitle': 'Region telemetry unavailable',
      'telemetry.regionsUnavailableDescription': 'Current public regions could not be loaded.',
      'telemetry.emptyRegionsTitle': 'No public regions published',
      'telemetry.emptyRegionsDescription': 'Region data is temporarily unavailable for public display.',
    };

    return labels[key] ?? key;
  },
}));

describe('ServerLocationsList', () => {
  it('renders an explicit degraded state when region telemetry fails', () => {
    render(
      <ServerLocationsList
        activeNodeId={null}
        isError
        regions={[]}
        setActiveNodeId={vi.fn()}
      />,
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Region telemetry unavailable')).toBeInTheDocument();
    expect(screen.getByText('Current public regions could not be loaded.')).toBeInTheDocument();
  });

  it('renders an explicit empty state after a successful empty region response', () => {
    render(
      <ServerLocationsList
        activeNodeId={null}
        isLoading={false}
        regions={[]}
        setActiveNodeId={vi.fn()}
      />,
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('No public regions published')).toBeInTheDocument();
    expect(screen.getByText('Region data is temporarily unavailable for public display.')).toBeInTheDocument();
  });
});
