import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";

import { ThemeProvider } from "./app/theme-provider";
import { Layout } from "./widgets/Layout";
import { DashboardPage } from "./pages/Dashboard";
import { ProfilesPage } from "./pages/Profiles";
import { SettingsPage } from "./pages/Settings";
import { HotspotPage } from "./pages/Hotspot";
import { SplitTunnelingPage } from "./pages/SplitTunneling";
import { PrivacyShieldPage } from "./pages/PrivacyShield";
import { SecurityPage } from "./pages/Security";
import { AnalyticsPage } from "./pages/Analytics";
import { AutomationPage } from "./pages/Automation";
import { StealthLabPage } from "./pages/StealthLab";
import { AccountPage } from "./pages/Account";
import { RemotePage } from "./pages/Remote";
import { RoutingPage } from "./pages/Routing";
import { SubscriptionsPage } from "./pages/Subscriptions";
import "./index.css";

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
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
