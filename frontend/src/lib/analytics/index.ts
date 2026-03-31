/**
 * Analytics tracking helper
 * Provides a consistent interface for tracking events across the app.
 * Can be swapped out for different providers (GA4, Mixpanel, Posthog, etc.)
 */
import { createGa4Provider } from '@/lib/analytics/providers/ga4';

type AuthEventName =
  | 'auth.login.started'
  | 'auth.login.success'
  | 'auth.login.error'
  | 'auth.register.started'
  | 'auth.register.success'
  | 'auth.register.error'
  | 'auth.logout'
  | 'auth.session.restored'
  | 'auth.session.expired'
  | 'auth.telegram.started'
  | 'auth.telegram.success'
  | 'auth.telegram.error'
  | 'auth.rate_limited';

type SeoEventName =
  | 'seo.landing_cta_click'
  | 'seo.download_cta_click'
  | 'seo.help_contact_click'
  | 'seo.ai_referral_session';

export type AnalyticsEventName = AuthEventName | SeoEventName;
export type EventProperties = Record<string, string | number | boolean | null | undefined>;

export interface AnalyticsProvider {
  track: (event: string, properties?: EventProperties) => void;
  identify: (userId: string, traits?: EventProperties) => void;
  reset: () => void;
}

// Default no-op provider (replaced at runtime via configureAnalytics)
const noopProvider: AnalyticsProvider = {
  track: () => {},
  identify: () => {},
  reset: () => {},
};

const gaMeasurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

let provider: AnalyticsProvider = gaMeasurementId ? createGa4Provider(gaMeasurementId) : noopProvider;

function withTimestamp(properties?: EventProperties): EventProperties {
  return {
    ...properties,
    timestamp: Date.now(),
  };
}

/**
 * Configure the analytics provider
 * Call this early in app initialization with your chosen provider
 */
export function configureAnalytics(customProvider: AnalyticsProvider): void {
  provider = customProvider;
}

/**
 * Track a generic analytics event
 */
export function trackEvent(event: AnalyticsEventName, properties?: EventProperties): void {
  provider.track(event, withTimestamp(properties));
}

/**
 * Track an auth-related event
 */
export function trackAuthEvent(event: AuthEventName, properties?: EventProperties): void {
  trackEvent(event, properties);
}

/**
 * Track a SEO / AI acquisition event
 */
export function trackSeoEvent(event: SeoEventName, properties?: EventProperties): void {
  trackEvent(event, properties);
}

/**
 * Identify a user after successful authentication
 */
export function identifyUser(userId: string, traits?: EventProperties): void {
  provider.identify(userId, traits);
}

/**
 * Reset analytics state (call on logout)
 */
export function resetAnalytics(): void {
  provider.reset();
}

// Convenience functions for common auth events
export const authAnalytics = {
  loginStarted: () => trackAuthEvent('auth.login.started'),

  loginSuccess: (userId: string, method: 'email' | 'telegram' | 'magic_link' | 'magic_link_otp' | 'google' | 'github' | 'discord' | 'facebook' | 'apple' | 'microsoft' | 'twitter' = 'email') => {
    trackAuthEvent('auth.login.success', { method });
    identifyUser(userId);
  },

  loginError: (errorType: string) => trackAuthEvent('auth.login.error', { errorType }),

  registerStarted: () => trackAuthEvent('auth.register.started'),

  registerSuccess: (userId: string) => {
    trackAuthEvent('auth.register.success');
    identifyUser(userId);
  },

  registerError: (errorType: string) => trackAuthEvent('auth.register.error', { errorType }),

  logout: () => {
    trackAuthEvent('auth.logout');
    resetAnalytics();
  },

  sessionRestored: (userId: string) => {
    trackAuthEvent('auth.session.restored');
    identifyUser(userId);
  },

  sessionExpired: () => trackAuthEvent('auth.session.expired'),

  telegramStarted: () => trackAuthEvent('auth.telegram.started'),

  telegramSuccess: (userId: string) => {
    trackAuthEvent('auth.telegram.success');
    identifyUser(userId);
  },

  telegramError: (errorType: string) => trackAuthEvent('auth.telegram.error', { errorType }),

  rateLimited: (retryAfterSeconds: number) => 
    trackAuthEvent('auth.rate_limited', { retryAfterSeconds }),
};

export const seoAnalytics = {
  aiReferralSession: (properties?: EventProperties) =>
    trackSeoEvent('seo.ai_referral_session', properties),
  downloadCtaClick: (properties?: EventProperties) =>
    trackSeoEvent('seo.download_cta_click', properties),
  helpContactClick: (properties?: EventProperties) =>
    trackSeoEvent('seo.help_contact_click', properties),
  landingCtaClick: (properties?: EventProperties) =>
    trackSeoEvent('seo.landing_cta_click', properties),
};
