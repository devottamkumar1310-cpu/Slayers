'use client';

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[SLAYERS] Unhandled UI error:', error);
  }, [error]);

  return (
    <div className="mx-auto max-w-lg py-28 text-center">
      <p className="eyebrow text-rust">Interface error</p>
      <h1 className="mt-4 text-2xl font-semibold tracking-tight text-bone">
        This screen failed to render
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-muted">
        Your work is safe on the server. Reloading this view usually clears it.
      </p>
      <button type="button" onClick={reset} className="btn-primary mt-6">
        Reload view
      </button>
    </div>
  );
}
