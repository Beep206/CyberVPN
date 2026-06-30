import { AxiosError, type AxiosResponse } from 'axios';
import { describe, expect, it } from 'vitest';

import { RateLimitError } from '@/lib/api/client';
import { getErrorMessage } from './formatting';

function axiosErrorWithData(data: unknown): AxiosError {
  return new AxiosError(
    'Request failed',
    undefined,
    undefined,
    undefined,
    {
      data,
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: {},
      config: { headers: {} },
    } as AxiosResponse,
  );
}

describe('growth getErrorMessage', () => {
  it('returns string detail directly', () => {
    const error = axiosErrorWithData({ detail: 'Campaign key already exists' });

    expect(getErrorMessage(error, 'Fallback')).toBe('Campaign key already exists');
  });

  it('formats FastAPI loc/msg validation details', () => {
    const error = axiosErrorWithData({
      detail: [{ loc: ['body', 'global_issue_cap'], msg: 'Field required', type: 'missing' }],
    });

    expect(getErrorMessage(error, 'Fallback')).toBe('body.global_issue_cap: Field required');
  });

  it('joins arrays of string and object details', () => {
    const error = axiosErrorWithData({
      detail: [
        'Campaign key already exists',
        { loc: ['body', 'root_usage_mode'], msg: 'Input should be valid', type: 'value_error' },
      ],
    });

    expect(getErrorMessage(error, 'Fallback')).toBe(
      'Campaign key already exists; body.root_usage_mode: Input should be valid',
    );
  });

  it('uses nested detail, message, error, code and type values safely', () => {
    expect(getErrorMessage(axiosErrorWithData({ detail: { message: 'Nested message' } }), 'Fallback')).toBe(
      'Nested message',
    );
    expect(getErrorMessage(axiosErrorWithData({ error: { code: 'INVITE_CAMPAIGN_VALIDATION' } }), 'Fallback')).toBe(
      'INVITE_CAMPAIGN_VALIDATION',
    );
    expect(getErrorMessage(axiosErrorWithData({ detail: { loc: 'body.field', type: 'value_error' } }), 'Fallback')).toBe(
      'body.field: value_error',
    );
  });

  it('falls back for unknown errors', () => {
    expect(getErrorMessage({ unexpected: true }, 'Fallback')).toBe('Fallback');
  });

  it('keeps RateLimitError message', () => {
    expect(getErrorMessage(new RateLimitError(60), 'Fallback')).toBe('Rate limited. Try again in 1 minutes');
  });
});
