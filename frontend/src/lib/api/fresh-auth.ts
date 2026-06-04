export const FRESH_AUTH_GRANT_ID_HEADER = 'X-Fresh-Auth-Grant-Id' as const;

export interface FreshAuthRequestOptions {
  freshAuthGrantId?: string;
}

interface FreshAuthRequestConfig {
  headers: {
    [FRESH_AUTH_GRANT_ID_HEADER]: string;
  };
}

export function buildFreshAuthRequestConfig(
  options?: FreshAuthRequestOptions,
): FreshAuthRequestConfig | undefined {
  if (!options?.freshAuthGrantId) {
    return undefined;
  }

  return {
    headers: {
      [FRESH_AUTH_GRANT_ID_HEADER]: options.freshAuthGrantId,
    },
  };
}
