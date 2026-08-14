'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { api } from '@/lib/api';
import { Film, Sparkles, ArrowRight, Layers, Search, ShieldCheck, CheckCircle2, Play, Zap } from 'lucide-react';

export default function LandingPage() {
  const router = useRouter();
  const [loadingDemo, setLoadingDemo] = useState(false);

  const handleRunDemo = async () => {
    setLoadingDemo(true);
    try {
      const demoProject = await api.createDemoProject();
      router.push(`/projects/${demoProject.id}`);
    } catch (err) {
      console.error('Failed to create demo project:', err);
      setLoadingDemo(false);
    }
  };

  return (
    <div className="space-y-24 py-8">
      {/* Hero Section */}
      <section className="text-center space-y-8 max-w-4xl mx-auto pt-8">
        <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-semibold uppercase tracking-wider">
          <Sparkles className="w-3.5 h-3.5" />
          <span>AI Visual Research Engine for Creators</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
          Turn your script into a <br className="hidden sm:inline" />
          <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-sky-400 bg-clip-text text-transparent">
            ready-to-edit visual asset package
          </span>
        </h1>

        <p className="text-lg sm:text-xl text-gray-300 max-w-2xl mx-auto leading-relaxed">
          Editors spend hours searching for B-roll, screenshots, product footage, and graphics.
          <strong className="text-white font-semibold"> SLAYERS automates visual discovery and organizes relevant assets scene-by-scene.</strong>
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link
            href="/projects/new"
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-3 text-base font-bold text-white bg-blue-600 hover:bg-blue-500 px-8 py-4 rounded-xl shadow-xl shadow-blue-600/30 transition active:scale-95"
          >
            <span>Start a Project</span>
            <ArrowRight className="w-5 h-5" />
          </Link>

          <button
            onClick={handleRunDemo}
            disabled={loadingDemo}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-3 text-base font-semibold text-gray-200 bg-surface border border-surfaceBorder hover:border-gray-600 hover:text-white px-8 py-4 rounded-xl transition active:scale-95 disabled:opacity-50"
          >
            {loadingDemo ? (
              <Zap className="w-5 h-5 text-amber-400 animate-spin" />
            ) : (
              <Play className="w-5 h-5 text-blue-400" />
            )}
            <span>{loadingDemo ? 'Building Demo Package...' : 'Try Sample Demo Project'}</span>
          </button>
        </div>
      </section>

      {/* Core Workflow Steps */}
      <section className="space-y-8">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-white uppercase tracking-wider">The 4-Step Pipeline</h2>
          <p className="text-sm text-gray-400">How SLAYERS turns raw script into organized visuals in seconds</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-surface border border-surfaceBorder rounded-2xl p-6 space-y-4 relative overflow-hidden">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold text-lg">
              1
            </div>
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <Layers className="w-5 h-5 text-blue-400" />
              <span>Analyze</span>
            </h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Segments script into distinct narrative beats and calculates precise timeline intervals.
            </p>
          </div>

          <div className="bg-surface border border-surfaceBorder rounded-2xl p-6 space-y-4 relative overflow-hidden">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center font-bold text-lg">
              2
            </div>
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <Search className="w-5 h-5 text-indigo-400" />
              <span>Discover</span>
            </h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Distinguishes generic stock from specific product UI references and queries asset providers.
            </p>
          </div>

          <div className="bg-surface border border-surfaceBorder rounded-2xl p-6 space-y-4 relative overflow-hidden">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 flex items-center justify-center font-bold text-lg">
              3
            </div>
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-purple-400" />
              <span>Verify</span>
            </h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Scores relevance from 0–100 and verifies Creative Commons & commercial license usage notes.
            </p>
          </div>

          <div className="bg-surface border border-surfaceBorder rounded-2xl p-6 space-y-4 relative overflow-hidden">
            <div className="w-10 h-10 rounded-xl bg-emerald-600/20 text-emerald-400 flex items-center justify-center font-bold text-lg">
              4
            </div>
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emeraldGlow" />
              <span>Organize</span>
            </h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Maps recommended & alternative assets directly to scene cards ready for editor download.
            </p>
          </div>
        </div>
      </section>

      {/* Before vs After Comparison */}
      <section className="bg-surface border border-surfaceBorder rounded-3xl p-8 sm:p-12 space-y-8 shadow-2xl">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-extrabold text-white">Why Editors Need SLAYERS</h2>
          <p className="text-sm text-gray-400">Stop wasting half your editing time tab-switching on stock sites</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Before */}
          <div className="bg-background/60 border border-red-500/20 rounded-2xl p-6 space-y-4">
            <div className="flex items-center space-x-2 text-red-400 font-bold text-sm uppercase tracking-wider">
              <span>BEFORE SLAYERS</span>
            </div>
            <ul className="space-y-3 text-xs text-gray-400 leading-relaxed">
              <li className="flex items-start space-x-2">
                <span className="text-red-500 font-bold">&times;</span>
                <span>Manually read script line by line to figure out visuals</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-red-500 font-bold">&times;</span>
                <span>Open 30 tabs on generic stock video websites</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-red-500 font-bold">&times;</span>
                <span>Struggle finding specific product interfaces & logos</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-red-500 font-bold">&times;</span>
                <span>Manually verify licenses and download separate files</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-red-500 font-bold">&times;</span>
                <span>Spend ~2–3 hours on research before touching timeline</span>
              </li>
            </ul>
          </div>

          {/* After */}
          <div className="bg-blue-950/20 border border-blue-500/30 rounded-2xl p-6 space-y-4">
            <div className="flex items-center space-x-2 text-emeraldGlow font-bold text-sm uppercase tracking-wider">
              <Sparkles className="w-4 h-4" />
              <span>AFTER SLAYERS</span>
            </div>
            <ul className="space-y-3 text-xs text-gray-200 leading-relaxed">
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emeraldGlow shrink-0 mt-0.5" />
                <span>Paste script and get automatic scene breakdown</span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emeraldGlow shrink-0 mt-0.5" />
                <span>Smart detection differentiates generic B-roll from specific product UI</span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emeraldGlow shrink-0 mt-0.5" />
                <span>Multi-provider discovery fetches real assets with 0–100 relevance score</span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emeraldGlow shrink-0 mt-0.5" />
                <span>Clear Creative Commons & usage license notes for every clip</span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emeraldGlow shrink-0 mt-0.5" />
                <span>Ready in 15 seconds with downloadable visual manifest</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
