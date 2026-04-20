import { render } from "@testing-library/react";
import * as React from "react";
import { describe, expect, it, vi } from "vitest";

import { ThemeProvider } from "@/app/theme-provider";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

vi.mock("@/components/ui/button", () => ({
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props}>
      {children}
    </button>
  ),
}));

vi.mock("@base-ui/react/dialog", () => {
  const renderSlot = (tag: keyof React.JSX.IntrinsicElements = "div") =>
    React.forwardRef<HTMLElement, Record<string, unknown>>(({ children, render, ...props }, ref) => {
      if (React.isValidElement(render)) {
        return React.cloneElement(
          render as React.ReactElement<Record<string, unknown>>,
          {
            ...props,
            ref,
          },
          children,
        );
      }

      return React.createElement(tag, { ...props, ref }, children);
    });

  return {
    Dialog: {
      Root: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
      Trigger: renderSlot("button"),
      Portal: ({ children }: { children: React.ReactNode }) => <>{children}</>,
      Backdrop: renderSlot("div"),
      Popup: renderSlot("div"),
      Close: renderSlot("button"),
      Title: renderSlot("h2"),
      Description: renderSlot("p"),
    },
  };
});

describe("theme surfaces", () => {
  it("applies the requested root theme and color scheme", () => {
    render(
      <ThemeProvider defaultTheme="light" storageKey="test-theme-light">
        <div>theme probe</div>
      </ThemeProvider>,
    );

    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.style.colorScheme).toBe("light");
  });

  it("keeps dialog surfaces on semantic tokens instead of hardcoded black and white shells", () => {
    render(
      <ThemeProvider defaultTheme="dark" storageKey="test-theme-dialog">
        <Dialog open>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Semantic Surface</DialogTitle>
            </DialogHeader>
            <DialogFooter>footer</DialogFooter>
          </DialogContent>
        </Dialog>
      </ThemeProvider>,
    );

    const overlay = document.querySelector('[data-slot="dialog-overlay"]');
    const content = document.querySelector('[data-slot="dialog-content"]');
    const footer = document.querySelector('[data-slot="dialog-footer"]');

    expect(overlay).not.toBeNull();
    expect(content).not.toBeNull();
    expect(footer).not.toBeNull();

    expect(overlay?.className).toContain("var(--overlay-backdrop)");
    expect(content?.className).toContain("var(--chrome-elevated)");
    expect(footer?.className).toContain("var(--panel-subtle)");
    expect(content?.className).not.toContain("bg-black");
    expect(content?.className).not.toContain("bg-white");
  });
});
