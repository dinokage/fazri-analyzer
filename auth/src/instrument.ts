import "dotenv/config";
import * as Sentry from "@sentry/node";

if (process.env.SENTRY_ENABLED === "true" && process.env.SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.SENTRY_DSN,
    environment: process.env.SENTRY_ENVIRONMENT ?? "development",
    tracesSampleRate: (() => {
      const raw = parseFloat(process.env.SENTRY_TRACES_SAMPLE_RATE ?? "0.1");
      return Number.isFinite(raw) ? Math.min(1, Math.max(0, raw)) : 0.1;
    })(),
    sendDefaultPii: false,
  });
  console.log(`Sentry initialized for environment: ${process.env.SENTRY_ENVIRONMENT}`);
}
