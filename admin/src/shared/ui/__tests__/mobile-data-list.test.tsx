import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileDataList } from '../mobile-data-list';

describe('MobileDataList', () => {
  it('renders priority content, label-value rows, status, and actions', () => {
    render(
      <MobileDataList
        items={[
          {
            id: 'srv-1',
            title: 'Tokyo Node 01',
            subtitle: 'wireguard',
            status: <span>online</span>,
            priority: <span>45%</span>,
            primaryFields: [
              { label: 'Location', value: 'Japan, Tokyo' },
              { label: 'IP', value: '45.32.12.90' },
            ],
            secondaryFields: [
              { label: 'Uptime', value: '12d 4h' },
            ],
            actions: <button type="button">Restart</button>,
          },
        ]}
      />
    );

    expect(screen.getByText('Tokyo Node 01')).toBeInTheDocument();
    expect(screen.getByText('online')).toBeInTheDocument();
    expect(screen.getByText('Location')).toBeInTheDocument();
    expect(screen.getByText('Japan, Tokyo')).toBeInTheDocument();
    expect(screen.getByText('Uptime')).toBeInTheDocument();
    expect(screen.getByText('12d 4h')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Restart' })).toBeInTheDocument();
  });
});
