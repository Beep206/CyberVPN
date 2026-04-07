import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";

import { ThemeProvider } from "./app/theme-provider";
import "./shared/i18n/i18n";
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
  import("./pages/Routing").then((module) => ({ default: module.RoutingPage })),
);
const SubscriptionsPage = lazy(() =>
  import("./pages/Subscriptions").then((module) => ({ default: module.SubscriptionsPage })),
);

function RouteLoadingFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#05070b] px-6 text-center">
      <div className="rounded-xl border border-border/40 bg-black/40 px-5 py-4 text-sm text-muted-foreground">
        Loading CyberVPN workspace...
      </div>
    </div>
  );
}

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <Suspense fallback={<RouteLoadingFallback />}>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/onboarding" element={<OnboardingPage />} />
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
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </AnimatePresence>
    </Suspense>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <BrowserRouter>
        <AnimatedRoutes />
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>
);
