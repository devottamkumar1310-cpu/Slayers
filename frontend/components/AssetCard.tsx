'use client';

import { useState } from 'react';
import type { Asset } from '@/types';
import {
  describeStatus,
  describeUsage,
  humanizeIntent,
  parseScoreFactors,
  scoreRationale,
  scoreTone,
} from '@/lib/format';
import { fileKind, isDocumentAsset, previewUrl } from '@/lib/preview';

export default function AssetCard({ asset }: { asset: Asset }) {
  const [imageFailed, setImageFailed] = useState(false);
  const [showBreakdown, setShowBreakdown] = useState(false);

  const status = describeStatus(asset.status);
  const usage = describeUsage(asset.usage_status);
  const factors = parseScoreFactors(asset.usage_notes);
  const rationale = scoreRationale(asset.usage_notes);
  const src = previewUrl(asset);
  const kind = fileKind(asset);
  const isDocument = isDocumentAsset(asset);
  const isRecommended = asset.status === 'recommended';

  return (
    <article
      className={`flex h-full flex-col border bg-panel ${
        isRecommended ? 'border-sage/45' : 'border-line'
      }`}
    >
      {/* ── The asset itself: the brightest, largest thing on the card ─────── */}
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-raised">
        {src && !imageFailed ? (
          /* eslint-disable-next-line @next/next/no-img-element -- remote hosts
             are open-ended (any provider CDN); next/image is configured
             unoptimized anyway, so a plain img avoids the allow-list trap. */
          <img
            src={src}
            alt={asset.title}
            loading="lazy"
            decoding="async"
            onError={() => setImageFailed(true)}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-faint">
            <span aria-hidden="true" className="h-8 w-8 border border-faint" />
            <span className="font-mono text-micro uppercase">
              {imageFailed ? 'Preview unavailable' : 'No preview'}
            </span>
          </div>
        )}

        {/* File type matters to an editor: a "match" that is a PDF scan is not
            drop-in footage, and the card should say so before they click. */}
        {kind && (
          <div
            className={`absolute bottom-0 right-0 px-2 py-1 font-mono text-micro uppercase ${
              isDocument ? 'bg-rust/90 text-ink' : 'bg-ink/90 text-faint'
            }`}
          >
            {kind}
          </div>
        )}

        {/* Score chip — solid so it stays legible on any image. */}
        <div className="absolute right-0 top-0 flex items-baseline gap-1 bg-ink/90 px-2.5 py-1.5">
          <span className={`font-mono text-base leading-none ${scoreTone(asset.relevance_score)}`}>
            {asset.relevance_score}
          </span>
          <span className="font-mono text-micro uppercase text-faint">match</span>
        </div>

        {/* Status ribbon */}
        <div className="absolute bottom-0 left-0 bg-ink/90 px-2.5 py-1">
          <span className={`font-mono text-micro uppercase ${status.text}`} title={status.hint}>
            {status.label}
          </span>
        </div>
      </div>

      {/* ── Metadata ───────────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col p-3.5">
        <h4 className="line-clamp-2 text-[13px] font-medium leading-snug text-bone" title={asset.title}>
          {asset.title}
        </h4>

        <dl className="mt-3 space-y-1.5 font-mono text-micro uppercase">
          <div className="flex justify-between gap-3">
            <dt className="text-faint">Source</dt>
            <dd className="truncate text-muted" title={asset.source}>
              {asset.source}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-faint">Type</dt>
            <dd className="text-muted">{humanizeIntent(asset.asset_type, 'Image')}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-faint">Usage</dt>
            <dd className={usage.tone === 'ok' ? 'text-muted' : 'text-rust'}>{usage.label}</dd>
          </div>
        </dl>

        {/* Licence, verbatim from the source. */}
        <p className="mt-3 border-t border-lineSoft pt-3 text-[11px] leading-relaxed text-muted">
          <span className="font-mono text-micro uppercase text-faint">Licence · </span>
          {asset.license_info}
          {asset.license_url && (
            <>
              {' '}
              <a
                href={asset.license_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-ochre underline underline-offset-2 hover:text-bone"
              >
                terms
              </a>
            </>
          )}
        </p>
        <p className={`mt-1.5 text-[11px] leading-relaxed ${usage.tone === 'ok' ? 'text-faint' : 'text-rust'}`}>
          {usage.note}
        </p>

        {/* Why this score — parsed from the backend's own breakdown. */}
        {(factors.length > 0 || rationale) && (
          <div className="mt-3 border-t border-lineSoft pt-3">
            <button
              type="button"
              onClick={() => setShowBreakdown((v) => !v)}
              aria-expanded={showBreakdown}
              className="font-mono text-micro uppercase text-ochre hover:text-bone"
            >
              {showBreakdown ? '− Hide score detail' : '+ Why this score'}
            </button>

            {showBreakdown && (
              <div className="mt-3 space-y-2">
                {factors.map((f) => (
                  <div key={f.label}>
                    <div className="flex justify-between font-mono text-micro uppercase">
                      <span className="text-faint">{f.label}</span>
                      <span className="text-muted">
                        {f.value}/{f.max}
                      </span>
                    </div>
                    <div className="mt-1 h-0.5 w-full bg-line">
                      <div
                        className="h-full bg-ochre"
                        style={{ width: `${(f.value / f.max) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
                {rationale && (
                  <p className="pt-1 text-[11px] leading-relaxed text-muted">{rationale}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Actions pinned to the bottom so cards align in a row. */}
        <div className="mt-auto flex gap-px border-t border-line pt-3.5">
          <a
            href={asset.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 border border-line px-2 py-2 text-center font-mono text-micro uppercase text-muted transition-colors hover:border-faint hover:text-bone"
          >
            Source page
          </a>
          <a
            href={asset.asset_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 border border-l-0 border-line px-2 py-2 text-center font-mono text-micro uppercase text-muted transition-colors hover:border-faint hover:text-bone"
          >
            Open file
          </a>
        </div>
      </div>
    </article>
  );
}
