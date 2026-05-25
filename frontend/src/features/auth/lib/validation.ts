export const PASSWORD_MIN_LENGTH = 12;

const EMAIL_MAX_LENGTH = 254;
const EMAIL_LOCAL_PART_MAX_LENGTH = 64;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/u;
const ASCII_PRINTABLE_PATTERN = /^[\x21-\x7E]+$/u;
const CYRILLIC_PATTERN = /[\u0400-\u04FF]/u;
const PASSWORD_SPECIAL_PATTERN = /[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;'/`~]/u;
const REPEATED_CHARACTER_PATTERN = /^(.)\1+$/u;
const SIMPLE_NUMERIC_SEQUENCE_PATTERN = /^(012|123|234|345|456|567|678|789|890)+$/u;

const COMMON_PASSWORDS = new Set([
  '123456',
  'password',
  '12345678',
  'qwerty',
  '123456789',
  '12345',
  '1234',
  '111111',
  '1234567',
  'dragon',
  '123123',
  'baseball',
  'iloveyou',
  'trustno1',
  'sunshine',
  'master',
  'welcome',
  'shadow',
  'ashley',
  'football',
  'jesus',
  'michael',
  'ninja',
  'mustang',
  'password1',
  'password123',
  'batman',
  'letmein',
  'qwerty123',
  'login',
  'admin',
  'abc123',
  'starwars',
  'solo',
  'princess',
  'monkey',
  '654321',
  'superman',
  'qazwsx',
  'zxcvbnm',
  'passw0rd',
  'qwerty1',
  'charlie',
  'donald',
  'hello',
  'password!',
  'welcome1',
  'computer',
  'jennifer',
  'jessica',
]);

export type EmailValidationCode =
  | 'emailRequired'
  | 'emailInvalid'
  | 'emailNoSpaces'
  | 'emailTooLong';

export type PasswordValidationCode =
  | 'passwordRequired'
  | 'passwordMinLength'
  | 'passwordUppercase'
  | 'passwordLowercase'
  | 'passwordNumber'
  | 'passwordSpecial'
  | 'passwordLatinLayout'
  | 'passwordCommon'
  | 'passwordRepeated'
  | 'passwordNumericSequence';

export interface ValidationResult<TCode extends string> {
  isValid: boolean;
  codes: TCode[];
}

export interface PasswordRequirement {
  code: Exclude<PasswordValidationCode, 'passwordRequired'>;
  met: boolean;
}

export function normalizeEmailInput(value: string): string {
  return value.trim();
}

export function validateEmailInput(value: string, required = true): ValidationResult<EmailValidationCode> {
  const normalized = normalizeEmailInput(value);
  const codes: EmailValidationCode[] = [];

  if (!normalized) {
    if (required) {
      codes.push('emailRequired');
    }

    return { isValid: codes.length === 0, codes };
  }

  if (/\s/u.test(value)) {
    codes.push('emailNoSpaces');
  }

  const [localPart = ''] = normalized.split('@');
  if (normalized.length > EMAIL_MAX_LENGTH || localPart.length > EMAIL_LOCAL_PART_MAX_LENGTH) {
    codes.push('emailTooLong');
  }

  if (!EMAIL_PATTERN.test(normalized)) {
    codes.push('emailInvalid');
  }

  return { isValid: codes.length === 0, codes };
}

export function getPasswordRequirements(password: string): PasswordRequirement[] {
  return [
    { code: 'passwordMinLength', met: password.length >= PASSWORD_MIN_LENGTH },
    { code: 'passwordUppercase', met: /[A-Z]/u.test(password) },
    { code: 'passwordLowercase', met: /[a-z]/u.test(password) },
    { code: 'passwordNumber', met: /\d/u.test(password) },
    { code: 'passwordSpecial', met: PASSWORD_SPECIAL_PATTERN.test(password) },
    {
      code: 'passwordLatinLayout',
      met: password.length === 0 || (ASCII_PRINTABLE_PATTERN.test(password) && !CYRILLIC_PATTERN.test(password)),
    },
    { code: 'passwordCommon', met: password.length === 0 || !COMMON_PASSWORDS.has(password.toLowerCase()) },
    { code: 'passwordRepeated', met: password.length === 0 || !REPEATED_CHARACTER_PATTERN.test(password) },
    { code: 'passwordNumericSequence', met: password.length === 0 || !SIMPLE_NUMERIC_SEQUENCE_PATTERN.test(password) },
  ];
}

export function validatePasswordInput(password: string): ValidationResult<PasswordValidationCode> {
  const codes: PasswordValidationCode[] = [];

  if (!password) {
    codes.push('passwordRequired');
    return { isValid: false, codes };
  }

  for (const requirement of getPasswordRequirements(password)) {
    if (!requirement.met) {
      codes.push(requirement.code);
    }
  }

  return { isValid: codes.length === 0, codes };
}
