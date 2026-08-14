'use client';

import { ContentSegment } from '@/types';
import AssetCard from '@/components/AssetCard';
import { Clock, Eye, Sparkles, AlertCircle } from 'lucide-react';

interface SceneCardProps {
  segment: ContentSegment;
}

export default function SceneCard({ segment }: SceneCardProps) {
  // Aggregate all assets across requirements for this segment
  const allAssets = segment.requirements.flatMap((req) => req.assets);
  
  const recommendedAsset = allAssets.find((a) => a.status === 'recommended') || allAssets[0];
  const alternativeAssets = allAssets.filter((a) => a.id !== recommendedAsset?.id);

  const mainRequirement = segment.requirements[0];

  const formatIntentLabel = (intent?: string) => {
    if (!intent) return 'Visual B-Roll';
    return intent.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="bg-surface border border-surfaceBorder rounded-2xl p-6 space-y-6 shadow-xl">
      {/* Scene Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surfaceBorder">
        <div className="flex items-center space-x-3">
          <span className="bg-blue-600/20 border border-blue-500/30 text-blue-400 text-xs font-black uppercase tracking-wider px-3 py-1 rounded-lg">
            SCENE {String(segment.sequence).padStart(2, '0')}
          </span>
          {segment.start_time && segment.end_time && (
            <div className="flex items-center space-x-1.5 text-xs text-gray-400 font-mono">
              <Clock className="w-3.5 h-3.5 text-gray-500" />
              <span>{segment.start_time} – {segment.end_time}</span>
            </div>
          )}
        </div>

        {/* Intent Badge */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-400">VISUAL NEEDED:</span>
          <span className="inline-flex items-center space-x-1.5 text-xs font-semibold text-indigo-300 bg-indigo-500/10 border border-indigo-500/30 px-3 py-1 rounded-full">
            <Eye className="w-3.5 h-3.5 text-indigo-400" />
            <span>{formatIntentLabel(segment.visual_intent)}</span>
          </span>
        </div>
      </div>

      {/* Narration Script Text */}
      <div className="bg-background/80 p-4 rounded-xl border border-surfaceBorder/80 space-y-1">
        <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest block">NARRATION SCRIPT:</span>
        <blockquote className="text-base text-gray-100 font-medium italic leading-relaxed">
          &ldquo;{segment.text}&rdquo;
        </blockquote>
      </div>

      {/* Requirement Rationale */}
      {mainRequirement && (
        <div className="flex items-start space-x-2.5 text-xs text-gray-300 bg-blue-950/20 border border-blue-500/20 p-3 rounded-xl">
          <Sparkles className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-blue-300">Requirement Context: </span>
            <span>{mainRequirement.description}</span>
            {mainRequirement.reason && <p className="text-gray-400 text-[11px] mt-0.5">{mainRequirement.reason}</p>}
          </div>
        </div>
      )}

      {/* Assets Grid */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <span>Discovered Visual Assets</span>
            <span className="text-xs font-normal text-gray-400 font-mono">({allAssets.length} found)</span>
          </h3>
        </div>

        {allAssets.length === 0 ? (
          <div className="p-8 text-center bg-background/40 border border-dashed border-surfaceBorder rounded-xl text-gray-500 text-sm">
            <AlertCircle className="w-6 h-6 mx-auto mb-2 text-gray-600" />
            <span>No assets discovered for this segment.</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {/* Recommended Asset */}
            {recommendedAsset && (
              <div className="md:col-span-1 lg:col-span-1">
                <AssetCard asset={recommendedAsset} isRecommended={true} />
              </div>
            )}

            {/* Alternative Assets */}
            {alternativeAssets.map((asset) => (
              <div key={asset.id} className="md:col-span-1 lg:col-span-1">
                <AssetCard asset={asset} isRecommended={false} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
