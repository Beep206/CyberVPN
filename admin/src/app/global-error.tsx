"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { reportFrontendRenderError } from '@/shared/lib/frontend-observability';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
    reportFrontendRenderError('admin_portal', {
      errorCode: error.name || error.digest || 'global_error',
      path: typeof window !== 'undefined' ? window.location.pathname : undefined,
    });
  }, [error]);

  return (
    <html>
      <body>
        <div style={{ padding: "2rem", fontFamily: "monospace", background: "#0a0a0a", color: "#00ffff", minHeight: "100vh" }}>
          <h2>Something went wrong</h2>
          <button onClick={() => reset()} style={{ marginTop: "1rem", padding: "0.5rem 1rem", background: "#ff00ff", color: "#000", border: "none", cursor: "pointer" }}>
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
