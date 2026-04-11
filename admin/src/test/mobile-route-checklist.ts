import type { MobileViewportId } from '@/test/mobile-viewport';

export type MobileRouteChecklistId =
  | 'dashboard-shell'
  | 'features'
  | 'pricing'
  | 'privacy'
  | 'download'
  | 'contact'
  | 'docs'
  | 'api';

interface MobileRouteChecklistEntry {
  id: MobileRouteChecklistId;
  route: string;
  routeGroup: 'dashboard' | 'marketing' | 'content-heavy' | 'auth' | 'miniapp';
  sourcePaths: string[];
  mustContain: string[];
  mustNotContain?: string[];
  viewports: MobileViewportId[];
}

export const MOBILE_ROUTE_CHECKLIST: MobileRouteChecklistEntry[] = [
  {
    id: 'dashboard-shell',
    route: '/[locale]/dashboard',
    routeGroup: 'dashboard',
    sourcePaths: ['app/[locale]/(dashboard)/layout.tsx'],
    mustContain: [
      'min-h-dvh',
      '<TerminalHeader performanceMode="always" showMobileSidebar />',
      'md:pl-64',
    ],
    mustNotContain: ['h-screen', 'overflow-hidden'],
    viewports: ['iphoneSafari', 'androidChrome', 'tabletLandscape', 'telegramWebView'],
  },
  {
    id: 'features',
    route: '/[locale]/features',
    routeGroup: 'marketing',
    sourcePaths: ['widgets/features/features-dashboard.tsx'],
    mustContain: [
      'ResponsiveSplitShell',
      'useVisualTier',
      "visualTier === 'full'",
      'data-visual-tier={visualTier}',
    ],
    mustNotContain: ['h-screen', 'overflow-y-auto'],
    viewports: ['iphoneSafari', 'smallAndroid', 'tabletPortrait'],
  },
  {
    id: 'pricing',
    route: '/[locale]/pricing',
    routeGroup: 'marketing',
    sourcePaths: ['widgets/pricing/pricing-dashboard.tsx'],
    mustContain: [
      'ResponsiveSplitShell',
      'useVisualTier',
      'FeatureMatrix',
      'data-visual-tier={visualTier}',
    ],
    mustNotContain: ['h-screen'],
    viewports: ['iphoneSafari', 'smallAndroid', 'tabletPortrait'],
  },
  {
    id: 'privacy',
    route: '/[locale]/privacy',
    routeGroup: 'content-heavy',
    sourcePaths: ['widgets/privacy/privacy-dashboard.tsx'],
    mustContain: [
      'ResponsiveSplitShell',
      "window.addEventListener('scroll', updateScrollDepth",
      'lg:sticky lg:top-24',
    ],
    mustNotContain: ['overflow-y-auto'],
    viewports: ['iphoneSafari', 'androidChrome', 'tabletPortrait'],
  },
  {
    id: 'download',
    route: '/[locale]/download',
    routeGroup: 'marketing',
    sourcePaths: ['widgets/download/download-dashboard.tsx'],
    mustContain: [
      'ResponsiveSplitShell',
      'useVisualTier',
      "visualTier === 'full'",
      'data-visual-tier={visualTier}',
    ],
    mustNotContain: ['h-screen'],
    viewports: ['iphoneSafari', 'largeIphone', 'smallAndroid'],
  },
  {
    id: 'contact',
    route: '/[locale]/contact',
    routeGroup: 'marketing',
    sourcePaths: ['widgets/contact-form.tsx'],
    mustContain: [
      'useVisualTier',
      'mobile-form-input',
      'keyboard-safe-bottom',
      'touch-target-comfortable',
    ],
    mustNotContain: ['min-h-screen'],
    viewports: ['iphoneSafari', 'androidChrome', 'telegramWebView'],
  },
  {
    id: 'docs',
    route: '/[locale]/docs',
    routeGroup: 'content-heavy',
    sourcePaths: ['widgets/docs-container.tsx', 'widgets/docs-sidebar.tsx'],
    mustContain: [
      'order-1 lg:order-2',
      'scrollIntoView',
      'lg:sticky lg:top-24',
    ],
    mustNotContain: ['window.scrollTo'],
    viewports: ['iphoneSafari', 'androidChrome', 'tabletLandscape'],
  },
  {
    id: 'api',
    route: '/[locale]/api',
    routeGroup: 'content-heavy',
    sourcePaths: ['widgets/api/api-dashboard.tsx'],
    mustContain: [
      'ResponsiveSplitShell',
      'grid-cols-1',
      'xl:sticky xl:top-24',
    ],
    mustNotContain: ['overflow-y-auto'],
    viewports: ['iphoneSafari', 'androidChrome', 'tabletLandscape'],
  },
];

export function getMobileRouteChecklistEntry(id: MobileRouteChecklistId) {
  return MOBILE_ROUTE_CHECKLIST.find((entry) => entry.id === id);
}
