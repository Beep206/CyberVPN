import { describe, expect, it } from "vitest";

import { locales, tauriLocaleCatalog } from "../../shared/i18n/config";
import { languageSelectorLocales } from "../LanguageSelector";

const reactLocaleCodes = new Set<string>(locales);

describe("LanguageSelector", () => {
  it("only advertises locales backed by bundled React resources", () => {
    expect(languageSelectorLocales.map((entry) => entry.code)).toEqual([...locales]);

    for (const entry of tauriLocaleCatalog) {
      if (!reactLocaleCodes.has(entry.code)) {
        expect(languageSelectorLocales.map((locale) => locale.code)).not.toContain(entry.code);
      }
    }
  });
});
