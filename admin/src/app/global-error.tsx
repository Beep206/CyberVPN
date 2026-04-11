"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
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
