export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export interface GrowthRuleCatalogField {
  type: string;
  operators: string[];
}

export interface GrowthRuleCatalogOperator {
  valueTypes: string[];
  safeRegex?: boolean;
}

export interface GrowthRuleCatalogAction {
  result: string;
  params: string[];
}

export interface GrowthRuleCatalogLimits {
  maxNodes?: number;
  maxDepth?: number;
  maxActions?: number;
  maxRegexLength?: number;
}

export interface GrowthRuleCatalog {
  catalogVersion: string;
  schemaVersion: string;
  limits: GrowthRuleCatalogLimits;
  fields: Record<string, GrowthRuleCatalogField>;
  operators: Record<string, GrowthRuleCatalogOperator>;
  actions: Record<string, GrowthRuleCatalogAction>;
}

export type RuleTreeRow =
  | {
      id: string;
      type: 'group';
      groupType: 'all' | 'any' | 'not';
      depth: number;
      path: string[];
      childCount: number;
    }
  | {
      id: string;
      type: 'condition';
      depth: number;
      path: string[];
      field: string;
      operator: string;
      value: JsonValue | undefined;
    }
  | {
      id: string;
      type: 'unsupported';
      depth: number;
      path: string[];
      nodeType: string;
    };

export type RuleActionRow = {
  id: string;
  index: number;
  action: string;
  result?: string;
  params: JsonObject;
};

export const DEFAULT_RULE_AST: JsonObject = {
  schema_version: 'growth-rule.v1',
  when: {
    type: 'all',
    children: [
      {
        type: 'condition',
        field: 'code.code_type',
        operator: 'eq',
        value: 'promo',
      },
      {
        type: 'condition',
        field: 'risk.score',
        operator: 'gte',
        value: '0.85',
      },
    ],
  },
  then: [
    {
      action: 'challenge',
      params: {
        challenge_type: 'email_otp',
        message_key: 'growth.rules.challenge.high_risk',
      },
    },
  ],
};

export const DEFAULT_SIMULATION_CONTEXT: JsonObject = {
  code: {
    code_type: 'promo',
  },
  risk: {
    score: '0.91',
  },
};

const EMPTY_CATALOG: GrowthRuleCatalog = {
  catalogVersion: '',
  schemaVersion: '',
  limits: {},
  fields: {},
  operators: {},
  actions: {},
};

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isJsonValue(value: unknown): value is JsonValue {
  if (
    value === null ||
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return true;
  }

  if (Array.isArray(value)) {
    return value.every(isJsonValue);
  }

  if (!isRecord(value)) {
    return false;
  }

  return Object.values(value).every(isJsonValue);
}

export function parseJsonObject(input: string): JsonObject {
  const parsed: unknown = JSON.parse(input);

  if (!isRecord(parsed) || !isJsonValue(parsed)) {
    throw new Error('Expected a JSON object.');
  }

  return parsed;
}

export function formatJson(value: JsonValue): string {
  return `${JSON.stringify(value, null, 2)}\n`;
}

export function normalizeRuleCatalog(rawCatalog: unknown): GrowthRuleCatalog {
  if (!isRecord(rawCatalog)) {
    return EMPTY_CATALOG;
  }

  const rawFields = isRecord(rawCatalog.fields) ? rawCatalog.fields : {};
  const rawOperators = isRecord(rawCatalog.operators) ? rawCatalog.operators : {};
  const rawActions = isRecord(rawCatalog.actions) ? rawCatalog.actions : {};
  const rawLimits = isRecord(rawCatalog.limits) ? rawCatalog.limits : {};

  return {
    catalogVersion: stringValue(rawCatalog.catalog_version),
    schemaVersion: stringValue(rawCatalog.schema_version),
    limits: {
      maxNodes: numberValue(rawLimits.max_nodes),
      maxDepth: numberValue(rawLimits.max_depth),
      maxActions: numberValue(rawLimits.max_actions),
      maxRegexLength: numberValue(rawLimits.max_regex_length),
    },
    fields: Object.fromEntries(
      Object.entries(rawFields)
        .filter((entry): entry is [string, Record<string, unknown>] => isRecord(entry[1]))
        .map(([field, spec]) => [
          field,
          {
            type: stringValue(spec.type),
            operators: stringArray(spec.operators),
          },
        ]),
    ),
    operators: Object.fromEntries(
      Object.entries(rawOperators)
        .filter((entry): entry is [string, Record<string, unknown>] => isRecord(entry[1]))
        .map(([operator, spec]) => [
          operator,
          {
            valueTypes: stringArray(spec.value_types),
            safeRegex: typeof spec.safe_regex === 'boolean' ? spec.safe_regex : undefined,
          },
        ]),
    ),
    actions: Object.fromEntries(
      Object.entries(rawActions)
        .filter((entry): entry is [string, Record<string, unknown>] => isRecord(entry[1]))
        .map(([action, spec]) => [
          action,
          {
            result: stringValue(spec.result),
            params: stringArray(spec.params),
          },
        ]),
    ),
  };
}

export function collectRuleTreeRows(ast: JsonObject): RuleTreeRow[] {
  const when = ast.when;

  if (!isRecord(when)) {
    return [];
  }

  return collectConditionRows(when, ['when'], 1);
}

export function collectRuleActionRows(ast: JsonObject): RuleActionRow[] {
  if (!Array.isArray(ast.then)) {
    return [];
  }

  return ast.then.flatMap((item, index) => {
    if (!isRecord(item)) {
      return [];
    }

    const params = isRecord(item.params) && isJsonValue(item.params) ? item.params : {};
    const result = typeof item.result === 'string' ? item.result : undefined;

    return [
      {
        id: `then.${index}`,
        index,
        action: stringValue(item.action),
        result,
        params,
      },
    ];
  });
}

export function addConditionToAst(
  ast: JsonObject,
  field: string,
  operator: string,
  value: JsonValue,
): JsonObject {
  const nextAst = cloneJsonObject(ast);
  const condition: JsonObject = {
    type: 'condition',
    field,
    operator,
    value,
  };

  if (!isRecord(nextAst.when)) {
    nextAst.when = {
      type: 'all',
      children: [condition],
    };
    return nextAst;
  }

  if (nextAst.when.type === 'all' || nextAst.when.type === 'any') {
    const children = Array.isArray(nextAst.when.children) ? nextAst.when.children : [];
    nextAst.when = {
      ...nextAst.when,
      children: [...children.filter(isJsonValue), condition],
    };
    return nextAst;
  }

  nextAst.when = {
    type: 'all',
    children: [nextAst.when as JsonObject, condition],
  };
  return nextAst;
}

export function updateConditionAtPath(
  ast: JsonObject,
  path: string[],
  updates: {
    field: string;
    operator: string;
    value: JsonValue;
  },
): JsonObject {
  const nextAst = cloneJsonObject(ast);
  const node = getMutableNodeAtPath(nextAst, path);

  if (!isRecord(node) || node.type !== 'condition') {
    return nextAst;
  }

  node.field = updates.field;
  node.operator = updates.operator;
  node.value = updates.value;
  return nextAst;
}

export function removeNodeAtPath(ast: JsonObject, path: string[]): JsonObject {
  const nextAst = cloneJsonObject(ast);
  if (path.length < 2) {
    return nextAst;
  }

  const parentPath = path.slice(0, -1);
  const lastPart = path.at(-1);
  const parent = getMutableNodeAtPath(nextAst, parentPath);

  if (!Array.isArray(parent) || lastPart == null) {
    return nextAst;
  }

  const index = Number(lastPart);
  if (Number.isInteger(index)) {
    parent.splice(index, 1);
  }

  return nextAst;
}

export function duplicateNodeAtPath(ast: JsonObject, path: string[]): JsonObject {
  const nextAst = cloneJsonObject(ast);
  if (path.length < 2) {
    return nextAst;
  }

  const parentPath = path.slice(0, -1);
  const lastPart = path.at(-1);
  const parent = getMutableNodeAtPath(nextAst, parentPath);
  const node = getMutableNodeAtPath(nextAst, path);

  if (!Array.isArray(parent) || lastPart == null || !isJsonValue(node)) {
    return nextAst;
  }

  const index = Number(lastPart);
  if (Number.isInteger(index)) {
    parent.splice(index + 1, 0, cloneJson(node));
  }

  return nextAst;
}

export function moveNodeAtPath(
  ast: JsonObject,
  path: string[],
  direction: 'up' | 'down',
): JsonObject {
  const nextAst = cloneJsonObject(ast);
  if (path.length < 2) {
    return nextAst;
  }

  const parentPath = path.slice(0, -1);
  const lastPart = path.at(-1);
  const parent = getMutableNodeAtPath(nextAst, parentPath);

  if (!Array.isArray(parent) || lastPart == null) {
    return nextAst;
  }

  const currentIndex = Number(lastPart);
  if (!Number.isInteger(currentIndex)) {
    return nextAst;
  }

  const nextIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
  if (nextIndex < 0 || nextIndex >= parent.length) {
    return nextAst;
  }

  const [node] = parent.splice(currentIndex, 1);
  if (node !== undefined) {
    parent.splice(nextIndex, 0, node);
  }

  return nextAst;
}

export function addActionToAst(
  ast: JsonObject,
  action: string,
  params: JsonObject,
): JsonObject {
  const nextAst = cloneJsonObject(ast);
  const currentActions = Array.isArray(nextAst.then) ? nextAst.then.filter(isJsonValue) : [];
  nextAst.then = [
    ...currentActions,
    {
      action,
      params,
    },
  ];
  return nextAst;
}

export function removeActionAtIndex(ast: JsonObject, actionIndex: number): JsonObject {
  const nextAst = cloneJsonObject(ast);
  const currentActions = Array.isArray(nextAst.then) ? nextAst.then.filter(isJsonValue) : [];
  nextAst.then = currentActions.filter((_item, index) => index !== actionIndex);
  return nextAst;
}

export function setRootGroupOperator(ast: JsonObject, operator: 'all' | 'any'): JsonObject {
  const nextAst = cloneJsonObject(ast);
  const when = isRecord(nextAst.when) ? nextAst.when : null;

  if (when && (when.type === 'all' || when.type === 'any')) {
    nextAst.when = {
      ...when,
      type: operator,
    };
    return nextAst;
  }

  if (when && isJsonValue(when)) {
    nextAst.when = {
      type: operator,
      children: [when],
    };
    return nextAst;
  }

  nextAst.when = {
    type: operator,
    children: [],
  };
  return nextAst;
}

export function buildSampleValue(fieldType: string, operator: string, field: string): JsonValue {
  const scalarValue = buildScalarSampleValue(fieldType, field);
  if (operator === 'in' || operator === 'not_in') {
    return [scalarValue];
  }
  return scalarValue;
}

export function parseConditionInputValue(
  rawValue: string,
  fieldType: string,
  operator: string,
): JsonValue {
  if (operator === 'in' || operator === 'not_in') {
    return rawValue
      .split(',')
      .map((item) => parseScalarValue(item.trim(), fieldType))
      .filter((item) => item !== '');
  }

  return parseScalarValue(rawValue, fieldType);
}

export function stringifyConditionValue(value: JsonValue | undefined): string {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(', ');
  }

  if (value == null) {
    return '';
  }

  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  return String(value);
}

export function buildActionParams(actionSpec: GrowthRuleCatalogAction | undefined): JsonObject {
  if (!actionSpec) {
    return {};
  }

  return Object.fromEntries(
    actionSpec.params.map((param) => [param, buildActionParamValue(param)]),
  );
}

export function rulePathToId(path: string[]): string {
  return path.join('.');
}

function collectConditionRows(
  node: Record<string, unknown>,
  path: string[],
  depth: number,
): RuleTreeRow[] {
  const nodeType = stringValue(node.type);

  if (nodeType === 'all' || nodeType === 'any') {
    const children = Array.isArray(node.children) ? node.children : [];
    return [
      {
        id: rulePathToId(path),
        type: 'group',
        groupType: nodeType,
        depth,
        path,
        childCount: children.length,
      },
      ...children.flatMap((child, index) =>
        isRecord(child)
          ? collectConditionRows(child, [...path, 'children', String(index)], depth + 1)
          : [],
      ),
    ];
  }

  if (nodeType === 'not') {
    const child = node.child;
    return [
      {
        id: rulePathToId(path),
        type: 'group',
        groupType: 'not',
        depth,
        path,
        childCount: isRecord(child) ? 1 : 0,
      },
      ...(isRecord(child) ? collectConditionRows(child, [...path, 'child'], depth + 1) : []),
    ];
  }

  if (nodeType === 'condition') {
    return [
      {
        id: rulePathToId(path),
        type: 'condition',
        depth,
        path,
        field: stringValue(node.field),
        operator: stringValue(node.operator),
        value: isJsonValue(node.value) ? node.value : undefined,
      },
    ];
  }

  return [
    {
      id: rulePathToId(path),
      type: 'unsupported',
      depth,
      path,
      nodeType,
    },
  ];
}

function cloneJsonObject(value: JsonObject): JsonObject {
  return cloneJson(value);
}

function cloneJson<T extends JsonValue>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function getMutableNodeAtPath(root: JsonObject, path: string[]): unknown {
  return path.reduce<unknown>((current, segment) => {
    if (Array.isArray(current)) {
      return current[Number(segment)];
    }

    if (isRecord(current)) {
      return current[segment];
    }

    return undefined;
  }, root);
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function numberValue(value: unknown): number | undefined {
  return typeof value === 'number' ? value : undefined;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function buildScalarSampleValue(fieldType: string, field: string): JsonPrimitive {
  if (fieldType === 'boolean') {
    return true;
  }

  if (fieldType === 'integer') {
    return 1;
  }

  if (fieldType === 'decimal') {
    return '0.85';
  }

  if (field === 'checkout.currency') {
    return 'USD';
  }

  if (field === 'checkout.sale_channel') {
    return 'web';
  }

  if (field === 'code.code_type') {
    return 'promo';
  }

  if (field === 'private_catalog.access_class') {
    return 'private';
  }

  return 'value';
}

function parseScalarValue(rawValue: string, fieldType: string): JsonPrimitive {
  if (fieldType === 'boolean') {
    return rawValue === 'true';
  }

  if (fieldType === 'integer') {
    const parsed = Number.parseInt(rawValue, 10);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  return rawValue;
}

function buildActionParamValue(param: string): JsonPrimitive {
  if (param.endsWith('_key')) {
    return `growth.rules.${param}`;
  }

  if (param === 'challenge_type') {
    return 'email_otp';
  }

  if (param === 'queue') {
    return 'risk';
  }

  return 'value';
}
