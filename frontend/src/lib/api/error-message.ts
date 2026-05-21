type ApiErrorDetail = {
  code?: unknown;
  message?: unknown;
  detail?: unknown;
};

function detailToMessage(detail: unknown): string | null {
  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => detailToMessage(item))
      .filter((item): item is string => Boolean(item));
    return messages.length > 0 ? messages.join(', ') : null;
  }

  if (detail && typeof detail === 'object') {
    const structured = detail as ApiErrorDetail;
    if (typeof structured.message === 'string') {
      return structured.message;
    }
    if (typeof structured.detail === 'string') {
      return structured.detail;
    }
    return JSON.stringify(detail);
  }

  return null;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  const axiosLikeError = error as {
    response?: {
      data?: {
        detail?: unknown;
        message?: unknown;
        error?: unknown;
      };
    };
    message?: unknown;
  };
  const responseData = axiosLikeError.response?.data;

  return (
    detailToMessage(responseData?.detail)
    ?? detailToMessage(responseData?.message)
    ?? detailToMessage(responseData?.error)
    ?? detailToMessage(axiosLikeError.message)
    ?? fallback
  );
}
