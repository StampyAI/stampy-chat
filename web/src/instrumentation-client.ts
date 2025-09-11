// This file configures the initialization of Sentry on the client.
// The added config here will be used whenever a users loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  release: process.env.NEXT_PUBLIC_RELEASE,
  environment:
    process.env.NEXT_PUBLIC_ENV === "production" ? "production" : "development",
  includeLocalVariables: true,

  // Add optional integrations for additional features
  integrations: [
    Sentry.replayIntegration(),
    Sentry.captureConsoleIntegration(),
    Sentry.httpClientIntegration(),
  ],

  // Define how likely traces are sampled. Adjust this value in production, or use tracesSampler for greater control.
  tracesSampleRate: process.env.NEXT_PUBLIC_ENV === "production" ? 0.1 : 1.0,
  profilesSampleRate: 1,
  // Enable logs to be sent to Sentry
  enableLogs: true,

  replaysSessionSampleRate:
    process.env.NEXT_PUBLIC_ENV === "production" ? 0.01 : 0.0,

  // Define how likely Replay events are sampled when an error occurs.
  replaysOnErrorSampleRate: process.env.NEXT_PUBLIC_ENV === "production" ? 0.1 : 0.0,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
