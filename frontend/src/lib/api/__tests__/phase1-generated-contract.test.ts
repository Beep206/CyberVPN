// @vitest-environment node

import { describe, expect, it } from 'vitest';
import type { components, paths } from '../generated/types';

const PHASE1_FRONTEND_PATHS = [
  '/api/v1/auth/login',
  '/api/v1/auth/me',
  '/api/v1/realms/resolve',
  '/api/v1/offers/',
  '/api/v1/pricebooks/resolve',
  '/api/v1/program-eligibility/',
  '/api/v1/legal-documents/sets/resolve',
  '/api/v1/policy-acceptance/',
  '/api/v1/policy-acceptance/me',
] as const satisfies readonly (keyof paths)[];

type Phase1RealmResolutionResponse = components['schemas']['RealmResolutionResponse'];
type Phase1PricebookResponse = components['schemas']['PricebookResponse'];
type Phase1AcceptedLegalDocumentResponse = components['schemas']['AcceptedLegalDocumentResponse'];

describe('Phase 1 generated API contract', () => {
  it('includes the frozen Phase 1 customer-facing path families', () => {
    expect(PHASE1_FRONTEND_PATHS).toContain('/api/v1/pricebooks/resolve');
    expect(PHASE1_FRONTEND_PATHS).toContain('/api/v1/policy-acceptance/');
  });

  it('exposes the required Phase 1 customer-facing schemas', () => {
    const compileGuard: {
      realmResolution: Phase1RealmResolutionResponse | null;
      pricebook: Phase1PricebookResponse | null;
      acceptedLegalDocument: Phase1AcceptedLegalDocumentResponse | null;
    } = {
      realmResolution: null,
      pricebook: null,
      acceptedLegalDocument: null,
    };

    expect(compileGuard).toEqual({
      realmResolution: null,
      pricebook: null,
      acceptedLegalDocument: null,
    });
  });
});
