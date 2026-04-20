'use client';

import { RouteErrorBoundary } from '@/shared/ui/route-error-boundary';

export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <RouteErrorBoundary error={error} reset={reset} />;
}
