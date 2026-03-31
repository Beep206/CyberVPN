interface PendingTwoFactorStageInput {
  token: string;
  locale: string;
  returnTo?: string | null;
  isNewUser?: boolean;
}

interface CompletePendingTwoFactorResponse {
  redirect_to: string;
}

async function readErrorDetail(response: Response, fallbackMessage: string): Promise<string> {
  try {
    const payload = await response.json() as { detail?: string };
    return payload.detail || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

export async function stagePendingTwoFactorSession(input: PendingTwoFactorStageInput): Promise<void> {
  const response = await fetch('/api/auth/2fa/pending', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      token: input.token,
      locale: input.locale,
      return_to: input.returnTo ?? null,
      is_new_user: input.isNewUser ?? false,
    }),
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to start two-factor verification.'));
  }
}

export async function completePendingTwoFactorSession(code: string): Promise<CompletePendingTwoFactorResponse> {
  const response = await fetch('/api/auth/2fa/complete', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
    },
    body: JSON.stringify({ code }),
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Two-factor verification failed.'));
  }

  return await response.json() as CompletePendingTwoFactorResponse;
}
