import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DocsContainer } from '../docs-container';
import { PrivacyDashboard } from '../privacy/privacy-dashboard';
import { TermsDashboard } from '../terms/terms-dashboard';
import { ApiDashboard } from '../api/api-dashboard';

vi.mock('../docs-sidebar', () => ({
  DocsSidebar: () => <div data-testid="docs-sidebar-stub">sidebar</div>,
}));

vi.mock('../docs-interactive-rail', () => ({
  DocsInteractiveRail: () => (
    <>
      <div data-testid="docs-container-sidebar" className="order-2 lg:order-1 lg:col-span-3">
        sidebar
      </div>
      <div
        data-testid="docs-container-scene"
        className="order-3 hidden lg:block lg:col-span-3 pointer-events-none"
      >
        scene
      </div>
    </>
  ),
}));

vi.mock('../privacy/privacy-index', () => ({
  PrivacyIndex: () => <div data-testid="privacy-index-stub">privacy index</div>,
}));

vi.mock('../privacy/privacy-content', () => ({
  PrivacyContent: () => <div data-testid="privacy-content-stub">privacy content</div>,
}));

vi.mock('../terms/compliance-scanner', () => ({
  ComplianceScanner: () => (
    <div data-testid="terms-scanner-stub">terms scanner</div>
  ),
}));

vi.mock('../terms/terms-content', () => ({
  TermsContent: () => <div data-testid="terms-content-stub">terms content</div>,
}));

vi.mock('../terms/signature-terminal', () => ({
  SignatureTerminal: () => (
    <div data-testid="terms-signature-stub">signature terminal</div>
  ),
}));

vi.mock('../api/endpoints-sidebar', () => ({
  EndpointsSidebar: () => <div data-testid="api-sidebar-stub">api sidebar</div>,
}));

vi.mock('../api/endpoint-details', () => ({
  EndpointDetails: () => <div data-testid="api-details-stub">api details</div>,
}));

vi.mock('../api/code-terminal', () => ({
  CodeTerminal: () => <div data-testid="api-terminal-stub">api terminal</div>,
}));

describe('Content-heavy route shells', () => {
  it('renders docs content before the table of contents on mobile', () => {
    render(<DocsContainer />);

    const layout = screen.getByTestId('docs-container-layout');
    const content = screen.getByTestId('docs-container-content');
    const sidebar = screen.getByTestId('docs-container-sidebar');

    expect(Array.from(layout.children)[0]).toBe(content);
    expect(content.className).toContain('order-1');
    expect(sidebar.className).toContain('order-2');
    expect(sidebar.className).toContain('lg:order-1');
  });

  it('keeps privacy and terms routes out of inner mobile scroll traps', () => {
    const { rerender } = render(<PrivacyDashboard />);

    expect(screen.getByTestId('privacy-dashboard-content').className).not.toContain(
      'overflow-y-auto',
    );

    rerender(<TermsDashboard />);

    expect(screen.getByTestId('terms-dashboard-content').className).not.toContain(
      'overflow-y-auto',
    );
  });

  it('keeps the api route shell in document flow instead of nested shell scrolling', () => {
    render(<ApiDashboard />);

    expect(screen.getByTestId('api-dashboard-main').className).not.toContain(
      'overflow-y-auto',
    );
  });
});
