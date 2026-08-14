'use client';

import { ProjectSummary } from '@/types';
import { Clock, Download, CheckCircle, ShieldAlert, Layers, Sparkles, Database } from 'lucide-react';

interface ProjectSummaryProps {
  summary: ProjectSummary;
  onExport: (format: 'json' | 'csv') => void;
}

export default function ProjectSummaryView({ summary, onExport }: ProjectSummaryProps) {
  const formatMinutes = (mins: number) => {
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    if (hours > 0) return `~${hours}h ${remainingMins}m`;
    return `~${mins}m`;
  };

  return (
    <div className="bg-surface border border-surfaceBorder rounded-2xl p-6 sm:p-8 space-y-6 shadow-2xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-surfaceBorder">
        <div>
          <div className="flex items-center space-x-2">
            <span className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full">
              PROJECT COMPLETE
            </span>
          </div>
          <h2 className="text-2xl font-bold text-white mt-2">Visual Research Package Manifest</h2>
          <p className="text-sm text-gray-400">All assets categorized, scored, and mapped to script timeline.</p>
        </div>

        {/* Export Actions */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => onExport('json')}
            className="flex items-center space-x-2 text-xs font-semibold text-gray-300 bg-surfaceBorder hover:bg-gray-700 px-4 py-2.5 rounded-xl transition"
          >
            <Download className="w-4 h-4" />
            <span>Export JSON</span>
          </button>
          <button
            onClick={() => onExport('csv')}
            className="flex items-center space-x-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 px-4 py-2.5 rounded-xl transition shadow-lg shadow-blue-600/20 active:scale-95"
          >
            <Download className="w-4 h-4" />
            <span>Export Package Manifest (.CSV)</span>
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-background/60 border border-surfaceBorder/80 p-4 rounded-xl space-y-1">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">SCENES</span>
          <p className="text-2xl font-black text-white">{summary.total_scenes}</p>
        </div>

        <div className="bg-background/60 border border-surfaceBorder/80 p-4 rounded-xl space-y-1">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">REQUIREMENTS</span>
          <p className="text-2xl font-black text-blue-400">{summary.total_requirements}</p>
        </div>

        <div className="bg-background/60 border border-surfaceBorder/80 p-4 rounded-xl space-y-1">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">DISCOVERED ASSETS</span>
          <p className="text-2xl font-black text-indigo-400">{summary.total_assets}</p>
        </div>

        <div className="bg-background/60 border border-surfaceBorder/80 p-4 rounded-xl space-y-1">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">HIGH MATCHES (&ge;80)</span>
          <p className="text-2xl font-black text-emerald-400">{summary.high_confidence_matches}</p>
        </div>

        <div className="bg-background/60 border border-surfaceBorder/80 p-4 rounded-xl space-y-1">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">SOURCES</span>
          <p className="text-2xl font-black text-purple-400">{summary.total_sources}</p>
        </div>

        <div className="bg-background/60 border border-surfaceBorder/80 p-4 rounded-xl space-y-1">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">MANUAL REVIEWS</span>
          <p className="text-2xl font-black text-amber-400">{summary.manual_review_items}</p>
        </div>
      </div>

      {/* Time Efficiency Comparison */}
      <div className="bg-gradient-to-r from-blue-950/40 via-surface to-indigo-950/40 border border-blue-500/20 p-6 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-1 text-center md:text-left">
          <h4 className="text-sm font-bold text-blue-300 uppercase tracking-wider flex items-center justify-center md:justify-start space-x-2">
            <Clock className="w-4 h-4 text-blue-400" />
            <span>Research Efficiency Saved</span>
          </h4>
          <p className="text-xs text-gray-400">
            Based on average manual asset searching rate of ~5 mins per scene requirement vs SLAYERS automated discovery.
          </p>
        </div>

        <div className="flex items-center space-x-6 sm:space-x-12 shrink-0">
          <div className="text-center">
            <span className="text-[10px] font-bold uppercase text-gray-400 block tracking-widest">EST. MANUAL RESEARCH</span>
            <span className="text-xl font-bold text-gray-300 line-through decoration-red-500 decoration-2">
              {formatMinutes(summary.estimated_manual_time_minutes)}
            </span>
          </div>

          <div className="text-2xl font-extrabold text-blue-500">&rarr;</div>

          <div className="text-center">
            <span className="text-[10px] font-bold uppercase text-emerald-400 block tracking-widest">SLAYERS PIPELINE</span>
            <span className="text-2xl font-black text-emerald-400">
              ~{summary.slayers_processing_time_seconds}s
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
