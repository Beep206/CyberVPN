import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DocsContentServer } from '../docs-content-server';

const messages = {
  title: 'NEURAL BLUEPRINTS',
  subtitle: 'SYSTEM DOCUMENTATION & SCHEMATICS',
  meta_description:
    'Comprehensive schematics and guides for integrating and utilizing the CyberVPN network.',
  section_getting_started: 'INITIALIZATION',
  section_routing: 'SIGNAL ROUTING',
  section_security: 'ENCRYPTION PROTOCOLS',
  section_api: 'NEURAL API',
  doc_install_title: 'Core Installation',
  doc_install_desc: 'Deploy the core engine on supported physical architectures.',
  doc_config_title: 'Configuring Tunnels',
  doc_config_desc: 'Establish secure pathways through hostile networks.',
  doc_protocols_title: 'Supported Protocols',
  doc_protocols_desc: 'Specifications for VLESS, VMess, and Trojan Reality.',
} as const;

vi.mock('next-intl/server', () => ({
  getTranslations: vi.fn(async () => (key: keyof typeof messages) => messages[key] ?? key),
}));

describe('DocsContentServer', () => {
  it('renders docs headings and setup content in server HTML', async () => {
    render(await DocsContentServer());

    expect(
      screen.getByRole('heading', { name: 'NEURAL BLUEPRINTS' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Core Installation' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/curl -sL https:\/\/cybervpn\.net\/install\.sh \| bash/),
    ).toBeInTheDocument();
  });

  it('keeps advanced docs knowledge visible without client navigation state', async () => {
    render(await DocsContentServer());

    expect(
      screen.getByRole('heading', { name: 'Neural API Interface' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Integrate directly with the VPN core/i),
    ).toBeInTheDocument();
  });
});
