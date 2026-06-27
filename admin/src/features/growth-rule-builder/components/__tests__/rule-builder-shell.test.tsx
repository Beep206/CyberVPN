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
  mockCreateGrowthRulePolicy,
  mockSubmitGrowthRulePolicy,
} = vi.hoisted(() => ({
  mockGetGrowthRuleCatalog: vi.fn(),
  mockCompileGrowthRule: vi.fn(),
  mockSimulateGrowthRule: vi.fn(),
  mockCreateGrowthRulePolicy: vi.fn(),
  mockSubmitGrowthRulePolicy: vi.fn(),
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
      createGrowthRulePolicy: (...args: unknown[]) => mockCreateGrowthRulePolicy(...args),
      submitGrowthRulePolicy: (...args: unknown[]) => mockSubmitGrowthRulePolicy(...args),
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
    mockCreateGrowthRulePolicy.mockResolvedValue({
      data: {
        id: '00000000-0000-0000-0000-000000000111',
        approval_state: 'draft',
        version_number: 1,
      },
    });
    mockSubmitGrowthRulePolicy.mockResolvedValue({
      data: {
        id: '00000000-0000-0000-0000-000000000111',
        approval_state: 'pending_approval',
        version_number: 1,
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

  it('imports a rule draft from a local JSON file without calling backend mutation paths', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');
    const importedAst = {
      schema_version: 'growth-rule.v1',
      when: {
        type: 'condition',
        field: 'checkout.currency',
        operator: 'eq',
        value: 'USD',
      },
      then: [{ action: 'allow', params: {} }],
    };

    await user.upload(
      screen.getByLabelText('rules.actions.importFile'),
      new File([JSON.stringify(importedAst)], 'growth-rule.json', { type: 'application/json' }),
    );

    await waitFor(() => {
      expect(getAstEditor().value).toContain('"field": "checkout.currency"');
    });
    expect(mockCompileGrowthRule).not.toHaveBeenCalled();
    expect(mockSimulateGrowthRule).not.toHaveBeenCalled();
  });

  it('restores autosaved drafts while clearing simulator context from local storage', async () => {
    const savedAst = {
      schema_version: 'growth-rule.v1',
      when: {
        type: 'condition',
        field: 'checkout.currency',
        operator: 'eq',
        value: 'USD',
      },
      then: [{ action: 'allow', params: {} }],
    };
    localStorage.setItem('admin:growth-rules:draft-json', JSON.stringify(savedAst, null, 2));
    localStorage.setItem(
      'admin:growth-rules:simulation-context-json',
      JSON.stringify({ checkout: { currency: 'USD' } }, null, 2),
    );

    renderWithQueryClient(<RuleBuilderShell />);

    await waitFor(() => {
      expect(getAstEditor().value).toContain('"field": "checkout.currency"');
    });
    expect(localStorage.getItem('admin:growth-rules:simulation-context-json')).toBeNull();

    const editedAst = getAstEditor().value.replace('checkout.currency', 'private_catalog.access_class');
    fireEvent.change(getAstEditor(), { target: { value: editedAst } });

    await waitFor(() => {
      expect(screen.getByText('rules.autosave.dirty')).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(localStorage.getItem('admin:growth-rules:draft-json')).toContain(
        'private_catalog.access_class',
      );
    });

    fireEvent.change(screen.getByLabelText('rules.simulator.contextLabel'), {
      target: {
        value: JSON.stringify(
          {
            user_id: 'user_001',
            email: 'alice@example.com',
            private_catalog_grant_id: 'grant_secret',
            code: 'SECRET100',
          },
          null,
          2,
        ),
      },
    });
    expect(localStorage.getItem('admin:growth-rules:simulation-context-json')).toBeNull();
  });

  it('exports the current draft through the keyboard path to clipboard and a JSON file', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const createObjectURL = vi.fn(() => 'blob:growth-rule-draft');
    const revokeObjectURL = vi.fn();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });
    Object.defineProperty(window.URL, 'createObjectURL', {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(window.URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectURL,
    });

    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');
    fireEvent.keyDown(window, { key: 's', ctrlKey: true });

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(expect.stringContaining('"schema_version"'));
    });
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:growth-rule-draft');
  });

  it('supports undo and redo keyboard shortcuts without entering editable controls', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');
    await user.click(screen.getByRole('button', { name: /checkout\.currency/ }));
    await user.click(screen.getByRole('button', { name: 'rules.inspector.addCondition' }));

    await waitFor(() => {
      expect(getAstEditor().value).toContain('"field": "checkout.currency"');
    });

    fireEvent.keyDown(window, { key: 'z', ctrlKey: true });
    await waitFor(() => {
      expect(getAstEditor().value).not.toContain('"field": "checkout.currency"');
    });

    fireEvent.keyDown(window, { key: 'y', ctrlKey: true });
    await waitFor(() => {
      expect(getAstEditor().value).toContain('"field": "checkout.currency"');
    });
  });

  it('supports keyboard movement in the accessible rule tree', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');
    const conditionButtons = screen.getAllByRole('button', { name: 'rules.tree.conditionLabel' });
    const firstCondition = conditionButtons[0];
    if (!firstCondition) {
      throw new Error('Expected at least one condition button.');
    }
    firstCondition.focus();
    await user.keyboard('{Alt>}{ArrowDown}{/Alt}');

    await waitFor(() => {
      const draft = getAstEditor().value;
      expect(draft.indexOf('"field": "risk.score"')).toBeLessThan(
        draft.indexOf('"field": "code.code_type"'),
      );
    });
  });

  it('compiles and simulates from keyboard shortcuts while rendering backend normalized diff', async () => {
    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');
    fireEvent.keyDown(window, { key: 'Enter', ctrlKey: true });

    await waitFor(() => {
      expect(mockCompileGrowthRule).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText('rules.diff.status.changed')).toBeInTheDocument();
    expect(screen.getByText('rules.diff.changedLines')).toBeInTheDocument();
    expect(screen.getAllByText('rule-checksum-001').length).toBeGreaterThan(0);

    fireEvent.keyDown(window, { key: 'Enter', ctrlKey: true, shiftKey: true });
    await waitFor(() => {
      expect(mockSimulateGrowthRule).toHaveBeenCalledTimes(1);
    });
  });

  it('submits compiled drafts into the audited policy-version workflow', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');
    await user.click(getFirstButton('rules.actions.compile'));

    await waitFor(() => {
      expect(mockCompileGrowthRule).toHaveBeenCalledTimes(1);
    });
    await user.click(screen.getByLabelText('rules.publish.approval'));
    await user.click(screen.getByRole('button', { name: 'rules.publish.submit' }));

    await waitFor(() => {
      expect(mockCreateGrowthRulePolicy).toHaveBeenCalledWith({
        policy_key: 'checkout_eligibility',
        subject_type: 'growth_rule',
        subject_id: null,
        ast: expect.objectContaining({
          schema_version: 'growth-rule.v1',
        }),
        change_reason: 'growth_rule_publish_review',
      });
    });
    expect(mockSubmitGrowthRulePolicy).toHaveBeenCalledWith('00000000-0000-0000-0000-000000000111', {
      change_reason: 'growth_rule_publish_review',
      effective_from: null,
      effective_to: null,
    });
    expect(screen.getByText('#1 pending_approval')).toBeInTheDocument();
    expect(screen.getByText('rules.publish.checklist.title')).toBeInTheDocument();
    expect(screen.getByText('rules.publish.checklist.backendWorkflow')).toBeInTheDocument();
    expect(screen.getAllByText('rules.publish.checklist.passed').length).toBeGreaterThan(0);
  });

  it('blocks policy submission after a compiled draft is edited', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<RuleBuilderShell />);

    await screen.findAllByText('checkout.currency');
    await user.click(getFirstButton('rules.actions.compile'));

    await waitFor(() => {
      expect(mockCompileGrowthRule).toHaveBeenCalledTimes(1);
    });
    await user.click(screen.getByLabelText('rules.publish.approval'));
    expect(screen.getByRole('button', { name: 'rules.publish.submit' })).toBeEnabled();

    await user.click(screen.getByRole('button', { name: /checkout\.currency/ }));
    await user.click(screen.getByRole('button', { name: 'rules.inspector.addCondition' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'rules.publish.submit' })).toBeDisabled();
    });
    expect(screen.getAllByText('rules.publish.checklist.blocked').length).toBeGreaterThan(0);
    expect(mockCreateGrowthRulePolicy).not.toHaveBeenCalled();
    expect(mockSubmitGrowthRulePolicy).not.toHaveBeenCalled();
  });
});
