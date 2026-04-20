import { beforeEach, describe, expect, it } from 'vitest';
import {
  EMPTY_PARTNER_APPLICATION_DRAFT,
  PARTNER_APPLICATION_DRAFT_STORAGE_KEY,
  clearPartnerApplicationDraft,
  loadPartnerApplicationDraft,
  savePartnerApplicationDraft,
} from './application-draft-storage';

describe('partner application draft storage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('saves and loads the application draft', () => {
    const draft = {
      ...EMPTY_PARTNER_APPLICATION_DRAFT,
      workspaceName: 'North Star Growth',
      contactEmail: 'ops@example.com',
      primaryLane: 'creator_affiliate' as const,
      updatedAt: '2026-04-18T10:00:00.000Z',
    };

    savePartnerApplicationDraft(draft);

    expect(loadPartnerApplicationDraft()).toEqual(draft);
  });

  it('returns null for invalid stored JSON', () => {
    window.localStorage.setItem(
      PARTNER_APPLICATION_DRAFT_STORAGE_KEY,
      '{broken-json',
    );

    expect(loadPartnerApplicationDraft()).toBeNull();
  });

  it('clears the stored draft', () => {
    savePartnerApplicationDraft({
      ...EMPTY_PARTNER_APPLICATION_DRAFT,
      workspaceName: 'To Clear',
    });

    clearPartnerApplicationDraft();

    expect(window.localStorage.getItem(PARTNER_APPLICATION_DRAFT_STORAGE_KEY)).toBeNull();
  });
});
