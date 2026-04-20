import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect, useState } from "react";
import { MemoryRouter, Outlet, Route, Routes, Link, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { RouteTransition } from "../RouteTransition";

let shellMountCount = 0;

function ShellHarness() {
  const location = useLocation();
  const [mounts, setMounts] = useState(0);

  useEffect(() => {
    shellMountCount += 1;
    setMounts(shellMountCount);
  }, []);

  return (
    <div>
      <div data-testid="shell-mount-count">{mounts}</div>
      <nav>
        <Link to="/">dashboard</Link>
        <Link to="/settings">settings</Link>
      </nav>
      <RouteTransition routeKey={location.pathname}>
        <Outlet />
      </RouteTransition>
    </div>
  );
}

describe("RouteTransition", () => {
  it("keeps the shell mounted while route content changes", async () => {
    shellMountCount = 0;

    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<ShellHarness />}>
            <Route index element={<div>Dashboard Page</div>} />
            <Route path="settings" element={<div>Settings Page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("shell-mount-count")).toHaveTextContent("1");
    });

    fireEvent.click(screen.getByRole("link", { name: "settings" }));

    expect(await screen.findByText("Settings Page")).toBeInTheDocument();
    expect(screen.getByTestId("shell-mount-count")).toHaveTextContent("1");
  });
});
