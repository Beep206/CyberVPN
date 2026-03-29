import type { Metadata } from 'next';

export const SITE_URL = 'https://cybervpn.com';

export function withSiteMetadata(metadata: Metadata): Metadata {
  return {
    metadataBase: new URL(SITE_URL),
    ...metadata,
  };
}
