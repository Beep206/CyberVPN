import { describe, expect, it } from 'vitest';
import {
  getCanonicalLocaleForPath,
  getIndexableLocalesForPath,
  getLocaleRolloutTier,
  isExpandedContentPath,
  isLocaleIndexableForPath,
} from '@/shared/lib/locale-rollout-policy';

describe('locale-rollout-policy', () => {
  it('keeps core marketing routes indexable for tier1 locales', () => {
    expect(getLocaleRolloutTier('en-EN')).toBe('tier1');
    expect(getLocaleRolloutTier('ar-SA')).toBe('tier2');
    expect(getLocaleRolloutTier('fr-FR')).toBe('tier3');

    expect(getIndexableLocalesForPath('/pricing')).toEqual([
      'en-EN',
      'ru-RU',
      'zh-CN',
      'hi-IN',
      'id-ID',
      'vi-VN',
      'th-TH',
      'ja-JP',
      'ko-KR',
    ]);
    expect(isLocaleIndexableForPath('ru-RU', '/pricing')).toBe(true);
    expect(isLocaleIndexableForPath('ja-JP', '/pricing')).toBe(true);
    expect(isLocaleIndexableForPath('fa-IR', '/pricing')).toBe(false);
  });

  it('indexes exact market hubs and detail content across all priority locales', () => {
    expect(isExpandedContentPath('/guides')).toBe(true);
    expect(isExpandedContentPath('/guides/how-to-bypass-dpi-with-vless-reality')).toBe(true);
    expect(isExpandedContentPath('/trust')).toBe(true);
    expect(isExpandedContentPath('/pricing')).toBe(false);

    expect(getIndexableLocalesForPath('/guides')).toEqual([
      'en-EN',
      'ru-RU',
      'zh-CN',
      'hi-IN',
      'id-ID',
      'vi-VN',
      'th-TH',
      'ja-JP',
      'ko-KR',
    ]);
    expect(isLocaleIndexableForPath('en-EN', '/guides')).toBe(true);
    expect(isLocaleIndexableForPath('ru-RU', '/guides')).toBe(true);
    expect(getCanonicalLocaleForPath('/guides', 'ru-RU')).toBe('ru-RU');
    expect(getIndexableLocalesForPath('/guides/how-to-bypass-dpi-with-vless-reality')).toEqual([
      'en-EN',
      'ru-RU',
      'zh-CN',
      'hi-IN',
      'id-ID',
      'vi-VN',
      'th-TH',
      'ja-JP',
      'ko-KR',
    ]);
    expect(isLocaleIndexableForPath('ru-RU', '/guides/how-to-bypass-dpi-with-vless-reality')).toBe(
      true,
    );
    expect(isLocaleIndexableForPath('zh-CN', '/guides/how-to-bypass-dpi-with-vless-reality')).toBe(
      true,
    );
    expect(isLocaleIndexableForPath('hi-IN', '/guides/how-to-bypass-dpi-with-vless-reality')).toBe(
      true,
    );
    expect(isLocaleIndexableForPath('ja-JP', '/guides/how-to-bypass-dpi-with-vless-reality')).toBe(
      true,
    );
    expect(isLocaleIndexableForPath('fa-IR', '/guides/how-to-bypass-dpi-with-vless-reality')).toBe(
      false,
    );
    expect(getCanonicalLocaleForPath('/guides/how-to-bypass-dpi-with-vless-reality', 'ru-RU')).toBe(
      'ru-RU',
    );
    expect(getCanonicalLocaleForPath('/guides/how-to-bypass-dpi-with-vless-reality', 'hi-IN')).toBe(
      'hi-IN',
    );
    expect(getCanonicalLocaleForPath('/guides/how-to-bypass-dpi-with-vless-reality', 'fa-IR')).toBe(
      'en-EN',
    );
  });
});
