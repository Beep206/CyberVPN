export const MOBILE_BREAKPOINTS = {
  compactPhoneMax: 389,
  mobileMax: 767,
  tabletMax: 1023,
} as const;

export const MOBILE_TOUCH_TARGETS = {
  minimumPx: 44,
  comfortablePx: 48,
  thumbReachInsetPx: 16,
} as const;

export const MOBILE_SAFE_AREA_VARS = {
  top: '--safe-area-top',
  right: '--safe-area-right',
  bottom: '--safe-area-bottom',
  left: '--safe-area-left',
  keyboardOffset: '--keyboard-offset',
} as const;

export const MOBILE_ROUTE_PERFORMANCE_BUDGETS = {
  dashboard: {
    lcpMs: 2500,
    inpMs: 200,
    cls: 0.1,
    jsKb: 240,
    longTaskMs: 200,
  },
  marketing: {
    lcpMs: 2500,
    inpMs: 200,
    cls: 0.1,
    jsKb: 200,
    longTaskMs: 200,
  },
  miniapp: {
    lcpMs: 2200,
    inpMs: 200,
    cls: 0.1,
    jsKb: 180,
    longTaskMs: 150,
  },
  auth: {
    lcpMs: 2200,
    inpMs: 200,
    cls: 0.1,
    jsKb: 160,
    longTaskMs: 150,
  },
} as const;

export type MobileRouteGroup = keyof typeof MOBILE_ROUTE_PERFORMANCE_BUDGETS;

export const MOBILE_ACCEPTANCE_CRITERIA = {
  scrollOwner: 'document',
  safeAreaSupport: true,
  reducedMotionSupport: true,
  touchFirstInteractions: true,
  keyboardSafeForms: true,
} as const;
