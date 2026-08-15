'use client';

import type { ProcessingJob, ProjectSummary } from '@/types';
import { formatDuration, formatMinutes } from '@/lib/format';

interface Props {
  summary: ProjectSummary;
  job?: ProcessingJob | null;
  onExport: (format: 'csv' | 'json') => void;
}

/**
 * Every number here comes straight from GET /projects/{id}/summary.
 *
 * The one derived figure — the manual-research estimate — is labelled as an
 * assumption and its rule is printed, because the backend computes it as
 * `requirements × 5 minutes` rather than measuring anything.
 */
export default function BoardSummary({ summary, job, onExport }: Props) {
  const measured = [
    { k: 'Scenes', v: summary.total_scenes },
    { k: 'Visual requirements', v: summary.total_requirements },
    { k: 'Assets found', v: summary.total_assets },
    { k: 'Scored 80+', v: summary.high_confidence_matches, tone: 'text-sage' },
    { k: 'Need review', v: summary.needs_review, tone: 'text-rust' },
    { k: 'Sources used', v: summary.total_sources },
  ];

  const breakdown = Object.entries(summary.provider_breakdown ?? {}).sort((a, b) => b[1] - a[1]);
  const warnings = job?.warnings ?? [];

  return (
    <div className="border-b border-line pb-10">
      {/* Metric ledger */}
      <dl className="grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-3 lg:grid-cols-6">
        {measured.map((m) => (
          <div key={m.k} className="bg-panel p-4">
            <dt className="font-mono text-micro uppercase text-faint">{m.k}</dt>
            <dd className={`mt-2 font-mono text-2xl leading-none ${m.tone ?? 'text-bone'}`}>
              {m.v}
            </dd>
          </div>
        ))}
      </dl>

      <div className="mt-6 grid gap-6 lg:grid-cols-12">
        {/* Sources */}
        <div className="lg:col-span-5">
          <p className="eyebrow">Where the assets came from</p>
          {breakdown.length === 0 ? (
            <p className="mt-3 text-xs text-faint">No source returned results for this run.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {breakdown.map(([name, count]) => {
                const pct = summary.total_assets ? (count / summary.total_assets) * 100 : 0;
                return (
                  <li key={name}>
                    <div className="flex items-baseline justify-between font-mono text-micro uppercase">
                      <span className="text-muted">{name}</span>
                      <span className="text-bone">{count}</span>
                    </div>
                    <div className="mt-1 h-0.5 w-full bg-line">
                      <div className="h-full bg-ochre" style={{ width: `${pct}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Timing — measured vs assumption, clearly separated */}
        <div className="lg:col-span-4">
          <p className="eyebrow">Time</p>
          <div className="mt-3 space-y-3">
            <div>
              <p className="font-mono text-xl text-bone">
                {formatDuration(summary.actual_processing_seconds)}
              </p>
              <p className="mt-0.5 font-mono text-micro uppercase text-faint">
                Measured pipeline run time
              </p>
            </div>
            <div className="border-t border-lineSoft pt-3">
              <p className="font-mono text-xl text-muted">
                {formatMinutes(summary.manual_estimate_minutes)}
              </p>
              <p className="mt-0.5 text-[11px] leading-relaxed text-faint">
                <span className="font-mono text-micro uppercase">Estimate, not measured</span> —
                assumes 5 minutes of manual searching per requirement
                ({summary.total_requirements} × 5).
              </p>
            </div>
          </div>
        </div>

        {/* Export */}
        <div className="lg:col-span-3">
          <p className="eyebrow">Export package</p>
          <p className="mt-3 text-xs leading-relaxed text-muted">
            Every scene, requirement and discovered asset — including the ones that need
            review.
          </p>
          <div className="mt-4 flex gap-2">
            <button type="button" onClick={() => onExport('csv')} className="btn-primary flex-1">
              CSV
            </button>
            <button type="button" onClick={() => onExport('json')} className="btn-ghost flex-1">
              JSON
            </button>
          </div>
        </div>
      </div>

      {/* Partial-failure disclosure: results are shown, but not silently. */}
      {warnings.length > 0 && (
        <details className="mt-6 border border-rust/40">
          <summary className="cursor-pointer px-4 py-2.5 font-mono text-label uppercase text-rust">
            {warnings.length} source warning{warnings.length === 1 ? '' : 's'} during this run
          </summary>
          <div className="border-t border-rust/30 px-4 py-3">
            <p className="text-xs leading-relaxed text-muted">
              These sources failed or returned nothing. The results below are what the
              remaining sources found, so coverage may be thinner than a clean run.
            </p>
            <ul className="mt-2.5 space-y-1.5">
              {warnings.map((w, i) => (
                <li key={i} className="font-mono text-[11px] leading-relaxed text-faint">
                  {w}
                </li>
              ))}
            </ul>
          </div>
        </details>
      )}
    </div>
  );
}
