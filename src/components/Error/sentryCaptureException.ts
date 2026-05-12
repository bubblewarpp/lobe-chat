export type ErrorType = Error & { digest?: string };

export const sentryCaptureException = async (error: Error & { digest?: string }) => {
  if (!process.env.NEXT_PUBLIC_SENTRY_DSN) return;

  const { captureException } = await import('@sentry/nextjs');
  return captureException(error);
};
