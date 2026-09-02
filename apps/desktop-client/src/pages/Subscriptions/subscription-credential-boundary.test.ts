import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("subscription credential UI boundary", () => {
  it("keeps the bearer URL out of React state, logs, and controlled props", () => {
    const source = readFileSync(
      resolve(process.cwd(), "src/pages/Subscriptions/index.tsx"),
      "utf8",
    );

    expect(source).toContain("const urlInputRef = useRef<HTMLInputElement>(null)");
    expect(source).toContain("ref={urlInputRef}");
    expect(source).toContain('credentialInput.value = ""');
    expect(source).not.toMatch(/useState(?:<[^>]+>)?\([^)]*url/i);
    expect(source).not.toMatch(
      /const\s*\[\s*[^,\]]*(?:url|credential)[^,\]]*,[^\]]*\]\s*=\s*useState/is,
    );
    expect(source).not.toContain("value={url}");
    expect(source).not.toContain("setUrl(");
    expect(source).not.toContain("Failed to create subscription");
  });
});
