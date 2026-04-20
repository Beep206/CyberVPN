import { headers } from 'next/headers';
import {
  resolvePartnerSurfaceContext,
  type PartnerSurfaceContext,
} from './runtime';

export async function getPartnerSurfaceContext(): Promise<PartnerSurfaceContext> {
  const requestHeaders = await headers();
  const forwardedHost = requestHeaders.get('x-forwarded-host');
  const host = forwardedHost ?? requestHeaders.get('host');

  return resolvePartnerSurfaceContext(host);
}
