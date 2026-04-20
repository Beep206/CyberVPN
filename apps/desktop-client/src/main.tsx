import { StrictMode, Suspense, lazy, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter, Route, Routes } from "react-router-dom";
import { MotionConfig } from "framer-motion";

import { ThemeProvider } from "./app/theme-provider";
import "./shared/i18n/i18n";
import { ConnectionProvider } from "./shared/model/use-connection";
import { desktopMotionEase } from "./shared/lib/motion";
import { PageSkeleton } from "./widgets/PageSkeleton";
import { Layout } from "./widgets/Layout";
import "./index.css";

const DashboardPage = lazy(() =>
  import("./pages/Dashboard").then((module) => ({ default: module.DashboardPage })),
);
const ProfilesPage = lazy(() =>
  import("./pages/Profiles").then((module) => ({ default: module.ProfilesPage })),
);
const SettingsPage = lazy(() =>
  import("./pages/Settings").then((module) => ({ default: module.SettingsPage })),
);
const HotspotPage = lazy(() =>
  import("./pages/Hotspot").then((module) => ({ default: module.HotspotPage })),
);
const SplitTunnelingPage = lazy(() =>
  import("./pages/SplitTunneling").then((module) => ({ default: module.SplitTunnelingPage })),
);
const PrivacyShieldPage = lazy(() =>
  import("./pages/PrivacyShield").then((module) => ({ default: module.PrivacyShieldPage })),
);
const SecurityPage = lazy(() =>
  import("./pages/Security").then((module) => ({ default: module.SecurityPage })),
);
const AnalyticsPage = lazy(() =>
  import("./pages/Analytics").then((module) => ({ default: module.AnalyticsPage })),
);
const AutomationPage = lazy(() =>
  import("./pages/Automation").then((module) => ({ default: module.AutomationPage })),
);
const StealthLabPage = lazy(() =>
  import("./pages/StealthLab").then((module) => ({ default: module.StealthLabPage })),
);
const AccountPage = lazy(() =>
  import("./pages/Account").then((module) => ({ default: module.AccountPage })),
);
const RemotePage = lazy(() =>
  import("./pages/Remote").then((module) => ({ default: module.RemotePage })),
);
const OnboardingPage = lazy(() =>
  import("./pages/Onboarding").then((module) => ({ default: module.OnboardingPage })),
);
const RoutingPage = lazy(() =>
  import("./pages/Routing/index").then((module) => ({ default: module.RoutingPage })),
);
const SubscriptionsPage = lazy(() =>
  import("./pages/Subscriptions").then((module) => ({ default: module.SubscriptionsPage })),
);
const LogsPage = lazy(() =>
  import("./pages/Logs").then((module) => ({ default: module.LogsPage })),
);

const routePreloaders = [
  () => import("./pages/Dashboard"),
  () => import("./pages/Profiles"),
  () => import("./pages/Settings"),
  () => import("./pages/Hotspot"),
  () => import("./pages/SplitTunneling"),
  () => import("./pages/PrivacyShield"),
  () => import("./pages/Security"),
  () => import("./pages/Analytics"),
  () => import("./pages/Automation"),
  () => import("./pages/StealthLab"),
  () => import("./pages/Account"),
  () => import("./pages/Remote"),
  () => import("./pages/Routing/index"),
  () => import("./pages/Subscriptions"),
  () => import("./pages/Logs"),
];

function RouteWarmup() {
  useEffect(() => {
    let cancelled = false;
    let timeoutId: number | null = null;
    let idleId: number | null = null;

    const preloadRoutes = () => {
      if (cancelled) {
        return;
      }

      for (const preload of routePreloaders) {
        void preload();
      }
    };

    if (typeof window.requestIdleCallback === "function") {
      idleId = window.requestIdleCallback(preloadRoutes, { timeout: 1500 });
    } else {
      timeoutId = window.setTimeout(preloadRoutes, 350);
    }

    return () => {
      cancelled = true;
      if (idleId !== null && typeof window.cancelIdleCallback === "function") {
        window.cancelIdleCallback(idleId);
      }
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, []);

  return null;
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/onboarding"
        element={
          <Suspense fallback={<PageSkeleton fullscreen />}>
            <OnboardingPage />
          </Suspense>
        }
      />
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="remote" element={<RemotePage />} />
        <Route path="stealth-lab" element={<StealthLabPage />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="account" element={<AccountPage />} />
        <Route path="automation" element={<AutomationPage />} />
        <Route path="profiles" element={<ProfilesPage />} />
        <Route path="routing" element={<RoutingPage />} />
        <Route path="hotspot" element={<HotspotPage />} />
        <Route path="split-tunneling" element={<SplitTunnelingPage />} />
        <Route path="privacy-shield" element={<PrivacyShieldPage />} />
        <Route path="subscriptions" element={<SubscriptionsPage />} />
        <Route path="logs" element={<LogsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <ConnectionProvider>
        <MotionConfig
          reducedMotion="user"
          transition={{ duration: 0.16, ease: desktopMotionEase }}
        >
          <HashRouter>
            <RouteWarmup />
            <AppRoutes />
          </HashRouter>
        </MotionConfig>
      </ConnectionProvider>
    </ThemeProvider>
  </StrictMode>
);
