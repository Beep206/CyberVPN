import { expect } from 'vitest';
import { type AxiosError } from 'axios';

function isAxiosError(error: unknown): error is AxiosError<{ detail: string }> {
  return (
    typeof error === 'object'
    && error !== null
    && 'isAxiosError' in error
    && (error as Record<string, unknown>).isAxiosError === true
  );
}

export async function expectAxiosErrorStatus(
  request: Promise<unknown>,
  status: number,
): Promise<void> {
  try {
    await request;
    expect.fail(`Expected AxiosError with status ${status}`);
  } catch (error: unknown) {
    expect(isAxiosError(error)).toBe(true);
    if (isAxiosError(error)) {
      expect(error.response?.status).toBe(status);
    }
  }
}
