import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Only enable Sentry when explicitly configured
  enabled: process.env.NEXT_PUBLIC_SENTRY_ENABLED === 'true',

  // Environment (development, staging, production)
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || 'development',

  // Performance Monitoring: 10% in production, 100% in development
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  // Session Replay: 10% of normal sessions, 100% of error sessions
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  integrations: [
    Sentry.browserTracingIntegration({
      // Track navigation performance
      traceFetch: true,
      traceXHR: true,
    }),
    Sentry.replayIntegration({
      // Privacy settings for session replay
      maskAllText: false,
      blockAllMedia: false,

      // Don't capture sensitive form inputs
      maskAllInputs: true,
    }),
  ],

  // Only trace requests to our own domains
  tracePropagationTargets: [
    "localhost",
    /^https:\/\/.*\.rayzrsole\.com/,
    /^https:\/\/.*\.rdpdc\.in/,
  ],

  // Filter sensitive data before sending to Sentry
  beforeSend(event, hint) {
    // Remove Authorization headers
    if (event.request?.headers) {
      delete event.request.headers['Authorization'];
      delete event.request.headers['authorization'];
      delete event.request.headers['Cookie'];
      delete event.request.headers['cookie'];
    }

    // Filter sensitive data from breadcrumbs
    if (event.breadcrumbs) {
      event.breadcrumbs = event.breadcrumbs.map(breadcrumb => {
        if (breadcrumb.data) {
          // Remove password fields
          if (breadcrumb.data.password) delete breadcrumb.data.password;
          if (breadcrumb.data.token) delete breadcrumb.data.token;
          if (breadcrumb.data.accessToken) delete breadcrumb.data.accessToken;
          if (breadcrumb.data.refreshToken) delete breadcrumb.data.refreshToken;

          // Remove authorization from fetch data
          if (breadcrumb.data.headers) {
            delete breadcrumb.data.headers.Authorization;
            delete breadcrumb.data.headers.authorization;
          }
        }
        return breadcrumb;
      });
    }

    return event;
  },

  // Ignore certain errors
  ignoreErrors: [
    // Browser extensions
    'top.GLOBALS',
    'ResizeObserver loop limit exceeded',
    'ResizeObserver loop completed with undelivered notifications',
    // Network errors that are expected
    'NetworkError',
    'Failed to fetch',
    'Load failed',
  ],
});
