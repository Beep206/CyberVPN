import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { UsersDataGrid } from '../users-data-grid';

vi.mock('@/shared/ui/atoms/cypher-text', () => ({
  CypherText: ({ text }: { text: string }) => <span>{text}</span>,
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

describe('UsersDataGrid', () => {
  it('renders a mobile list view for primary user workflows', () => {
    render(<UsersDataGrid />);

    const mobileList = screen.getByTestId('users-mobile-list');

    expect(mobileList).toBeInTheDocument();
    expect(within(mobileList).getByText('neo@matrix.net')).toBeInTheDocument();
    expect(within(mobileList).getByText('2 mins ago')).toBeInTheDocument();
  });

  it('keeps the dense table available on desktop breakpoints', () => {
    render(<UsersDataGrid />);

    expect(screen.getByTestId('users-desktop-table').className).toContain(
      'hidden md:block',
    );
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('lets search controls wrap instead of forcing width overflow', () => {
    render(<UsersDataGrid />);

    expect(screen.getByTestId('users-grid-toolbar').className).toContain(
      'flex-col',
    );
    expect(screen.getByPlaceholderText('searchPlaceholder').className).toContain(
      'w-full',
    );
  });
});
