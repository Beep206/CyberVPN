'use client';

import { useEffect, useId, useRef, useState } from 'react';
import type { ChangeEvent, KeyboardEvent, ReactNode, RefObject } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  Download,
  FileUp,
  GitCompare,
  History,
  ListTree,
  Play,
  Plus,
  Redo2,
  RotateCcw,
  Save,
  Search,
  Trash2,
  Undo2,
  Wand2,
  XCircle,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { growthApi } from '@/lib/api/growth';
import type {
  AdminGrowthRuleCompileResponse,
  AdminGrowthRulePolicyDiffResponse,
  AdminGrowthRulePolicyVersionResponse,
  AdminGrowthRuleSimulateResponse,
} from '@/lib/api/growth';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import { getErrorMessage } from '@/features/growth/lib/formatting';
import { hasAdminPermission } from '@/shared/lib/admin-rbac';
import { useAuthStore } from '@/stores/auth-store';
import {
  DEFAULT_RULE_AST,
  DEFAULT_SIMULATION_CONTEXT,
  addActionToAst,
  addConditionToAst,
  buildActionParams,
  buildSampleValue,
  collectRuleActionRows,
  collectRuleTreeRows,
  duplicateNodeAtPath,
  formatJson,
  isRecord,
  moveNodeAtPath,
  normalizeRuleCatalog,
  parseConditionInputValue,
  parseJsonObject,
  removeActionAtIndex,
  removeNodeAtPath,
  rulePathToId,
  setRootGroupOperator,
  stringifyConditionValue,
  updateConditionAtPath,
} from '@/features/growth-rule-builder/lib/ast';
import type {
  GrowthRuleCatalog,
  JsonObject,
  RuleTreeRow,
} from '@/features/growth-rule-builder/lib/ast';
import { cn } from '@/lib/utils';

const DRAFT_STORAGE_KEY = 'admin:growth-rules:draft-json';
const CONTEXT_STORAGE_KEY = 'admin:growth-rules:simulation-context-json';
const POLICY_VERSIONS_QUERY_KEY = ['growth', 'rules', 'policy-versions'];

type AutosaveState = 'idle' | 'dirty' | 'saved' | 'restored';

type VersionDiffStatus = 'uncompiled' | 'invalid' | 'match' | 'changed';

interface VersionDiffSummary {
  status: VersionDiffStatus;
  normalizedJson: string | null;
  changedLines: number;
  addedLines: number;
  removedLines: number;
}

function stringifyUnknown(value: unknown): string {
  return `${JSON.stringify(value, null, 2)}\n`;
}

function downloadDraftJson(draftJson: string) {
  if (typeof window.URL.createObjectURL !== 'function') {
    return;
  }

  const objectUrl = window.URL.createObjectURL(
    new Blob([draftJson], { type: 'application/json' }),
  );
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = 'growth-rule-draft.json';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL?.(objectUrl);
}

function siblingPath(path: string[], direction: 'up' | 'down'): string[] {
  const nextPath = [...path];
  const lastPart = nextPath.at(-1);
  if (lastPart == null) {
    return nextPath;
  }

  const index = Number(lastPart);
  if (!Number.isInteger(index)) {
    return nextPath;
  }

  nextPath[nextPath.length - 1] = String(direction === 'up' ? index - 1 : index + 1);
  return nextPath;
}

function parseDraftJson(input: string): { value: JsonObject | null; error: string | null } {
  try {
    return { value: parseJsonObject(input), error: null };
  } catch (error) {
    return {
      value: null,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

function firstCatalogField(catalog: GrowthRuleCatalog): [string, GrowthRuleCatalog['fields'][string]] | null {
  return Object.entries(catalog.fields)[0] ?? null;
}

function firstOperatorForField(catalog: GrowthRuleCatalog, field: string): string {
  return catalog.fields[field]?.operators[0] ?? Object.keys(catalog.operators)[0] ?? 'eq';
}

function filterCatalogKeys<T>(
  entries: [string, T][],
  query: string,
  buildHaystack: (key: string, value: T) => string,
): [string, T][] {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return entries;
  }

  return entries.filter(([key, value]) =>
    buildHaystack(key, value).toLowerCase().includes(normalizedQuery),
  );
}

function countMatchedTraceItems(trace: AdminGrowthRuleSimulateResponse['trace'] | undefined): number {
  return trace?.filter((item) => item.result === true).length ?? 0;
}

function stableSerialize(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableSerialize(item)).join(',')}]`;
  }

  if (isRecord(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key])}`)
      .join(',')}}`;
  }

  return JSON.stringify(value) ?? 'null';
}

function splitJsonLines(value: string): string[] {
  return value.trimEnd().split('\n');
}

function buildLineDiffSummary(leftJson: string, rightJson: string) {
  const leftLines = splitJsonLines(leftJson);
  const rightLines = splitJsonLines(rightJson);
  const maxLines = Math.max(leftLines.length, rightLines.length);
  let changedLines = 0;
  let addedLines = 0;
  let removedLines = 0;

  for (let index = 0; index < maxLines; index += 1) {
    const leftLine = leftLines[index];
    const rightLine = rightLines[index];

    if (leftLine == null && rightLine != null) {
      addedLines += 1;
      continue;
    }

    if (leftLine != null && rightLine == null) {
      removedLines += 1;
      continue;
    }

    if (leftLine !== rightLine) {
      changedLines += 1;
    }
  }

  return { changedLines, addedLines, removedLines };
}

function summarizeVersionDiff(
  draftJson: string,
  compiledRule: AdminGrowthRuleCompileResponse | null,
): VersionDiffSummary {
  if (!compiledRule) {
    return {
      status: 'uncompiled',
      normalizedJson: null,
      changedLines: 0,
      addedLines: 0,
      removedLines: 0,
    };
  }

  const parsedDraft = parseDraftJson(draftJson);
  if (!parsedDraft.value) {
    return {
      status: 'invalid',
      normalizedJson: stringifyUnknown(compiledRule.normalized_ast),
      changedLines: 0,
      addedLines: 0,
      removedLines: 0,
    };
  }

  const normalizedJson = stringifyUnknown(compiledRule.normalized_ast);
  const lineSummary = buildLineDiffSummary(draftJson, normalizedJson);
  const isCanonicalMatch =
    stableSerialize(parsedDraft.value) === stableSerialize(compiledRule.normalized_ast);

  return {
    status: isCanonicalMatch ? 'match' : 'changed',
    normalizedJson,
    ...lineSummary,
  };
}

function isEditableKeyboardTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLElement
    ? Boolean(target.closest('input, textarea, select, [contenteditable="true"]'))
    : false;
}

export function RuleBuilderShell() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const role = useAuthStore((state) => state.user?.role);
  const canEditRules = hasAdminPermission(role, 'growth.rules.edit');
  const canValidateRules = hasAdminPermission(role, 'growth.rules.validate');
  const canPublishRules = hasAdminPermission(role, 'growth.rules.publish');
  const canApproveRules = hasAdminPermission(role, 'growth.rules.approve');
  const astEditorId = useId();
  const astErrorId = useId();
  const importFileInputId = useId();
  const contextEditorId = useId();
  const contextErrorId = useId();
  const importFileInputRef = useRef<HTMLInputElement>(null);
  const shortcutHandlersRef = useRef<{
    compileDraft: () => void;
    simulateDraft: () => void;
    exportDraft: () => void | Promise<void>;
    undoDraft: () => void;
    redoDraft: () => void;
  }>({
    compileDraft: () => undefined,
    simulateDraft: () => undefined,
    exportDraft: () => undefined,
    undoDraft: () => undefined,
    redoDraft: () => undefined,
  });

  const [draftJson, setDraftJson] = useState(() => formatJson(DEFAULT_RULE_AST));
  const [contextJson, setContextJson] = useState(() => formatJson(DEFAULT_SIMULATION_CONTEXT));
  const [history, setHistory] = useState<string[]>(() => [formatJson(DEFAULT_RULE_AST)]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [selectedField, setSelectedField] = useState('code.code_type');
  const [selectedOperator, setSelectedOperator] = useState('eq');
  const [conditionValue, setConditionValue] = useState('promo');
  const [selectedConditionPath, setSelectedConditionPath] = useState<string[] | null>(null);
  const [catalogSearch, setCatalogSearch] = useState('');
  const [uiMessage, setUiMessage] = useState<string | null>(null);
  const [autosaveState, setAutosaveState] = useState<AutosaveState>('idle');
  const [compiledRule, setCompiledRule] = useState<AdminGrowthRuleCompileResponse | null>(null);
  const [policyVersion, setPolicyVersion] = useState<AdminGrowthRulePolicyVersionResponse | null>(null);
  const [simulationResult, setSimulationResult] = useState<AdminGrowthRuleSimulateResponse | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [publishReason, setPublishReason] = useState('growth_rule_publish_review');
  const [publishApproved, setPublishApproved] = useState(false);
  const [policyActionIdInput, setPolicyActionIdInput] = useState('');
  const [policyCompareIdInput, setPolicyCompareIdInput] = useState('');
  const [policyActionReason, setPolicyActionReason] = useState('growth_rule_lifecycle_review');
  const [policyDiff, setPolicyDiff] = useState<AdminGrowthRulePolicyDiffResponse | null>(null);

  const catalogQuery = useQuery({
    queryKey: ['growth', 'rules', 'catalog'],
    queryFn: async () => {
      const response = await growthApi.getGrowthRuleCatalog();
      return response.data.catalog;
    },
    staleTime: 60_000,
  });

  const policyVersionsQuery = useQuery({
    queryKey: POLICY_VERSIONS_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.listGrowthRulePolicies({
        policy_key: 'checkout_eligibility',
        include_inactive: true,
        limit: 8,
      });
      return response.data;
    },
    staleTime: 30_000,
  });

  const catalog = normalizeRuleCatalog(catalogQuery.data);
  const fieldEntries = filterCatalogKeys(
    Object.entries(catalog.fields),
    catalogSearch,
    (field, spec) => `${field} ${spec.type} ${spec.operators.join(' ')}`,
  );
  const operatorEntries = filterCatalogKeys(
    Object.entries(catalog.operators),
    catalogSearch,
    (operator, spec) => `${operator} ${spec.valueTypes.join(' ')}`,
  );
  const actionEntries = filterCatalogKeys(
    Object.entries(catalog.actions),
    catalogSearch,
    (action, spec) => `${action} ${spec.result} ${spec.params.join(' ')}`,
  );
  const selectedFieldSpec = catalog.fields[selectedField] ?? firstCatalogField(catalog)?.[1];
  const selectedFieldType = selectedFieldSpec?.type ?? 'string';
  const availableOperators = selectedFieldSpec?.operators.length
    ? selectedFieldSpec.operators
    : Object.keys(catalog.operators);
  const parsedDraft = parseDraftJson(draftJson);
  const parsedContext = parseDraftJson(contextJson);
  const treeRows = parsedDraft.value ? collectRuleTreeRows(parsedDraft.value) : [];
  const actionRows = parsedDraft.value ? collectRuleActionRows(parsedDraft.value) : [];
  const selectedConditionId = selectedConditionPath ? rulePathToId(selectedConditionPath) : null;
  const policyVersions = policyVersionsQuery.data?.items ?? [];
  const newestPolicyVersion = policyVersion ?? policyVersions[0] ?? null;
  const activePolicyVersionId = policyActionIdInput.trim() || newestPolicyVersion?.id || '';
  const persistedSelectedPolicyVersion =
    policyVersions.find((version) => version.id === activePolicyVersionId) ?? null;
  const selectedPolicyVersion =
    policyVersion?.id === activePolicyVersionId
      ? policyVersion
      : persistedSelectedPolicyVersion ?? newestPolicyVersion ?? null;
  const defaultComparePolicyVersion = policyVersions.find((version) => version.id !== activePolicyVersionId);
  const comparePolicyVersionId = policyCompareIdInput.trim() || defaultComparePolicyVersion?.id || '';

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      const savedDraft = window.localStorage.getItem(DRAFT_STORAGE_KEY);
      window.localStorage.removeItem(CONTEXT_STORAGE_KEY);

      if (savedDraft) {
        setDraftJson(savedDraft);
        setHistory([savedDraft]);
        setHistoryIndex(0);
        setAutosaveState('restored');
      }
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      window.localStorage.setItem(DRAFT_STORAGE_KEY, draftJson);
      window.localStorage.removeItem(CONTEXT_STORAGE_KEY);
      setAutosaveState('saved');
    }, 350);

    return () => window.clearTimeout(timeoutId);
  }, [draftJson]);

  useEffect(() => {
    if (catalogQuery.data == null) {
      return;
    }

    const normalizedCatalog = normalizeRuleCatalog(catalogQuery.data);
    if (normalizedCatalog.fields[selectedField]) {
      return;
    }

    const firstField = firstCatalogField(normalizedCatalog);
    if (!firstField) {
      return;
    }

    const [field, spec] = firstField;
    const operator = spec.operators[0] ?? firstOperatorForField(normalizedCatalog, field);
    const timeoutId = window.setTimeout(() => {
      setSelectedField(field);
      setSelectedOperator(operator);
      setConditionValue(stringifyConditionValue(buildSampleValue(spec.type, operator, field)));
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [catalogQuery.data, selectedField]);

  useEffect(() => {
    if (!availableOperators.length || availableOperators.includes(selectedOperator)) {
      return;
    }

    const operator = availableOperators[0];
    if (!operator) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setSelectedOperator(operator);
      setConditionValue(
        stringifyConditionValue(buildSampleValue(selectedFieldType, operator, selectedField)),
      );
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [availableOperators, selectedField, selectedFieldType, selectedOperator]);

  const compileMutation = useMutation({
    mutationFn: (ast: JsonObject) => growthApi.compileGrowthRule({ ast }),
    onSuccess: (response) => {
      setCompiledRule(response.data);
      setServerError(null);
      setUiMessage(t('rules.feedback.compiled'));
    },
    onError: (error) => {
      setCompiledRule(null);
      setServerError(getErrorMessage(error, t('rules.errors.compileFailed')));
    },
  });

  const simulateMutation = useMutation({
    mutationFn: (payload: { ast: JsonObject; context: JsonObject }) =>
      growthApi.simulateGrowthRule(payload),
    onSuccess: (response) => {
      setSimulationResult(response.data);
      setServerError(null);
      setUiMessage(t('rules.feedback.simulated'));
    },
    onError: (error) => {
      setSimulationResult(null);
      setServerError(getErrorMessage(error, t('rules.errors.simulateFailed')));
    },
  });

  const submitPolicyMutation = useMutation({
    mutationFn: async (payload: { ast: JsonObject; reason: string }) => {
      const createResponse = await growthApi.createGrowthRulePolicy({
        policy_key: 'checkout_eligibility',
        subject_type: 'growth_rule',
        subject_id: null,
        ast: payload.ast,
        change_reason: payload.reason,
      });
      const submitResponse = await growthApi.submitGrowthRulePolicy(createResponse.data.id, {
        change_reason: payload.reason,
        effective_from: null,
        effective_to: null,
      });
      return submitResponse.data;
    },
    onSuccess: (response) => {
      setPolicyVersion(response);
      setServerError(null);
      setUiMessage(t('rules.feedback.policySubmitted'));
      void queryClient.invalidateQueries({ queryKey: POLICY_VERSIONS_QUERY_KEY });
    },
    onError: (error) => {
      setServerError(getErrorMessage(error, t('rules.errors.policySubmitFailed')));
    },
  });

  const approvePolicyMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.approveGrowthRulePolicy(activePolicyVersionId, {
        change_reason: policyActionReason,
        effective_from: null,
        effective_to: null,
      });
      return response.data;
    },
    onSuccess: (response) => {
      setPolicyVersion(response);
      setServerError(null);
      setUiMessage(t('rules.feedback.policyApproved'));
      void queryClient.invalidateQueries({ queryKey: POLICY_VERSIONS_QUERY_KEY });
    },
    onError: (error) => {
      setServerError(getErrorMessage(error, t('rules.errors.policyActionFailed')));
    },
  });

  const rejectPolicyMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.rejectGrowthRulePolicy(activePolicyVersionId, {
        change_reason: policyActionReason,
        effective_from: null,
        effective_to: null,
      });
      return response.data;
    },
    onSuccess: (response) => {
      setPolicyVersion(response);
      setServerError(null);
      setUiMessage(t('rules.feedback.policyRejected'));
      void queryClient.invalidateQueries({ queryKey: POLICY_VERSIONS_QUERY_KEY });
    },
    onError: (error) => {
      setServerError(getErrorMessage(error, t('rules.errors.policyActionFailed')));
    },
  });

  const publishPolicyMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.publishGrowthRulePolicy(activePolicyVersionId, {
        change_reason: policyActionReason,
        effective_from: null,
        effective_to: null,
      });
      return response.data;
    },
    onSuccess: (response) => {
      setPolicyVersion(response);
      setServerError(null);
      setUiMessage(t('rules.feedback.policyPublished'));
      void queryClient.invalidateQueries({ queryKey: POLICY_VERSIONS_QUERY_KEY });
    },
    onError: (error) => {
      setServerError(getErrorMessage(error, t('rules.errors.policyActionFailed')));
    },
  });

  const rollbackPolicyMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.rollbackGrowthRulePolicy(activePolicyVersionId, {
        change_reason: policyActionReason,
        effective_from: null,
      });
      return response.data;
    },
    onSuccess: (response) => {
      setPolicyVersion(response);
      setServerError(null);
      setUiMessage(t('rules.feedback.policyRolledBack'));
      void queryClient.invalidateQueries({ queryKey: POLICY_VERSIONS_QUERY_KEY });
    },
    onError: (error) => {
      setServerError(getErrorMessage(error, t('rules.errors.policyActionFailed')));
    },
  });

  const diffPolicyMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.diffGrowthRulePolicy(
        activePolicyVersionId,
        comparePolicyVersionId || undefined,
      );
      return response.data;
    },
    onSuccess: (response) => {
      setPolicyDiff(response);
      setServerError(null);
      setUiMessage(t('rules.feedback.policyDiffLoaded'));
    },
    onError: (error) => {
      setPolicyDiff(null);
      setServerError(getErrorMessage(error, t('rules.errors.policyDiffFailed')));
    },
  });

  const pushDraft = (nextAst: JsonObject, messageKey: string) => {
    if (!canEditRules) {
      setServerError(t('rules.permission.readOnly'));
      return;
    }

    const nextJson = formatJson(nextAst);
    const nextHistory = [...history.slice(0, historyIndex + 1), nextJson];
    setHistory(nextHistory);
    setHistoryIndex(nextHistory.length - 1);
    setDraftJson(nextJson);
    setAutosaveState('dirty');
    setUiMessage(t(messageKey));
    setServerError(null);
    setCompiledRule(null);
    setSimulationResult(null);
    setPolicyVersion(null);
    setPublishApproved(false);
  };

  const importDraftAst = (nextAst: JsonObject, messageKey: string) => {
    if (!canEditRules) {
      setServerError(t('rules.permission.readOnly'));
      return;
    }

    pushDraft(nextAst, messageKey);
    compileMutation.mutate(nextAst);
  };

  const getCurrentAst = (): JsonObject | null => {
    if (!parsedDraft.value) {
      setServerError(t('rules.errors.astInvalid', { detail: parsedDraft.error ?? '' }));
      return null;
    }

    return parsedDraft.value;
  };

  const addCondition = () => {
    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    const value = parseConditionInputValue(conditionValue, selectedFieldType, selectedOperator);
    pushDraft(
      addConditionToAst(currentAst, selectedField, selectedOperator, value),
      'rules.feedback.conditionAdded',
    );
  };

  const updateSelectedCondition = () => {
    const currentAst = getCurrentAst();
    if (!currentAst || !selectedConditionPath) {
      return;
    }

    const value = parseConditionInputValue(conditionValue, selectedFieldType, selectedOperator);
    pushDraft(
      updateConditionAtPath(currentAst, selectedConditionPath, {
        field: selectedField,
        operator: selectedOperator,
        value,
      }),
      'rules.feedback.conditionUpdated',
    );
  };

  const duplicateConditionAtPath = (path: string[]) => {
    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    pushDraft(duplicateNodeAtPath(currentAst, path), 'rules.feedback.nodeDuplicated');
  };

  const duplicateSelectedCondition = () => {
    if (!selectedConditionPath) {
      return;
    }

    duplicateConditionAtPath(selectedConditionPath);
  };

  const moveConditionAtPath = (path: string[], direction: 'up' | 'down') => {
    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    pushDraft(moveNodeAtPath(currentAst, path, direction), 'rules.feedback.nodeMoved');
    setSelectedConditionPath(siblingPath(path, direction));
  };

  const removeConditionAtPath = (path: string[]) => {
    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    pushDraft(removeNodeAtPath(currentAst, path), 'rules.feedback.nodeRemoved');
    setSelectedConditionPath(null);
  };

  const removeSelectedCondition = () => {
    if (!selectedConditionPath) {
      return;
    }

    removeConditionAtPath(selectedConditionPath);
  };

  const addAction = (action: string) => {
    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    pushDraft(
      addActionToAst(currentAst, action, buildActionParams(catalog.actions[action])),
      'rules.feedback.actionAdded',
    );
  };

  const removeAction = (actionIndex: number) => {
    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    pushDraft(removeActionAtIndex(currentAst, actionIndex), 'rules.feedback.actionRemoved');
  };

  const setRootOperator = (operator: 'all' | 'any') => {
    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    pushDraft(setRootGroupOperator(currentAst, operator), 'rules.feedback.rootUpdated');
  };

  const commitJsonDraft = () => {
    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    importDraftAst(currentAst, 'rules.feedback.imported');
  };

  const resetDraft = () => {
    pushDraft(DEFAULT_RULE_AST, 'rules.feedback.reset');
    setCompiledRule(null);
    setSimulationResult(null);
    setSelectedConditionPath(null);
  };

  const undoDraft = () => {
    if (!canEditRules) {
      setServerError(t('rules.permission.readOnly'));
      return;
    }

    if (historyIndex === 0) {
      return;
    }

    const nextIndex = Math.max(0, historyIndex - 1);
    const nextJson = history[nextIndex];
    if (nextJson) {
      setHistoryIndex(nextIndex);
      setDraftJson(nextJson);
      setUiMessage(t('rules.feedback.undo'));
      setCompiledRule(null);
      setSimulationResult(null);
      setPolicyVersion(null);
      setPublishApproved(false);
    }
  };

  const redoDraft = () => {
    if (!canEditRules) {
      setServerError(t('rules.permission.readOnly'));
      return;
    }

    if (historyIndex >= history.length - 1) {
      return;
    }

    const nextIndex = Math.min(history.length - 1, historyIndex + 1);
    const nextJson = history[nextIndex];
    if (nextJson) {
      setHistoryIndex(nextIndex);
      setDraftJson(nextJson);
      setUiMessage(t('rules.feedback.redo'));
      setCompiledRule(null);
      setSimulationResult(null);
      setPolicyVersion(null);
      setPublishApproved(false);
    }
  };

  const exportDraft = async () => {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(draftJson);
    }

    downloadDraftJson(draftJson);
    setUiMessage(t('rules.feedback.exported'));
  };

  const importDraftFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) {
      return;
    }
    if (!canEditRules) {
      setServerError(t('rules.permission.readOnly'));
      return;
    }

    try {
      const text = await file.text();
      const parsed = parseJsonObject(text);
      importDraftAst(parsed, 'rules.feedback.fileImported');
    } catch (error) {
      setServerError(t('rules.errors.importFailed', {
        detail: error instanceof Error ? error.message : String(error),
      }));
    }
  };

  const compileDraft = () => {
    if (!canValidateRules) {
      setServerError(t('rules.permission.validateDenied'));
      return;
    }

    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    compileMutation.mutate(currentAst);
  };

  const simulateDraft = () => {
    if (!canValidateRules) {
      setServerError(t('rules.permission.validateDenied'));
      return;
    }

    const currentAst = getCurrentAst();
    if (!currentAst) {
      return;
    }

    if (!parsedContext.value) {
      setServerError(t('rules.errors.contextInvalid', { detail: parsedContext.error ?? '' }));
      return;
    }

    simulateMutation.mutate({ ast: currentAst, context: parsedContext.value });
  };

  const submitPolicyDraft = () => {
    if (!canPublishRules) {
      setServerError(t('rules.permission.publishDenied'));
      return;
    }

    const currentAst = getCurrentAst();
    const reason = publishReason.trim();
    if (!currentAst) {
      return;
    }
    if (!compiledRule) {
      setServerError(t('rules.errors.compileRequired'));
      return;
    }
    if (!reason || !publishApproved) {
      setServerError(t('rules.errors.publishChecklistIncomplete'));
      return;
    }

    submitPolicyMutation.mutate({ ast: currentAst, reason });
  };

  const approvePolicyVersion = () => {
    if (!canApproveRules) {
      setServerError(t('rules.permission.approveDenied'));
      return;
    }
    approvePolicyMutation.mutate();
  };

  const rejectPolicyVersion = () => {
    if (!canApproveRules) {
      setServerError(t('rules.permission.approveDenied'));
      return;
    }
    rejectPolicyMutation.mutate();
  };

  const publishPolicyVersion = () => {
    if (!canPublishRules) {
      setServerError(t('rules.permission.publishDenied'));
      return;
    }
    publishPolicyMutation.mutate();
  };

  const rollbackPolicyVersion = () => {
    if (!canPublishRules) {
      setServerError(t('rules.permission.publishDenied'));
      return;
    }
    rollbackPolicyMutation.mutate();
  };

  const selectCondition = (row: RuleTreeRow) => {
    if (row.type !== 'condition') {
      return;
    }

    const fieldSpec = catalog.fields[row.field];
    setSelectedConditionPath(row.path);
    setSelectedField(row.field);
    setSelectedOperator(row.operator);
    setConditionValue(stringifyConditionValue(row.value));
    if (!fieldSpec) {
      setUiMessage(t('rules.feedback.unsupportedSelection'));
    }
  };

  useEffect(() => {
    shortcutHandlersRef.current = {
      compileDraft,
      simulateDraft,
      exportDraft,
      undoDraft,
      redoDraft,
    };
  });

  useEffect(() => {
    const handleShortcut = (event: globalThis.KeyboardEvent) => {
      if (!event.ctrlKey && !event.metaKey) {
        return;
      }

      const key = event.key.toLowerCase();
      if (key === 'enter') {
        event.preventDefault();
        if (event.shiftKey) {
          shortcutHandlersRef.current.simulateDraft();
          return;
        }

        shortcutHandlersRef.current.compileDraft();
        return;
      }

      if (key === 's') {
        event.preventDefault();
        void shortcutHandlersRef.current.exportDraft();
        return;
      }

      if (isEditableKeyboardTarget(event.target)) {
        return;
      }

      if (key === 'z' && event.shiftKey) {
        event.preventDefault();
        shortcutHandlersRef.current.redoDraft();
        return;
      }

      if (key === 'z') {
        event.preventDefault();
        shortcutHandlersRef.current.undoDraft();
        return;
      }

      if (key === 'y') {
        event.preventDefault();
        shortcutHandlersRef.current.redoDraft();
      }
    };

    window.addEventListener('keydown', handleShortcut);
    return () => window.removeEventListener('keydown', handleShortcut);
  }, []);

  return (
    <GrowthPageShell
      eyebrow={t('rules.eyebrow')}
      title={t('rules.title')}
      description={t('rules.description')}
      icon={ListTree}
      actions={
        <>
          <Button
            type="button"
            variant="outline"
            size="sm"
            magnetic={false}
            onClick={undoDraft}
            disabled={!canEditRules || historyIndex === 0}
            aria-label={t('rules.actions.undo')}
            aria-keyshortcuts="Control+Z Meta+Z"
          >
            <Undo2 className="mr-2 h-4 w-4" aria-hidden="true" />
            {t('rules.actions.undo')}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            magnetic={false}
            onClick={redoDraft}
            disabled={!canEditRules || historyIndex >= history.length - 1}
            aria-label={t('rules.actions.redo')}
            aria-keyshortcuts="Control+Y Meta+Y Control+Shift+Z Meta+Shift+Z"
          >
            <Redo2 className="mr-2 h-4 w-4" aria-hidden="true" />
            {t('rules.actions.redo')}
          </Button>
          <Button
            type="button"
            size="sm"
            magnetic={false}
            onClick={compileDraft}
            disabled={!canValidateRules || compileMutation.isPending}
            aria-label={t('rules.actions.compile')}
            aria-keyshortcuts="Control+Enter Meta+Enter"
          >
            <Wand2 className="mr-2 h-4 w-4" aria-hidden="true" />
            {compileMutation.isPending ? t('rules.actions.compiling') : t('rules.actions.compile')}
          </Button>
          <Button
            type="button"
            size="sm"
            magnetic={false}
            onClick={simulateDraft}
            disabled={!canValidateRules || simulateMutation.isPending}
            aria-label={t('rules.actions.simulate')}
            aria-keyshortcuts="Control+Shift+Enter Meta+Shift+Enter"
          >
            <Play className="mr-2 h-4 w-4" aria-hidden="true" />
            {simulateMutation.isPending ? t('rules.actions.simulating') : t('rules.actions.simulate')}
          </Button>
        </>
      }
      metrics={[
        {
          label: t('rules.metrics.catalogVersion'),
          value: catalog.catalogVersion || t('common.missing'),
          hint: t('rules.metrics.catalogVersionHint'),
          tone: catalog.catalogVersion ? 'info' : 'warning',
        },
        {
          label: t('rules.metrics.nodes'),
          value: String(treeRows.length + actionRows.length),
          hint: t('rules.metrics.nodesHint', {
            max: catalog.limits.maxNodes ?? 0,
          }),
          tone: 'neutral',
        },
        {
          label: t('rules.metrics.checksum'),
          value: compiledRule?.compiled_checksum.slice(0, 12) ?? t('common.missing'),
          hint: compiledRule ? t('rules.metrics.checksumHint') : t('rules.metrics.checksumMissing'),
          tone: compiledRule ? 'success' : 'warning',
        },
        {
          label: t('rules.metrics.trace'),
          value: new Intl.NumberFormat(locale).format(countMatchedTraceItems(simulationResult?.trace)),
          hint: t('rules.metrics.traceHint'),
          tone: simulationResult?.matched ? 'success' : 'neutral',
        },
      ]}
    >
      <div aria-live="polite" className="sr-only">
        {uiMessage}
      </div>

      {serverError || parsedDraft.error || parsedContext.error || catalogQuery.error || policyVersionsQuery.error ? (
        <div
          role="alert"
          className="rounded-lg border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono leading-6 text-neon-pink"
        >
          <div className="flex items-start gap-3">
            <XCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-display uppercase tracking-[0.18em] text-white">
                {t('rules.errors.title')}
              </p>
              <p className="mt-1">
                {serverError
                  ?? (parsedDraft.error
                    ? t('rules.errors.astInvalid', { detail: parsedDraft.error })
                    : null)
                  ?? (parsedContext.error
                    ? t('rules.errors.contextInvalid', { detail: parsedContext.error })
                    : null)
                  ?? getErrorMessage(
                    catalogQuery.error ?? policyVersionsQuery.error,
                    catalogQuery.error
                      ? t('rules.errors.catalogFailed')
                      : t('rules.errors.policyListFailed'),
                  )}
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {!canEditRules ? (
        <RulePermissionNotice>{t('rules.permission.readOnly')}</RulePermissionNotice>
      ) : null}

      <div className="grid gap-6 2xl:grid-cols-[minmax(17rem,0.85fr)_minmax(0,1.35fr)_minmax(20rem,1fr)]">
        <RulePalette
          t={t}
          canEdit={canEditRules}
          catalog={catalog}
          isLoading={catalogQuery.isLoading}
          search={catalogSearch}
          onSearchChange={setCatalogSearch}
          fieldEntries={fieldEntries}
          operatorEntries={operatorEntries}
          actionEntries={actionEntries}
          selectedField={selectedField}
          selectedOperator={selectedOperator}
          onSelectField={(field, spec) => {
            const operator = spec.operators[0] ?? firstOperatorForField(catalog, field);
            setSelectedField(field);
            setSelectedOperator(operator);
            setConditionValue(stringifyConditionValue(buildSampleValue(spec.type, operator, field)));
          }}
          onSelectOperator={(operator) => {
            setSelectedOperator(operator);
            setConditionValue(
              stringifyConditionValue(buildSampleValue(selectedFieldType, operator, selectedField)),
            );
          }}
          onAddAction={addAction}
        />

        <section className="space-y-6">
          <RuleTreePanel
            t={t}
            canEdit={canEditRules}
            rows={treeRows}
            actions={actionRows}
            selectedConditionId={selectedConditionId}
            onSelectCondition={selectCondition}
            onRemoveAction={removeAction}
            onSetRootOperator={setRootOperator}
            onDuplicateCondition={(row) => {
              setSelectedConditionPath(row.path);
              duplicateConditionAtPath(row.path);
            }}
            onRemoveCondition={(row) => {
              removeConditionAtPath(row.path);
            }}
            onMoveCondition={(row, direction) => {
              moveConditionAtPath(row.path, direction);
            }}
          />
          <JsonEditorPanel
            t={t}
            astEditorId={astEditorId}
            astErrorId={astErrorId}
            importFileInputId={importFileInputId}
            importFileInputRef={importFileInputRef}
            draftJson={draftJson}
            parseError={parsedDraft.error}
            autosaveState={autosaveState}
            onDraftChange={(value) => {
              if (!canEditRules) {
                setServerError(t('rules.permission.readOnly'));
                return;
              }
              setDraftJson(value);
              setAutosaveState('dirty');
              setCompiledRule(null);
              setSimulationResult(null);
              setPolicyVersion(null);
              setPublishApproved(false);
            }}
            onCommit={commitJsonDraft}
            onImportFile={importDraftFile}
            onExport={exportDraft}
            onReset={resetDraft}
            canEdit={canEditRules}
          />
        </section>

        <section className="space-y-6">
          <RuleInspectorPanel
            t={t}
            canEdit={canEditRules}
            catalog={catalog}
            selectedField={selectedField}
            selectedOperator={selectedOperator}
            conditionValue={conditionValue}
            availableOperators={availableOperators}
            hasSelectedCondition={Boolean(selectedConditionPath)}
            onFieldChange={(field) => {
              const spec = catalog.fields[field];
              const operator = spec?.operators[0] ?? firstOperatorForField(catalog, field);
              setSelectedField(field);
              setSelectedOperator(operator);
              setConditionValue(
                stringifyConditionValue(buildSampleValue(spec?.type ?? 'string', operator, field)),
              );
            }}
            onOperatorChange={(operator) => {
              setSelectedOperator(operator);
              setConditionValue(
                stringifyConditionValue(buildSampleValue(selectedFieldType, operator, selectedField)),
              );
            }}
            onValueChange={setConditionValue}
            onAddCondition={addCondition}
            onUpdateSelected={updateSelectedCondition}
            onDuplicateSelected={duplicateSelectedCondition}
            onRemoveSelected={removeSelectedCondition}
          />
          <CompilePanel t={t} compiledRule={compiledRule} />
          <PublishReadinessPanel
            t={t}
            compiledRule={compiledRule}
            reason={publishReason}
            approved={publishApproved}
            onReasonChange={setPublishReason}
            onApprovedChange={setPublishApproved}
            onSubmit={submitPolicyDraft}
            isSubmitting={submitPolicyMutation.isPending}
            policyVersion={policyVersion}
            canPublish={canPublishRules}
          />
          <PolicyLifecyclePanel
            t={t}
            policies={policyVersions}
            isLoading={policyVersionsQuery.isLoading}
            policyId={activePolicyVersionId}
            comparePolicyId={comparePolicyVersionId}
            reason={policyActionReason}
            canApprove={canApproveRules}
            canPublish={canPublishRules}
            policyDiff={policyDiff}
            selectedPolicy={selectedPolicyVersion}
            onPolicyIdChange={setPolicyActionIdInput}
            onComparePolicyIdChange={setPolicyCompareIdInput}
            onReasonChange={setPolicyActionReason}
            onApprove={approvePolicyVersion}
            onReject={rejectPolicyVersion}
            onPublish={publishPolicyVersion}
            onRollback={rollbackPolicyVersion}
            onDiff={() => diffPolicyMutation.mutate()}
            isApprovePending={approvePolicyMutation.isPending}
            isRejectPending={rejectPolicyMutation.isPending}
            isPublishPending={publishPolicyMutation.isPending}
            isRollbackPending={rollbackPolicyMutation.isPending}
            isDiffPending={diffPolicyMutation.isPending}
          />
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <SimulatorPanel
          t={t}
          contextEditorId={contextEditorId}
          contextErrorId={contextErrorId}
          contextJson={contextJson}
          contextError={parsedContext.error}
          simulationResult={simulationResult}
          onContextChange={(value) => {
            if (!canValidateRules) {
              setServerError(t('rules.permission.validateDenied'));
              return;
            }
            setContextJson(value);
            setAutosaveState('dirty');
            setSimulationResult(null);
          }}
          onSimulate={simulateDraft}
          isSimulating={simulateMutation.isPending}
          canValidate={canValidateRules}
        />
        <VersionDiffPanel t={t} draftJson={draftJson} compiledRule={compiledRule} />
      </div>
    </GrowthPageShell>
  );
}

interface TranslationFn {
  (key: string): string;
  (key: string, values: Record<string, string | number>): string;
}

function RulePermissionNotice({ children }: { children: ReactNode }) {
  return (
    <div
      role="note"
      className="rounded-lg border border-amber-400/30 bg-amber-400/10 p-4 text-xs font-mono leading-5 text-amber-100"
    >
      {children}
    </div>
  );
}

function policyTone(value: string | null | undefined) {
  const normalizedValue = value?.toLowerCase();
  if (normalizedValue === 'approved' || normalizedValue === 'active' || normalizedValue === 'published') {
    return 'success' as const;
  }
  if (normalizedValue === 'pending_approval' || normalizedValue === 'draft') {
    return 'warning' as const;
  }
  if (normalizedValue === 'rejected' || normalizedValue === 'inactive') {
    return 'danger' as const;
  }
  return 'neutral' as const;
}

interface RulePaletteProps {
  t: TranslationFn;
  canEdit: boolean;
  catalog: GrowthRuleCatalog;
  isLoading: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  fieldEntries: [string, GrowthRuleCatalog['fields'][string]][];
  operatorEntries: [string, GrowthRuleCatalog['operators'][string]][];
  actionEntries: [string, GrowthRuleCatalog['actions'][string]][];
  selectedField: string;
  selectedOperator: string;
  onSelectField: (field: string, spec: GrowthRuleCatalog['fields'][string]) => void;
  onSelectOperator: (operator: string) => void;
  onAddAction: (action: string) => void;
}

function RulePalette({
  t,
  canEdit,
  catalog,
  isLoading,
  search,
  onSearchChange,
  fieldEntries,
  operatorEntries,
  actionEntries,
  selectedField,
  selectedOperator,
  onSelectField,
  onSelectOperator,
  onAddAction,
}: RulePaletteProps) {
  return (
    <aside className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('rules.palette.title')}
          </h2>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {t('rules.palette.description')}
          </p>
        </div>
        <GrowthStatusChip
          label={catalog.catalogVersion || t('common.missing')}
          tone={catalog.catalogVersion ? 'info' : 'warning'}
        />
      </div>

      <label className="mt-5 block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
        {t('rules.palette.search')}
        <span className="mt-2 flex items-center gap-2 rounded-lg border border-grid-line/20 bg-terminal-bg/60 px-3 py-2 focus-within:border-neon-cyan/45">
          <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-hidden"
            placeholder={t('rules.palette.searchPlaceholder')}
          />
        </span>
      </label>

      {isLoading ? (
        <div className="mt-5 text-sm font-mono text-muted-foreground">
          {t('rules.palette.loading')}
        </div>
      ) : null}

      <PaletteGroup title={t('rules.palette.fields')} emptyLabel={t('rules.palette.emptyFields')}>
        {fieldEntries.map(([field, spec]) => (
          <button
            key={field}
            type="button"
            disabled={!canEdit}
            onClick={() => onSelectField(field, spec)}
            className={cn(
              'w-full rounded-lg border p-3 text-left transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan',
              field === selectedField
                ? 'border-neon-cyan/45 bg-neon-cyan/10 text-neon-cyan'
                : 'border-grid-line/20 bg-terminal-bg/50 text-foreground hover:border-grid-line/50',
            )}
            aria-pressed={field === selectedField}
          >
            <span className="block font-mono text-xs">{field}</span>
            <span className="mt-1 block text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              {spec.type}
            </span>
          </button>
        ))}
      </PaletteGroup>

      <PaletteGroup title={t('rules.palette.operators')} emptyLabel={t('rules.palette.emptyOperators')}>
        {operatorEntries.map(([operator, spec]) => (
          <button
            key={operator}
            type="button"
            disabled={!canEdit}
            onClick={() => onSelectOperator(operator)}
            className={cn(
              'rounded-lg border px-3 py-2 text-left font-mono text-xs transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan',
              operator === selectedOperator
                ? 'border-neon-cyan/45 bg-neon-cyan/10 text-neon-cyan'
                : 'border-grid-line/20 bg-terminal-bg/50 text-muted-foreground hover:border-grid-line/50 hover:text-foreground',
            )}
            aria-pressed={operator === selectedOperator}
          >
            <span className="block">{operator}</span>
            <span className="mt-1 block text-[10px] uppercase tracking-[0.14em]">
              {spec.valueTypes.join(', ') || t('common.missing')}
            </span>
          </button>
        ))}
      </PaletteGroup>

      <PaletteGroup title={t('rules.palette.actions')} emptyLabel={t('rules.palette.emptyActions')}>
        {actionEntries.map(([action, spec]) => (
          <button
            key={action}
            type="button"
            disabled={!canEdit}
            onClick={() => onAddAction(action)}
            className="w-full rounded-lg border border-grid-line/20 bg-terminal-bg/50 p-3 text-left transition-colors hover:border-matrix-green/40 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-matrix-green"
          >
            <span className="flex items-center justify-between gap-3">
              <span className="font-mono text-xs text-foreground">{action}</span>
              <Plus className="h-4 w-4 text-matrix-green" aria-hidden="true" />
            </span>
            <span className="mt-1 block text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              {spec.result || t('common.missing')}
            </span>
          </button>
        ))}
      </PaletteGroup>
    </aside>
  );
}

function PaletteGroup({
  title,
  emptyLabel,
  children,
}: {
  title: string;
  emptyLabel: string;
  children: ReactNode;
}) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : Boolean(children);

  return (
    <section className="mt-6">
      <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">{title}</h3>
      <div className="mt-3 grid gap-2">{hasChildren ? children : <GrowthEmptyState label={emptyLabel} />}</div>
    </section>
  );
}

interface RuleTreePanelProps {
  t: TranslationFn;
  canEdit: boolean;
  rows: RuleTreeRow[];
  actions: ReturnType<typeof collectRuleActionRows>;
  selectedConditionId: string | null;
  onSelectCondition: (row: RuleTreeRow) => void;
  onDuplicateCondition: (row: Extract<RuleTreeRow, { type: 'condition' }>) => void;
  onRemoveCondition: (row: Extract<RuleTreeRow, { type: 'condition' }>) => void;
  onMoveCondition: (
    row: Extract<RuleTreeRow, { type: 'condition' }>,
    direction: 'up' | 'down',
  ) => void;
  onRemoveAction: (actionIndex: number) => void;
  onSetRootOperator: (operator: 'all' | 'any') => void;
}

function RuleTreePanel({
  t,
  canEdit,
  rows,
  actions,
  selectedConditionId,
  onSelectCondition,
  onDuplicateCondition,
  onRemoveCondition,
  onMoveCondition,
  onRemoveAction,
  onSetRootOperator,
}: RuleTreePanelProps) {
  const keyboardHelpId = useId();

  function handleConditionKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    row: Extract<RuleTreeRow, { type: 'condition' }>,
  ) {
    if (!canEdit) {
      return;
    }

    if (event.key === 'Delete' || event.key === 'Backspace') {
      event.preventDefault();
      onRemoveCondition(row);
      return;
    }

    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'd') {
      event.preventDefault();
      onDuplicateCondition(row);
      return;
    }

    if (event.altKey && event.key === 'ArrowUp') {
      event.preventDefault();
      onMoveCondition(row, 'up');
      return;
    }

    if (event.altKey && event.key === 'ArrowDown') {
      event.preventDefault();
      onMoveCondition(row, 'down');
    }
  }

  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('rules.tree.title')}
          </h2>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {t('rules.tree.description')}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            magnetic={false}
            disabled={!canEdit}
            onClick={() => onSetRootOperator('all')}
          >
            {t('rules.tree.all')}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            magnetic={false}
            disabled={!canEdit}
            onClick={() => onSetRootOperator('any')}
          >
            {t('rules.tree.any')}
          </Button>
        </div>
      </div>

      <div
        role="tree"
        aria-label={t('rules.tree.ariaLabel')}
        aria-describedby={keyboardHelpId}
        className="mt-5 space-y-2"
      >
        <p id={keyboardHelpId} className="sr-only">
          {t('rules.tree.keyboardHelp')}
        </p>
        {rows.length === 0 ? (
          <GrowthEmptyState label={t('rules.tree.empty')} />
        ) : (
          rows.map((row) => {
            const isSelected = row.id === selectedConditionId;

            return (
              <div
                key={row.id}
                role="treeitem"
                aria-level={row.depth}
                aria-selected={isSelected}
                className={cn(
                  'rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-3',
                  isSelected ? 'border-neon-cyan/45 bg-neon-cyan/10' : '',
                )}
                style={{ marginLeft: `${Math.max(0, row.depth - 1) * 0.75}rem` }}
              >
                {row.type === 'condition' ? (
                  <button
                    type="button"
                    onClick={() => onSelectCondition(row)}
                    onKeyDown={(event) => handleConditionKeyDown(event, row)}
                    aria-label={t('rules.tree.conditionLabel', {
                      field: row.field,
                      operator: row.operator,
                    })}
                    className="block w-full text-left focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                  >
                    <span className="font-mono text-xs text-neon-cyan">{row.field}</span>
                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                      {row.operator}
                    </span>
                    <span className="mt-1 block break-words text-xs font-mono text-foreground">
                      {stringifyConditionValue(row.value)}
                    </span>
                  </button>
                ) : row.type === 'group' ? (
                  <div>
                    <span className="font-mono text-xs uppercase tracking-[0.16em] text-white">
                      {row.groupType}
                    </span>
                    <span className="ml-2 text-xs font-mono text-muted-foreground">
                      {t('rules.tree.children', { count: row.childCount })}
                    </span>
                  </div>
                ) : (
                  <span className="font-mono text-xs text-neon-pink">{row.nodeType}</span>
                )}
              </div>
            );
          })
        )}
      </div>

      <section className="mt-6">
        <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
          {t('rules.actionsPanel.title')}
        </h3>
        <div className="mt-3 space-y-2">
          {actions.length === 0 ? (
            <GrowthEmptyState label={t('rules.actionsPanel.empty')} />
          ) : (
            actions.map((action) => (
              <div
                key={action.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-3"
              >
                <div className="min-w-0">
                  <p className="truncate font-mono text-xs text-matrix-green">{action.action}</p>
                  <p className="mt-1 truncate text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                    {action.result || t('common.missing')}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  magnetic={false}
                  disabled={!canEdit}
                  onClick={() => onRemoveAction(action.index)}
                  aria-label={t('rules.actionsPanel.remove')}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            ))
          )}
        </div>
      </section>
    </article>
  );
}

interface JsonEditorPanelProps {
  t: TranslationFn;
  canEdit: boolean;
  astEditorId: string;
  astErrorId: string;
  importFileInputId: string;
  importFileInputRef: RefObject<HTMLInputElement | null>;
  draftJson: string;
  parseError: string | null;
  autosaveState: AutosaveState;
  onDraftChange: (value: string) => void;
  onCommit: () => void;
  onImportFile: (event: ChangeEvent<HTMLInputElement>) => void;
  onExport: () => void;
  onReset: () => void;
}

function JsonEditorPanel({
  t,
  canEdit,
  astEditorId,
  astErrorId,
  importFileInputId,
  importFileInputRef,
  draftJson,
  parseError,
  autosaveState,
  onDraftChange,
  onCommit,
  onImportFile,
  onExport,
  onReset,
}: JsonEditorPanelProps) {
  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('rules.editor.title')}
          </h2>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {t('rules.editor.description')}
          </p>
        </div>
        <GrowthStatusChip label={t(`rules.autosave.${autosaveState}`)} tone="info" />
      </div>

      <label
        htmlFor={astEditorId}
        className="mt-5 block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground"
      >
        {t('rules.editor.astLabel')}
      </label>
      <textarea
        id={astEditorId}
        value={draftJson}
        disabled={!canEdit}
        onChange={(event) => onDraftChange(event.target.value)}
        aria-invalid={Boolean(parseError)}
        aria-describedby={parseError ? astErrorId : undefined}
        spellCheck={false}
        className="mt-2 min-h-96 w-full resize-y rounded-lg border border-grid-line/25 bg-terminal-bg/70 p-4 font-mono text-xs leading-5 text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
      />
      {parseError ? (
        <p id={astErrorId} className="mt-2 text-xs font-mono text-neon-pink">
          {t('rules.errors.astInvalid', { detail: parseError })}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button type="button" size="sm" magnetic={false} onClick={onCommit} disabled={!canEdit}>
          <Save className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('rules.actions.import')}
        </Button>
        <input
          ref={importFileInputRef}
          id={importFileInputId}
          type="file"
          accept="application/json,.json"
          className="sr-only"
          aria-label={t('rules.actions.importFile')}
          disabled={!canEdit}
          onChange={onImportFile}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          magnetic={false}
          disabled={!canEdit}
          onClick={() => importFileInputRef.current?.click()}
        >
          <FileUp className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('rules.actions.importFile')}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          magnetic={false}
          onClick={onExport}
          aria-keyshortcuts="Control+S Meta+S"
        >
          <Download className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('rules.actions.export')}
        </Button>
        <Button type="button" variant="outline" size="sm" magnetic={false} onClick={onReset} disabled={!canEdit}>
          <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('rules.actions.reset')}
        </Button>
      </div>
    </article>
  );
}

interface RuleInspectorPanelProps {
  t: TranslationFn;
  canEdit: boolean;
  catalog: GrowthRuleCatalog;
  selectedField: string;
  selectedOperator: string;
  conditionValue: string;
  availableOperators: string[];
  hasSelectedCondition: boolean;
  onFieldChange: (field: string) => void;
  onOperatorChange: (operator: string) => void;
  onValueChange: (value: string) => void;
  onAddCondition: () => void;
  onUpdateSelected: () => void;
  onDuplicateSelected: () => void;
  onRemoveSelected: () => void;
}

function RuleInspectorPanel({
  t,
  canEdit,
  catalog,
  selectedField,
  selectedOperator,
  conditionValue,
  availableOperators,
  hasSelectedCondition,
  onFieldChange,
  onOperatorChange,
  onValueChange,
  onAddCondition,
  onUpdateSelected,
  onDuplicateSelected,
  onRemoveSelected,
}: RuleInspectorPanelProps) {
  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
        {t('rules.inspector.title')}
      </h2>
      <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
        {t('rules.inspector.description')}
      </p>

      <div className="mt-5 grid gap-4">
        <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
          {t('rules.inspector.field')}
          <select
            value={selectedField}
            disabled={!canEdit}
            onChange={(event) => onFieldChange(event.target.value)}
            className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
          >
            {Object.keys(catalog.fields).map((field) => (
              <option key={field} value={field}>
                {field}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
          {t('rules.inspector.operator')}
          <select
            value={selectedOperator}
            disabled={!canEdit}
            onChange={(event) => onOperatorChange(event.target.value)}
            className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
          >
            {availableOperators.map((operator) => (
              <option key={operator} value={operator}>
                {operator}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
          {t('rules.inspector.value')}
          <input
            value={conditionValue}
            disabled={!canEdit}
            onChange={(event) => onValueChange(event.target.value)}
            className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
          />
        </label>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        <Button type="button" magnetic={false} onClick={onAddCondition} disabled={!canEdit}>
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('rules.inspector.addCondition')}
        </Button>
        <Button
          type="button"
          variant="outline"
          magnetic={false}
          onClick={onUpdateSelected}
          disabled={!canEdit || !hasSelectedCondition}
        >
          <CheckCircle2 className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('rules.inspector.updateSelected')}
        </Button>
        <Button
          type="button"
          variant="outline"
          magnetic={false}
          onClick={onDuplicateSelected}
          disabled={!canEdit || !hasSelectedCondition}
        >
          <Copy className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('rules.inspector.duplicateSelected')}
        </Button>
        <Button
          type="button"
          variant="outline"
          magnetic={false}
          onClick={onRemoveSelected}
          disabled={!canEdit || !hasSelectedCondition}
        >
          <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('rules.inspector.removeSelected')}
        </Button>
      </div>
    </article>
  );
}

function CompilePanel({
  t,
  compiledRule,
}: {
  t: TranslationFn;
  compiledRule: AdminGrowthRuleCompileResponse | null;
}) {
  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
        {t('rules.compile.title')}
      </h2>
      {compiledRule ? (
        <div className="mt-4 space-y-3">
          <InfoLine label={t('rules.compile.checksum')} value={compiledRule.compiled_checksum} />
          <InfoLine label={t('rules.compile.schema')} value={compiledRule.schema_version} />
          <InfoLine label={t('rules.compile.catalog')} value={compiledRule.catalog_version} />
          <div className="grid gap-3 sm:grid-cols-3">
            <MetricCell label={t('rules.compile.nodeCount')} value={String(compiledRule.node_count)} />
            <MetricCell label={t('rules.compile.maxDepth')} value={String(compiledRule.max_depth)} />
            <MetricCell
              label={t('rules.compile.complexity')}
              value={String(compiledRule.complexity_score)}
            />
          </div>
        </div>
      ) : (
        <GrowthEmptyState label={t('rules.compile.empty')} />
      )}
    </article>
  );
}

function PublishReadinessPanel({
  t,
  compiledRule,
  policyVersion,
  reason,
  approved,
  canPublish,
  isSubmitting,
  onReasonChange,
  onApprovedChange,
  onSubmit,
}: {
  t: TranslationFn;
  compiledRule: AdminGrowthRuleCompileResponse | null;
  policyVersion: AdminGrowthRulePolicyVersionResponse | null;
  reason: string;
  approved: boolean;
  canPublish: boolean;
  isSubmitting: boolean;
  onReasonChange: (value: string) => void;
  onApprovedChange: (value: boolean) => void;
  onSubmit: () => void;
}) {
  const isReadyForBackend = Boolean(compiledRule && reason.trim() && approved && canPublish);
  const checklist = [
    {
      label: t('rules.publish.checklist.compiled'),
      passed: Boolean(compiledRule),
    },
    {
      label: t('rules.publish.checklist.reason'),
      passed: Boolean(reason.trim()),
    },
    {
      label: t('rules.publish.checklist.approval'),
      passed: approved,
    },
    {
      label: t('rules.publish.checklist.backendWorkflow'),
      passed: true,
    },
  ];

  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-300" aria-hidden="true" />
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('rules.publish.title')}
          </h2>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {t('rules.publish.description')}
          </p>
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <InfoLine
          label={t('rules.publish.checksum')}
          value={compiledRule?.compiled_checksum ?? t('common.missing')}
        />
        <InfoLine
          label={t('rules.publish.policyVersion')}
          value={policyVersion ? `#${policyVersion.version_number} ${policyVersion.approval_state}` : t('common.missing')}
        />
        <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
          {t('rules.publish.reasonCode')}
          <input
            value={reason}
            disabled={!canPublish}
            onChange={(event) => onReasonChange(event.target.value)}
            className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
          />
        </label>
        <label className="flex items-start gap-3 rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-3 text-xs font-mono leading-5 text-muted-foreground">
          <input
            type="checkbox"
            checked={approved}
            disabled={!canPublish}
            onChange={(event) => onApprovedChange(event.target.checked)}
            className="mt-1 h-4 w-4 rounded border-grid-line/40 bg-terminal-bg text-neon-cyan focus:ring-neon-cyan"
          />
          <span>{t('rules.publish.approval')}</span>
        </label>
        <div className="rounded-lg border border-amber-400/30 bg-amber-400/10 p-4">
          <GrowthStatusChip
            label={isReadyForBackend ? t('rules.publish.ready') : t('rules.publish.notReady')}
            tone={isReadyForBackend ? 'warning' : 'neutral'}
          />
          <p className="mt-3 text-xs font-mono leading-5 text-amber-100">
            {policyVersion ? t('rules.publish.submitted') : t('rules.publish.backendWorkflow')}
          </p>
        </div>
        <section aria-label={t('rules.publish.checklist.title')}>
          <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
            {t('rules.publish.checklist.title')}
          </h3>
          <ul className="mt-3 space-y-2">
            {checklist.map((item) => (
              <li
                key={item.label}
                className="flex items-center justify-between gap-3 rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-3"
              >
                <span className="text-xs font-mono leading-5 text-muted-foreground">
                  {item.label}
                </span>
                <GrowthStatusChip
                  label={item.passed ? t('rules.publish.checklist.passed') : t('rules.publish.checklist.blocked')}
                  tone={item.passed ? 'success' : 'warning'}
                />
              </li>
            ))}
          </ul>
        </section>
        <Button
          type="button"
          variant="outline"
          magnetic={false}
          disabled={!isReadyForBackend || isSubmitting}
          onClick={onSubmit}
        >
          {isSubmitting ? t('rules.publish.submitting') : t('rules.publish.submit')}
        </Button>
      </div>
    </article>
  );
}

function PolicyLifecyclePanel({
  t,
  policies,
  selectedPolicy,
  isLoading,
  policyId,
  comparePolicyId,
  reason,
  canApprove,
  canPublish,
  policyDiff,
  isApprovePending,
  isRejectPending,
  isPublishPending,
  isRollbackPending,
  isDiffPending,
  onPolicyIdChange,
  onComparePolicyIdChange,
  onReasonChange,
  onApprove,
  onReject,
  onPublish,
  onRollback,
  onDiff,
}: {
  t: TranslationFn;
  policies: AdminGrowthRulePolicyVersionResponse[];
  selectedPolicy: AdminGrowthRulePolicyVersionResponse | null;
  isLoading: boolean;
  policyId: string;
  comparePolicyId: string;
  reason: string;
  canApprove: boolean;
  canPublish: boolean;
  policyDiff: AdminGrowthRulePolicyDiffResponse | null;
  isApprovePending: boolean;
  isRejectPending: boolean;
  isPublishPending: boolean;
  isRollbackPending: boolean;
  isDiffPending: boolean;
  onPolicyIdChange: (value: string) => void;
  onComparePolicyIdChange: (value: string) => void;
  onReasonChange: (value: string) => void;
  onApprove: () => void;
  onReject: () => void;
  onPublish: () => void;
  onRollback: () => void;
  onDiff: () => void;
}) {
  const reasonPresent = Boolean(reason.trim());
  const selectedApprovalState = selectedPolicy?.approval_state.toLowerCase();
  const canRunApprove = Boolean(canApprove && policyId && reasonPresent);
  const canRunPublish = Boolean(
    canPublish && policyId && reasonPresent && selectedApprovalState === 'approved',
  );
  const canRunRollback = Boolean(canPublish && policyId && reasonPresent);

  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex items-start gap-3">
        <History className="mt-0.5 h-5 w-5 text-neon-cyan" aria-hidden="true" />
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('rules.lifecycle.title')}
          </h2>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {t('rules.lifecycle.description')}
          </p>
        </div>
      </div>

      {!canApprove && !canPublish ? (
        <div className="mt-5">
          <RulePermissionNotice>{t('rules.permission.auditReadOnly')}</RulePermissionNotice>
        </div>
      ) : null}

      <div className="mt-5 grid gap-4">
        <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
          {t('rules.lifecycle.policyId')}
          <input
            value={policyId}
            onChange={(event) => onPolicyIdChange(event.target.value)}
            className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
          />
        </label>
        <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
          {t('rules.lifecycle.comparePolicyId')}
          <input
            value={comparePolicyId}
            onChange={(event) => onComparePolicyIdChange(event.target.value)}
            className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
          />
        </label>
        <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
          {t('rules.lifecycle.reasonCode')}
          <input
            value={reason}
            disabled={!canApprove && !canPublish}
            onChange={(event) => onReasonChange(event.target.value)}
            className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
          />
        </label>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <Button
          type="button"
          variant="outline"
          magnetic={false}
          disabled={!policyId || isDiffPending}
          onClick={onDiff}
        >
          <GitCompare className="mr-2 h-4 w-4" aria-hidden="true" />
          {isDiffPending ? t('rules.lifecycle.loadingDiff') : t('rules.lifecycle.loadDiff')}
        </Button>
        <Button
          type="button"
          variant="outline"
          magnetic={false}
          disabled={!canRunApprove || isApprovePending}
          onClick={onApprove}
        >
          {isApprovePending ? t('rules.lifecycle.running') : t('rules.lifecycle.approve')}
        </Button>
        <Button
          type="button"
          variant="outline"
          magnetic={false}
          disabled={!canRunApprove || isRejectPending}
          onClick={onReject}
        >
          {isRejectPending ? t('rules.lifecycle.running') : t('rules.lifecycle.reject')}
        </Button>
        <Button
          type="button"
          variant="outline"
          magnetic={false}
          disabled={!canRunPublish || isPublishPending}
          onClick={onPublish}
        >
          {isPublishPending ? t('rules.lifecycle.running') : t('rules.lifecycle.publish')}
        </Button>
        <Button
          type="button"
          variant="outline"
          magnetic={false}
          disabled={!canRunRollback || isRollbackPending}
          onClick={onRollback}
        >
          {isRollbackPending ? t('rules.lifecycle.running') : t('rules.lifecycle.rollback')}
        </Button>
      </div>

      <section className="mt-6" aria-label={t('rules.lifecycle.auditTitle')}>
        <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
          {t('rules.lifecycle.auditTitle')}
        </h3>
        {isLoading ? (
          <p className="mt-3 text-xs font-mono text-muted-foreground">
            {t('rules.lifecycle.loadingPolicies')}
          </p>
        ) : policies.length ? (
          <div className="mt-3 space-y-3">
            {policies.map((policy) => (
              <div
                key={policy.id}
                className="rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <GrowthStatusChip
                    label={`#${policy.version_number}`}
                    tone="info"
                  />
                  <GrowthStatusChip
                    label={policy.approval_state}
                    tone={policyTone(policy.approval_state)}
                  />
                  <GrowthStatusChip
                    label={policy.version_status}
                    tone={policyTone(policy.version_status)}
                  />
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <InfoLine label={t('rules.lifecycle.auditFields.id')} value={policy.id} />
                  <InfoLine
                    label={t('rules.lifecycle.auditFields.checksum')}
                    value={policy.compiled_checksum ?? t('common.missing')}
                  />
                  <InfoLine
                    label={t('rules.lifecycle.auditFields.createdBy')}
                    value={policy.created_by_admin_user_id ?? t('common.missing')}
                  />
                  <InfoLine
                    label={t('rules.lifecycle.auditFields.approvedBy')}
                    value={policy.approved_by_admin_user_id ?? t('common.missing')}
                  />
                  <InfoLine
                    label={t('rules.lifecycle.auditFields.approvedAt')}
                    value={policy.approved_at ?? t('common.missing')}
                  />
                  <InfoLine
                    label={t('rules.lifecycle.auditFields.effectiveFrom')}
                    value={policy.effective_from}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-3">
            <GrowthEmptyState label={t('rules.lifecycle.emptyPolicies')} />
          </div>
        )}
      </section>

      <section className="mt-6" aria-label={t('rules.lifecycle.backendDiffTitle')}>
        <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
          {t('rules.lifecycle.backendDiffTitle')}
        </h3>
        {policyDiff ? (
          <div className="mt-3 rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <GrowthStatusChip
                label={policyDiff.changed ? t('rules.lifecycle.diffChanged') : t('rules.lifecycle.diffUnchanged')}
                tone={policyDiff.changed ? 'warning' : 'success'}
              />
              <GrowthStatusChip
                label={policyDiff.policy_version_id}
                tone="neutral"
              />
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <InfoLine
                label={t('rules.lifecycle.auditFields.currentChecksum')}
                value={policyDiff.current_checksum ?? t('common.missing')}
              />
              <InfoLine
                label={t('rules.lifecycle.auditFields.compareChecksum')}
                value={policyDiff.compare_checksum ?? t('common.missing')}
              />
            </div>
            <pre className="mt-4 max-h-44 overflow-auto whitespace-pre-wrap break-words text-xs text-foreground">
              {stringifyUnknown(policyDiff.changed_fields)}
            </pre>
          </div>
        ) : (
          <div className="mt-3">
            <GrowthEmptyState label={t('rules.lifecycle.emptyDiff')} />
          </div>
        )}
      </section>
    </article>
  );
}

interface SimulatorPanelProps {
  t: TranslationFn;
  canValidate: boolean;
  contextEditorId: string;
  contextErrorId: string;
  contextJson: string;
  contextError: string | null;
  simulationResult: AdminGrowthRuleSimulateResponse | null;
  onContextChange: (value: string) => void;
  onSimulate: () => void;
  isSimulating: boolean;
}

function SimulatorPanel({
  t,
  canValidate,
  contextEditorId,
  contextErrorId,
  contextJson,
  contextError,
  simulationResult,
  onContextChange,
  onSimulate,
  isSimulating,
}: SimulatorPanelProps) {
  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('rules.simulator.title')}
          </h2>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {t('rules.simulator.description')}
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          magnetic={false}
          onClick={onSimulate}
          disabled={!canValidate || isSimulating}
        >
          <Play className="mr-2 h-4 w-4" aria-hidden="true" />
          {isSimulating ? t('rules.actions.simulating') : t('rules.actions.simulate')}
        </Button>
      </div>

      <label
        htmlFor={contextEditorId}
        className="mt-5 block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground"
      >
        {t('rules.simulator.contextLabel')}
      </label>
      <textarea
        id={contextEditorId}
        value={contextJson}
        disabled={!canValidate}
        onChange={(event) => onContextChange(event.target.value)}
        aria-invalid={Boolean(contextError)}
        aria-describedby={contextError ? contextErrorId : undefined}
        spellCheck={false}
        className="mt-2 min-h-56 w-full resize-y rounded-lg border border-grid-line/25 bg-terminal-bg/70 p-4 font-mono text-xs leading-5 text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
      />
      {contextError ? (
        <p id={contextErrorId} className="mt-2 text-xs font-mono text-neon-pink">
          {t('rules.errors.contextInvalid', { detail: contextError })}
        </p>
      ) : null}

      {simulationResult ? (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <GrowthStatusChip
                label={simulationResult.matched ? t('rules.simulator.matched') : t('rules.simulator.notMatched')}
                tone={simulationResult.matched ? 'success' : 'neutral'}
              />
              <GrowthStatusChip label={simulationResult.result} tone="info" />
            </div>
            <InfoLine
              className="mt-4"
              label={t('rules.simulator.checksum')}
              value={simulationResult.compiled_checksum}
            />
          </div>
          <div className="rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4">
            <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
              {t('rules.simulator.actionsTitle')}
            </h3>
            <pre className="mt-3 max-h-52 overflow-auto whitespace-pre-wrap break-words text-xs text-foreground">
              {stringifyUnknown(simulationResult.actions)}
            </pre>
          </div>
          <div className="rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4 lg:col-span-2">
            <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
              {t('rules.simulator.traceTitle')}
            </h3>
            <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words text-xs text-foreground">
              {stringifyUnknown(simulationResult.trace)}
            </pre>
          </div>
        </div>
      ) : (
        <div className="mt-5">
          <GrowthEmptyState label={t('rules.simulator.empty')} />
        </div>
      )}
    </article>
  );
}

function VersionDiffPanel({
  t,
  draftJson,
  compiledRule,
}: {
  t: TranslationFn;
  draftJson: string;
  compiledRule: AdminGrowthRuleCompileResponse | null;
}) {
  const summary = summarizeVersionDiff(draftJson, compiledRule);
  const diffTone = summary.status === 'match'
    ? 'success'
    : summary.status === 'changed'
      ? 'warning'
      : summary.status === 'invalid'
        ? 'danger'
        : 'neutral';

  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex items-start gap-3">
        <GitCompare className="mt-0.5 h-5 w-5 text-neon-cyan" aria-hidden="true" />
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('rules.diff.title')}
          </h2>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {t('rules.diff.description')}
          </p>
        </div>
      </div>
      <div
        role="status"
        aria-live="polite"
        className="mt-5 grid gap-3 rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4 sm:grid-cols-[auto_1fr]"
      >
        <GrowthStatusChip label={t(`rules.diff.status.${summary.status}`)} tone={diffTone} />
        <p className="text-xs font-mono leading-5 text-muted-foreground">
          {t('rules.diff.statusDescription')}
        </p>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <MetricCell
          label={t('rules.diff.changedLines')}
          value={String(summary.changedLines)}
        />
        <MetricCell
          label={t('rules.diff.addedLines')}
          value={String(summary.addedLines)}
        />
        <MetricCell
          label={t('rules.diff.removedLines')}
          value={String(summary.removedLines)}
        />
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
            {t('rules.diff.draft')}
          </h3>
          <pre
            tabIndex={0}
            aria-label={t('rules.diff.draft')}
            className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4 text-xs text-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
          >
            {draftJson}
          </pre>
        </div>
        <div>
          <h3 className="text-xs font-display uppercase tracking-[0.2em] text-white">
            {t('rules.diff.normalized')}
          </h3>
          <pre
            tabIndex={0}
            aria-label={t('rules.diff.normalized')}
            className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4 text-xs text-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
          >
            {summary.normalizedJson ?? t('rules.diff.empty')}
          </pre>
        </div>
      </div>
    </article>
  );
}

function InfoLine({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className={cn('min-w-0', className)}>
      <p className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 break-words font-mono text-xs text-foreground">{value}</p>
    </div>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-3">
      <p className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 font-display text-xl tracking-[0.1em] text-white">{value}</p>
    </div>
  );
}
