import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RuleBuilderShell } from '../rule-builder-shell';

const {
  mockGetGrowthRuleCatalog,
  mockCompileGrowthRule,
  mockSimulateGrowthRule,
} = vi.hoisted(() => ({
  mockGetGrowthRuleCatalog: vi.fn(),
  mockCompileGrowthRule: vi.fn(),
  mockSimulateGrowthRule: vi.fn(),
}));

vi.mock('@/lib/api/growth', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/growth')>('@/lib/api/growth');
  return {
    ...actual,
    growthApi: {
      ...actual.growthApi,
      getGrowthRuleCatalog: (...args: unknown[]) => mockGetGrowthRuleCatalog(...args),
      compileGrowthRule: (...args: unknown[]) => mockCompileGrowthRule(...args),
      simulateGrowthRule: (...args: unknown[]) => mockSimulateGrowthRule(...args),
    },
  };
});

const catalog = {
  catalog_version: 'growth-rule-catalog.v1',
  schema_version: 'growth-rule.v1',
  limits: {
    max_nodes: 32,
    max_depth: 6,
    max_actions: 8,
    max_regex_length: 120,
  },
  fields: {
    'code.code_type': { type: 'string', operators: ['eq', 'in'] },
    'checkout.currency': { type: 'string', operators: ['eq', 'in', 'not_in'] },
    'risk.score': { type: 'decimal', operators: ['eq', 'gte', 'lte'] },
  },
  operators: {
    eq: { value_types: ['string', 'decimal'] },
    gte: { value_types: ['decimal'] },
    in: { value_types: ['list'] },
    not_in: { value_types: ['list'] },
  },
  actions: {
    allow: { result: 'allow', params: [] },
    challenge: { result: 'challenge', params: ['challenge_type', 'message_key'] },
  },
};

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

function getAstEditor(): HTMLTextAreaElement {
  return screen.getByLabelText('rules.editor.astLabel') as HTMLTextAreaElement;
}

function getFirstButton(name: string): HTMLElement {
  const button = screen.getAllByRole('button', { name })[0];
  if (!button) {
    throw new Error(`Button not found: ${name}`);
  }
  return button;
}

describe('RuleBuilderShell', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockGetGrowthRuleCatalog.mockResolvedValue({ data: { catalog } });
    mockCompileGrowthRule.mockResolvedValue({
      data: {
        schema_version: 'growth-rule.v1',
        catalog_version: 'growth-rule-catalog.v1',
        normalized_ast: {
          schema_version: 'growth-rule.v1',
          when: {
            type: 'condition',
            field: 'checkout.currency',
            operator: 'eq',
            value: 'USD',
          },
          then: [{ action: 'allow', params: {} }],
        },
        compiled_plan: {
          catalog_version: 'growth-rule-catalog.v1',
          condition: {
            type: 'condition',
            field: 'checkout.currency',
            operator: 'eq',
            value: 'USD',
          },
          actions: [{ action: 'allow', params: {} }],
        },
        compiled_checksum: 'rule-checksum-001',
        node_count: 3,
        max_depth: 2,
        complexity_score: 5,
      },
    });
    mockSimulateGrowthRule.mockResolvedValue({
      data: {
        matched: true,
        result: 'allow',
        actions: [{ action: 'allow', result: 'allow', params: {} }],
        trace: [{ type: 'condition', field: 'checkout.currency', result: true }],
        compiled_checksum: 'rule-checksum-001',
      },
    });
  });

  it('adds catalog-backed conditions and actions to the JSON AST', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');

    await user.click(screen.getByRole('button', { name: /checkout\.currency/ }));
    await user.click(screen.getByRole('button', { name: 'rules.inspector.addCondition' }));
    await user.click(screen.getByRole('button', { name: /allow/ }));

    const astEditor = getAstEditor();
    expect(astEditor.value).toContain('"field": "checkout.currency"');
    expect(astEditor.value).toContain('"action": "allow"');
  });

  it('compiles and simulates the edited AST through the admin API wrapper', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');
    await user.click(screen.getByRole('button', { name: /checkout\.currency/ }));
    await user.click(screen.getByRole('button', { name: 'rules.inspector.addCondition' }));

    await user.click(getFirstButton('rules.actions.compile'));

    await waitFor(() => {
      expect(mockCompileGrowthRule).toHaveBeenCalledWith({
        ast: expect.objectContaining({
          schema_version: 'growth-rule.v1',
        }),
      });
    });
    expect(screen.getAllByText('rule-checksum-001').length).toBeGreaterThan(0);

    await user.click(screen.getAllByRole('button', { name: 'rules.actions.simulate' })[0]);

    await waitFor(() => {
      expect(mockSimulateGrowthRule).toHaveBeenCalledWith({
        ast: expect.objectContaining({
          schema_version: 'growth-rule.v1',
        }),
        context: expect.objectContaining({
          code: { code_type: 'promo' },
        }),
      });
    });

    const simulator = screen.getByRole('heading', { name: 'rules.simulator.title' }).closest('article');
    if (!simulator) {
      throw new Error('Simulator article not found.');
    }
    expect(within(simulator).getByText('rules.simulator.matched')).toBeInTheDocument();
  });

  it('keeps invalid AST JSON client-side and does not call compile', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');

    fireEvent.change(getAstEditor(), { target: { value: '{' } });
    await user.click(getFirstButton('rules.actions.compile'));

    expect(mockCompileGrowthRule).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('rules.errors.astInvalid');
  });
});
