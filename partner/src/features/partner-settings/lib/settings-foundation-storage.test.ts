import { beforeEach, describe, expect, it } from 'vitest';
import {
  EMPTY_PARTNER_SETTINGS_FOUNDATION_DRAFT,
  PARTNER_SETTINGS_FOUNDATION_STORAGE_KEY,
  clearPartnerSettingsFoundationDraft,
  loadPartnerSettingsFoundationDraft,
  savePartnerSettingsFoundationDraft,
} from './settings-foundation-storage';

describe('partner settings foundation storage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('saves and loads local settings baseline', () => {
    const draft = {
      ...EMPTY_PARTNER_SETTINGS_FOUNDATION_DRAFT,
      preferredLanguage: 'ru-RU',
      requireMfaForWorkspace: true,
      updatedAt: '2026-04-18T10:00:00.000Z',
    };

    savePartnerSettingsFoundationDraft(draft);

    expect(loadPartnerSettingsFoundationDraft()).toEqual(draft);
  });

  it('returns null for invalid stored data', () => {
    window.localStorage.setItem(
      PARTNER_SETTINGS_FOUNDATION_STORAGE_KEY,
      '{broken-json',
    );

    expect(loadPartnerSettingsFoundationDraft()).toBeNull();
  });

  it('clears the settings draft', () => {
    savePartnerSettingsFoundationDraft({
      ...EMPTY_PARTNER_SETTINGS_FOUNDATION_DRAFT,
      preferredLanguage: 'en-EN',
    });

    clearPartnerSettingsFoundationDraft();

    expect(window.localStorage.getItem(PARTNER_SETTINGS_FOUNDATION_STORAGE_KEY)).toBeNull();
  });
});
