import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Only enable Sentry when explicitly configured
  enabled: process.env.NEXT_PUBLIC_SENTRY_ENABLED === 'true',

  // Environment (development, staging, production)
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || 'development',

  // Performance Monitoring: 10% in production, 100% in development
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  integrations: [
    Sentry.httpIntegration(),
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

    // Remove query parameters that might contain tokens
    if (event.request?.query_string) {
      const queryParams = new URLSearchParams(event.request.query_string);
      if (queryParams.has('token')) queryParams.delete('token');
      if (queryParams.has('access_token')) queryParams.delete('access_token');
      if (queryParams.has('refresh_token')) queryParams.delete('refresh_token');
      event.request.query_string = queryParams.toString();
    }

    // Filter JWT tokens from exception messages
    if (event.exception?.values) {
      event.exception.values = event.exception.values.map(exception => {
        if (exception.value) {
          // Replace JWT tokens with [Filtered]
          exception.value = exception.value.replace(
            /Bearer [A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*/g,
            'Bearer [Filtered]'
          );
        }
        return exception;
      });
    }

    return event;
  },

  // Ignore certain errors
  ignoreErrors: [
    'ECONNREFUSED',
    'ENOTFOUND',
    'ETIMEDOUT',
  ],
});
