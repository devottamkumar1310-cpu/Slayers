'use client';

import { Asset } from '@/types';
import { ExternalLink, Download, ShieldAlert, ShieldCheck, CheckCircle2, Film, Image as ImageIcon } from 'lucide-react';

interface AssetCardProps {
  asset: Asset;
  isRecommended?: boolean;
}

export default function AssetCard({ asset, isRecommended = false }: AssetCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400';
    if (score >= 60) return 'bg-blue-500/10 border-blue-500/30 text-blue-400';
    return 'bg-amber-500/10 border-amber-500/30 text-amber-400';
  };

  const isManualReview = asset.license_info.toLowerCase().includes('verify') || asset.status === 'flagged';

  return (
    <div
      className={`rounded-xl border transition-all overflow-hidden flex flex-col justify-between ${
        isRecommended
          ? 'bg-surface border-blue-500/40 shadow-xl shadow-blue-500/5 ring-1 ring-blue-500/20'
          : 'bg-surface/60 border-surfaceBorder hover:border-gray-600'
      }`}
    >
      <div>
        {/* Thumbnail Preview Header */}
        <div className="relative aspect-video w-full bg-background overflow-hidden group">
          {asset.thumbnail_url || asset.asset_url ? (
            <img
              src={asset.thumbnail_url || asset.asset_url}
              alt={asset.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              onError={(e) => {
                // Fallback for image load failure
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-surfaceBorder/30 text-gray-500">
              {asset.asset_type === 'video' ? <Film className="w-8 h-8" /> : <ImageIcon className="w-8 h-8" />}
            </div>
          )}

          {/* Recommended Tag */}
          {isRecommended && (
            <div className="absolute top-2 left-2 bg-blue-600 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md shadow-md">
              RECOMMENDED
            </div>
          )}

          {/* Score Badge */}
          <div
            className={`absolute top-2 right-2 border text-xs font-bold px-2 py-0.5 rounded-md backdrop-blur-md shadow-md ${getScoreColor(
              asset.relevance_score
            )}`}
          >
            {asset.relevance_score} MATCH
          </div>
        </div>

        {/* Content Details */}
        <div className="p-4 space-y-3">
          <div className="flex items-start justify-between gap-2">
            <h4 className="text-sm font-semibold text-white line-clamp-2" title={asset.title}>
              {asset.title}
            </h4>
          </div>

          {/* Rationale / Why */}
          {asset.usage_notes && (
            <div className="text-xs text-gray-300 bg-background/60 p-2.5 rounded-lg border border-surfaceBorder/60 space-y-1">
              <span className="text-[10px] uppercase font-bold text-gray-400 block tracking-wider">WHY THIS ASSET:</span>
              <p className="leading-relaxed">{asset.usage_notes}</p>
            </div>
          )}

          {/* Source & License Metadata */}
          <div className="space-y-1.5 pt-1 text-xs">
            <div className="flex items-center justify-between text-gray-400">
              <span>Source:</span>
              <span className="font-medium text-gray-200">{asset.source}</span>
            </div>

            <div className="flex items-center justify-between text-gray-400">
              <span>License:</span>
              <span className="font-medium text-gray-300 truncate max-w-[180px]" title={asset.license_info}>
                {asset.license_info}
              </span>
            </div>

            {/* License Usage Status Tag */}
            <div className="flex items-center justify-between pt-1">
              <span className="text-gray-400">Usage Status:</span>
              {isManualReview ? (
                <span className="inline-flex items-center space-x-1 text-[11px] font-semibold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/30">
                  <ShieldAlert className="w-3 h-3" />
                  <span>VERIFY MANUALLY</span>
                </span>
              ) : (
                <span className="inline-flex items-center space-x-1 text-[11px] font-semibold text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded border border-emerald-400/30">
                  <ShieldCheck className="w-3 h-3" />
                  <span>COMMERCIAL OK</span>
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="p-4 pt-0 flex items-center space-x-2">
        <a
          href={asset.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 inline-flex items-center justify-center space-x-1.5 text-xs font-semibold text-gray-300 bg-surfaceBorder/60 hover:bg-surfaceBorder hover:text-white px-3 py-2 rounded-lg transition"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span>Open Source</span>
        </a>

        <a
          href={asset.asset_url}
          target="_blank"
          download
          rel="noopener noreferrer"
          className="flex-1 inline-flex items-center justify-center space-x-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 px-3 py-2 rounded-lg transition shadow-md"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Asset Direct</span>
        </a>
      </div>
    </div>
  );
}
