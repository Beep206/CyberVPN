/**
 * Analytics tracking helper
 * Provides a consistent interface for tracking events across the app.
 * Can be swapped out for different providers (GA4, Mixpanel, Posthog, etc.)
 */

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

type EventProperties = Record<string, string | number | boolean | undefined>;

interface AnalyticsProvider {
  track: (event: string, properties?: EventProperties) => void;
  identify: (userId: string, traits?: EventProperties) => void;
  reset: () => void;
}

// Default provider logs to console in development
const consoleProvider: AnalyticsProvider = {
  track: (event, properties) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics]', event, properties);
    }
  },
  identify: (userId, traits) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics] Identify:', userId, traits);
    }
  },
  reset: () => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics] Reset');
    }
  },
};

let provider: AnalyticsProvider = consoleProvider;

/**
 * Configure the analytics provider
 * Call this early in app initialization with your chosen provider
 */
export function configureAnalytics(customProvider: AnalyticsProvider): void {
  provider = customProvider;
}

/**
 * Track an auth-related event
 */
export function trackAuthEvent(event: AuthEventName, properties?: EventProperties): void {
  provider.track(event, {
    ...properties,
    timestamp: Date.now(),
  });
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
  
  loginSuccess: (userId: string, method: 'email' | 'telegram' | 'magic_link' | 'google' | 'github' | 'discord' | 'apple' | 'microsoft' | 'twitter' = 'email') => {
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
