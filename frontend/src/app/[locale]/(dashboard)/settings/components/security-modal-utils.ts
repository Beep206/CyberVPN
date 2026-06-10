import { AxiosError } from 'axios';

type ApiErrorResponse = {
  detail?: unknown;
};

export function getApiErrorDetail(error: unknown): string | null {
  if (!(error instanceof AxiosError)) {
    return null;
  }

  const detail = (error.response?.data as ApiErrorResponse | undefined)?.detail;

  return typeof detail === 'string' && detail.trim() ? detail : null;
}

export function getApiErrorStatus(error: unknown): number | undefined {
  return error instanceof AxiosError ? error.response?.status : undefined;
}
