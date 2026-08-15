'use client';

import { useEffect, useRef, useState } from 'react';
import type { ProcessingJob } from '@/types';
import { api, ApiError } from '@/lib/api';
import ErrorNotice from '@/components/ErrorNotice';

/**
 * Stage boundaries are the pipeline's OWN progress values (see
 * backend/app/workers/pipeline_worker.py). Nothing is simulated: the bar
 * follows job.progress and the caption prints job.current_step verbatim.
 */
const STAGES = [
  { name: 'Analyse script', from: 5, to: 25 },
  { name: 'Build scenes', from: 25, to: 40 },
  { name: 'Read visual intent', from: 40, to: 60 },
  { name: 'Search sources', from: 60, to: 88 },
  { name: 'Rank & package', from: 88, to: 100 },
];

const POLL_MS = 1_200;
/** No progress movement for this long → surface a "still working" note. */
const STALL_MS = 45_000;
/** Consecutive failed polls before we stop and show an error. */
const MAX_POLL_FAILURES = 5;

interface Props {
  projectId: string;
  onCompleted: () => void;
}

export default function ProcessingView({ projectId, onCompleted }: Props) {
  const [job, setJob] = useState<ProcessingJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stalled, setStalled] = useState(false);
  const [retrying, setRetrying] = useState(false);

  // Held in a ref so a new parent-render identity never restarts the interval.
  const onCompletedRef = useRef(onCompleted);
  onCompletedRef.current = onCompleted;

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;
    let failures = 0;
    let lastProgress = -1;
    let lastMovedAt = Date.now();

    const stop = () => {
      if (timer) clearInterval(timer);
      timer = null;
    };

    const poll = async () => {
      if (cancelled) return;
      try {
        const status = await api.getProjectStatus(projectId);
        if (cancelled) return;
        failures = 0;
        setJob(status);

        if (status.progress !== lastProgress) {
          lastProgress = status.progress;
          lastMovedAt = Date.now();
          setStalled(false);
        } else if (Date.now() - lastMovedAt > STALL_MS) {
          setStalled(true);
        }

        if (status.status === 'completed') {
          stop();
          cancelled = true;
          onCompletedRef.current();
        } else if (status.status === 'failed') {
          stop();
          cancelled = true;
          setError(status.error || 'The pipeline stopped before it finished.');
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.isNotFound) {
          stop();
          cancelled = true;
          setError('This project no longer exists. It may have been deleted.');
          return;
        }
        failures += 1;
        if (failures >= MAX_POLL_FAILURES) {
          stop();
          cancelled = true;
          setError(
            err instanceof ApiError
              ? err.message
              : 'Lost contact with the engine while the run was in progress.'
          );
        }
      }
    };

    void poll();
    timer = setInterval(poll, POLL_MS);

    return () => {
      cancelled = true;
      stop();
    };
  }, [projectId]);

  const retry = async () => {
    setRetrying(true);
    try {
      await api.startProcessing(projectId);
      window.location.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not restart the run.');
      setRetrying(false);
    }
  };

  const progress = job?.progress ?? 0;
  const queued = !job || job.status === 'pending';
  const warnings = job?.warnings ?? [];

  return (
    <div className="mx-auto max-w-3xl py-12">
      <div className="flex items-baseline justify-between border-b border-line pb-4">
        <p className="eyebrow">{error ? 'Run stopped' : queued ? 'Queued' : 'Running'}</p>
        <p className="font-mono text-sm text-bone" aria-live="polite">
          {progress}%
        </p>
      </div>

      {/* Progress bar — width is job.progress, nothing else. */}
      <div
        className="mt-4 h-1 w-full bg-line"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Pipeline progress"
      >
        <div
          className={`h-full transition-[width] duration-500 ease-out ${
            error ? 'bg-rust' : 'bg-ochre'
          }`}
          style={{ width: `${Math.max(progress, 2)}%` }}
        />
      </div>

      <p className="mt-4 font-mono text-sm text-bone" aria-live="polite">
        {error ? 'Stopped' : (job?.current_step ?? 'Waiting for the engine to pick this up')}
      </p>

      {/* Stage ledger */}
      <ol className="mt-8 divide-y divide-lineSoft border-y border-line">
        {STAGES.map((stage) => {
          const done = progress >= stage.to;
          const active = !error && !done && progress >= stage.from;
          return (
            <li
              key={stage.name}
              className="flex items-center justify-between py-3.5"
              aria-current={active ? 'step' : undefined}
            >
              <div className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                    done ? 'bg-sage' : active ? 'animate-pulse bg-ochre' : 'bg-line'
                  }`}
                />
                <span
                  className={`font-mono text-label uppercase ${
                    done ? 'text-bone' : active ? 'text-ochre' : 'text-faint'
                  }`}
                >
                  {stage.name}
                </span>
              </div>
              <span className="font-mono text-micro uppercase text-faint">
                {done ? 'Done' : active ? 'Working' : 'Waiting'}
              </span>
            </li>
          );
        })}
      </ol>

      {/* Live provider tallies, straight from job.provider_stats */}
      {job?.provider_stats && Object.keys(job.provider_stats).length > 0 && (
        <div className="mt-6">
          <p className="eyebrow">Results per source</p>
          <ul className="mt-2.5 flex flex-wrap gap-2">
            {Object.entries(job.provider_stats).map(([name, count]) => (
              <li
                key={name}
                className="border border-line px-2.5 py-1 font-mono text-micro uppercase text-muted"
              >
                {name} <span className="text-bone">{count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {stalled && !error && (
        <p className="mt-6 border-l-2 border-ochre pl-3 text-xs leading-relaxed text-muted">
          Still working. Provider searches can be slow when a source is rate-limiting;
          the run continues in the background even if you navigate away.
        </p>
      )}

      {warnings.length > 0 && !error && (
        <details className="mt-6 border border-line">
          <summary className="cursor-pointer px-4 py-2.5 font-mono text-label uppercase text-rust">
            {warnings.length} source warning{warnings.length === 1 ? '' : 's'}
          </summary>
          <ul className="space-y-1.5 border-t border-line px-4 py-3">
            {warnings.map((w, i) => (
              <li key={i} className="font-mono text-[11px] leading-relaxed text-muted">
                {w}
              </li>
            ))}
          </ul>
        </details>
      )}

      {error && (
        <div className="mt-6">
          <ErrorNotice
            message={error}
            hint="Nothing was lost — restarting re-runs the pipeline on the same script."
            onRetry={retry}
            retryLabel={retrying ? 'Restarting…' : 'Restart run'}
          />
        </div>
      )}
    </div>
  );
}
