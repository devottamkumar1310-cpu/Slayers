'use client';

import type { AssetRequirement, ContentSegment } from '@/types';
import AssetCard from '@/components/AssetCard';
import { humanizeIntent } from '@/lib/format';

/**
 * One scene = one row of the board.
 *
 * The left column is the script (what is being said, and when). The right
 * column is what SLAYERS decided that line needs and what it found for it.
 * Requirements are NOT flattened together: each one keeps its own intent,
 * query and ranked candidate set, because that mapping is the product.
 */
/** Cheap containment test used to drop echo-of-the-narration descriptions. */
function isRedundant(description: string, narration: string): boolean {
  const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
  const d = norm(description);
  const n = norm(narration);
  return !d || n.includes(d) || d.includes(n);
}

export default function SceneCard({ segment }: { segment: ContentSegment }) {
  const requirements = segment.requirements ?? [];
  const totalAssets = requirements.reduce((n, r) => n + r.assets.length, 0);

  // The heuristic analyser writes "Visual for: <narration>", which just repeats
  // the quote above it. Only show the description when it says something new.
  const description =
    segment.scene_description && !isRedundant(segment.scene_description, segment.text)
      ? segment.scene_description
      : null;

  return (
    <section
      aria-labelledby={`scene-${segment.sequence}`}
      className="grid gap-6 border-t border-line py-8 lg:grid-cols-12 lg:gap-10"
    >
      {/* ── Left: the script ─────────────────────────────────────────────── */}
      <div className="lg:col-span-4">
        <div className="lg:sticky lg:top-24">
          <div className="flex items-baseline gap-3">
            <h3
              id={`scene-${segment.sequence}`}
              className="font-mono text-label uppercase tracking-[0.16em] text-ochre"
            >
              Scene {String(segment.sequence).padStart(2, '0')}
            </h3>
            {segment.start_time && segment.end_time && (
              <span className="font-mono text-micro uppercase text-faint">
                {segment.start_time}–{segment.end_time}
              </span>
            )}
            {segment.importance === 'high' && (
              <span className="border border-line px-1.5 py-0.5 font-mono text-micro uppercase text-muted">
                Key beat
              </span>
            )}
          </div>

          <blockquote className="mt-4 border-l-2 border-line pl-4 text-[15px] leading-relaxed text-bone">
            {segment.text}
          </blockquote>

          {description && (
            <p className="mt-4 pl-4 text-xs leading-relaxed text-faint">{description}</p>
          )}

          <p className="mt-5 pl-4 font-mono text-micro uppercase text-faint">
            {requirements.length} requirement{requirements.length === 1 ? '' : 's'} ·{' '}
            {totalAssets} asset{totalAssets === 1 ? '' : 's'}
          </p>
        </div>
      </div>

      {/* ── Right: what it needs, and what was found ─────────────────────── */}
      <div className="space-y-8 lg:col-span-8">
        {requirements.length === 0 ? (
          <p className="border border-dashed border-line px-4 py-8 text-center text-xs text-faint">
            No visual requirement was generated for this line.
          </p>
        ) : (
          requirements.map((req, i) => (
            <RequirementBlock key={req.id} requirement={req} index={i} />
          ))
        )}
      </div>
    </section>
  );
}

function RequirementBlock({
  requirement,
  index,
}: {
  requirement: AssetRequirement;
  index: number;
}) {
  const assets = requirement.assets ?? [];

  return (
    <div className={index > 0 ? 'border-t border-lineSoft pt-8' : ''}>
      {/* The decision: what this line needs to show. */}
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="font-mono text-micro uppercase text-faint">Needs</span>
        <span aria-hidden="true" className="font-mono text-micro text-faint">
          →
        </span>
        <span className="border border-ochre/50 bg-ochre-wash px-2 py-1 font-mono text-label uppercase text-ochre">
          {humanizeIntent(requirement.asset_type)}
        </span>
        <span className="border border-line px-2 py-1 font-mono text-micro uppercase text-muted">
          {requirement.priority} priority
        </span>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-bone">{requirement.description}</p>

      {requirement.reason && (
        <p className="mt-1.5 text-xs leading-relaxed text-muted">{requirement.reason}</p>
      )}

      <p className="mt-3 font-mono text-micro uppercase text-faint">
        Searched for{' '}
        <span className="text-muted normal-case">&ldquo;{requirement.search_query}&rdquo;</span>
      </p>

      {/* The results. */}
      {assets.length === 0 ? (
        <div className="mt-5 border border-dashed border-line px-4 py-8 text-center">
          <p className="font-mono text-label uppercase text-rust">Nothing found</p>
          <p className="mx-auto mt-2 max-w-sm text-xs leading-relaxed text-muted">
            No source returned a usable candidate for this query. Naming a specific product,
            company or place in the line usually fixes it — or search manually using the query
            above.
          </p>
        </div>
      ) : (
        <>
          <p className="mt-5 font-mono text-micro uppercase text-faint">
            {assets.length} candidate{assets.length === 1 ? '' : 's'}, best first
          </p>
          <ul className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {assets.map((asset) => (
              <li key={asset.id}>
                <AssetCard asset={asset} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
