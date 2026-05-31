import { describe, expect, it } from "vitest";

import {
  localeCatalog,
  locales,
  tauriLocaleCatalog,
  tauriLocales,
} from "../config";

const bundledMessages = import.meta.glob("../locales/*.json", { eager: true });
const bundledMessageLocales = Object.keys(bundledMessages).map((filePath) =>
  filePath.replace("../locales/", "").replace(/\.json$/, ""),
);

describe("desktop React locale inventory", () => {
  it("matches the bundled React message resources", () => {
    expect([...locales].sort()).toEqual(bundledMessageLocales.sort());
    expect(localeCatalog.map((entry) => entry.code)).toEqual([...locales]);
  });

  it("keeps the full Tauri locale inventory separate from selectable React locales", () => {
    expect(tauriLocales.length).toBeGreaterThan(locales.length);
    expect(tauriLocaleCatalog.map((entry) => entry.code)).toEqual([...tauriLocales]);
    expect(tauriLocales).toContain("zh-CN");
    expect(localeCatalog.map((entry) => entry.code)).not.toContain("zh-CN");
  });
});
