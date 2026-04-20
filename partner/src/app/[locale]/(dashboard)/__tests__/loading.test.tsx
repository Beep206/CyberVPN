import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import DashboardLoading from '../loading';

describe('DashboardLoading', () => {
  it('renders loading skeleton with aria label', () => {
    render(<DashboardLoading />);
    expect(
      screen.getByLabelText('Loading dashboard content'),
    ).toBeInTheDocument();
  });

  it('renders stats row skeletons', () => {
    const { container } = render(<DashboardLoading />);
    // 4 stat cards in the grid
    const statCards = container.querySelectorAll('.grid > div');
    expect(statCards).toHaveLength(4);
  });

  it('renders data grid skeleton with rows', () => {
    const { container } = render(<DashboardLoading />);
    // 6 table row skeletons + 1 header row
    const borderRows = container.querySelectorAll('.border-b');
    expect(borderRows.length).toBeGreaterThanOrEqual(7);
  });
});
