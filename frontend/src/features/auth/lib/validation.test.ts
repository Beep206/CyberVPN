import { describe, expect, it } from 'vitest';
import {
  PASSWORD_MIN_LENGTH,
  getPasswordRequirements,
  normalizeEmailInput,
  validateEmailInput,
  validateLoginIdentifierInput,
  validatePasswordInput,
} from './validation';

describe('auth validation', () => {
  it('normalizes and validates practical email input without overfitting to one regex', () => {
    expect(normalizeEmailInput('  user@example.com  ')).toBe('user@example.com');
    expect(validateEmailInput('user@example.com')).toEqual({ isValid: true, codes: [] });
    expect(validateEmailInput('  user@example.com  ')).toEqual({
      isValid: false,
      codes: ['emailNoSpaces'],
    });
    expect(validateEmailInput('missing-at.example.com').codes).toContain('emailInvalid');
    expect(validateEmailInput('').codes).toContain('emailRequired');
  });

  it('rejects too-long local parts before backend uniqueness checks run', () => {
    const localPart = 'a'.repeat(65);
    const result = validateEmailInput(`${localPart}@example.com`);

    expect(result.isValid).toBe(false);
    expect(result.codes).toContain('emailTooLong');
  });

  it('validates login identifiers without blocking username login', () => {
    expect(validateLoginIdentifierInput('sasha_beep')).toEqual({ isValid: true, codes: [] });
    expect(validateLoginIdentifierInput('user@example.com')).toEqual({ isValid: true, codes: [] });
    expect(validateLoginIdentifierInput('')).toEqual({
      isValid: false,
      codes: ['loginIdentifierRequired'],
    });
    expect(validateLoginIdentifierInput('broken@example').codes).toContain('emailInvalid');
    expect(validateLoginIdentifierInput(' user@example.com ').codes).toContain('emailNoSpaces');
  });

  it('accepts a strong ASCII password and exposes requirement status for the UI', () => {
    const password = 'CyberVPN-2026!';

    expect(validatePasswordInput(password)).toEqual({ isValid: true, codes: [] });
    expect(getPasswordRequirements(password)).toEqual(
      expect.arrayContaining([
        { code: 'passwordMinLength', met: true },
        { code: 'passwordLatinLayout', met: true },
        { code: 'passwordCommon', met: true },
      ]),
    );
  });

  it('flags short, common, repeated, numeric-sequence, and non-latin password input', () => {
    expect(PASSWORD_MIN_LENGTH).toBe(12);
    expect(validatePasswordInput('').codes).toEqual(['passwordRequired']);
    expect(validatePasswordInput('password').codes).toEqual(
      expect.arrayContaining([
        'passwordMinLength',
        'passwordUppercase',
        'passwordNumber',
        'passwordSpecial',
        'passwordCommon',
      ]),
    );
    expect(validatePasswordInput('Аа123456789!').codes).toContain('passwordLatinLayout');
    expect(validatePasswordInput('111111111111').codes).toEqual(
      expect.arrayContaining(['passwordRepeated', 'passwordSpecial']),
    );
    expect(validatePasswordInput('123456789012').codes).toContain('passwordNumericSequence');
  });
});
