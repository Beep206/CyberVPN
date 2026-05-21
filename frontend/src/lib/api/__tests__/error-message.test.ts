import { describe, expect, it } from 'vitest';

import { getApiErrorMessage } from '../error-message';

describe('getApiErrorMessage', () => {
  it('returns structured API detail message instead of an object', () => {
    expect(
      getApiErrorMessage(
        {
          response: {
            data: {
              detail: {
                code: 'INVALID_TOKEN',
                message: 'Invalid token',
              },
            },
          },
        },
        'Fallback',
      ),
    ).toBe('Invalid token');
  });

  it('falls back to JSON for unknown object details', () => {
    expect(
      getApiErrorMessage(
        {
          response: {
            data: {
              detail: {
                code: 'UNKNOWN',
              },
            },
          },
        },
        'Fallback',
      ),
    ).toBe('{"code":"UNKNOWN"}');
  });
});
