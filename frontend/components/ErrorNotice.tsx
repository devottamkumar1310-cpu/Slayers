'use client';

interface ErrorNoticeProps {
  message: string;
  /** Optional extra guidance, e.g. "Start the backend, then retry." */
  hint?: string;
  onRetry?: () => void;
  retryLabel?: string;
}

/**
 * The single place user-facing failures are rendered. Only the friendly
 * message from ApiError reaches here — raw server detail stays in the console.
 */
export default function ErrorNotice({
  message,
  hint,
  onRetry,
  retryLabel = 'Retry',
}: ErrorNoticeProps) {
  return (
    <div role="alert" className="border border-rust/50 bg-rust/[0.06] p-4">
      <p className="font-mono text-label uppercase text-rust">Something went wrong</p>
      <p className="mt-2 text-sm leading-relaxed text-bone">{message}</p>
      {hint && <p className="mt-1.5 text-xs leading-relaxed text-muted">{hint}</p>}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 border border-rust/50 px-3 py-1.5 font-mono text-label uppercase text-rust transition-colors hover:bg-rust hover:text-ink"
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}
