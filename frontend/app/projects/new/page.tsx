'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Film, Sparkles, ArrowRight, FileText, Zap, AlertCircle } from 'lucide-react';

const PRESET_SCRIPTS = [
  {
    title: 'How AI Coding Agents are Changing Software Development',
    type: 'script',
    text: `The software industry is undergoing a massive shift as AI coding agents emerge.
Developers no longer spend hours writing boilerplate code manually.
Instead, intelligent agents analyze repositories, create implementation plans, and write multi-file features.
For example, modern IDE interfaces now feature AI pair-programmers integrated right into the editor window.
This transformation allows small engineering teams to build complex software in a fraction of the time.`
  },
  {
    title: 'Introducing the Next Generation Cloud Architecture',
    type: 'script',
    text: `Today we are announcing a revolutionary serverless cloud platform built for real-time applications.
Our new analytics dashboard processes millions of events per second with sub-millisecond latency.
Engineering teams can monitor global data pipelines and microservices in real time.
Here is a live look at the user dashboard interface showing global network metrics.`
  }
];

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [sourceType, setSourceType] = useState('script');
  const [sourceText, setSourceText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !sourceText.trim()) {
      setError('Please provide both a project name and script content.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const project = await api.createProject(name, sourceText, sourceType);
      // Trigger processing pipeline
      await api.startProcessing(project.id);
      router.push(`/projects/${project.id}`);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to create project.');
      setLoading(false);
    }
  };

  const loadPreset = (preset: typeof PRESET_SCRIPTS[0]) => {
    setName(preset.title);
    setSourceType(preset.type);
    setSourceText(preset.text);
    setError(null);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-4">
      <div className="space-y-2">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>NEW VISUAL ASSET PACKAGE</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white">Create a Visual Research Project</h1>
        <p className="text-sm text-gray-400">
          Paste your script or transcript below. SLAYERS will automatically extract scenes, detect visual intents, and discover matching assets.
        </p>
      </div>

      {/* Preset Pickers */}
      <div className="space-y-3">
        <span className="text-xs font-bold uppercase tracking-wider text-gray-400 block">Quick Demo Presets:</span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {PRESET_SCRIPTS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => loadPreset(preset)}
              className="text-left p-3.5 bg-surface hover:bg-surfaceBorder border border-surfaceBorder rounded-xl transition space-y-1 group"
            >
              <span className="text-xs font-semibold text-blue-400 group-hover:text-blue-300 flex items-center space-x-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Preset {idx + 1}</span>
              </span>
              <p className="text-sm font-medium text-white line-clamp-1">{preset.title}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Project Form */}
      <form onSubmit={handleSubmit} className="bg-surface border border-surfaceBorder rounded-2xl p-6 sm:p-8 space-y-6 shadow-2xl">
        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-gray-300 block">Project Title</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. AI Agents Explainer Video Script"
            className="w-full bg-background border border-surfaceBorder rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
            required
          />
        </div>

        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-gray-300 block">Content Type</label>
          <div className="grid grid-cols-3 gap-3">
            {[
              { id: 'script', label: 'Video Script' },
              { id: 'transcript', label: 'Audio Transcript' },
              { id: 'text', label: 'Raw Article / Text' },
            ].map((type) => (
              <button
                key={type.id}
                type="button"
                onClick={() => setSourceType(type.id)}
                className={`py-2.5 px-3 rounded-xl text-xs font-semibold border transition ${
                  sourceType === type.id
                    ? 'bg-blue-600 border-blue-500 text-white shadow-md'
                    : 'bg-background border-surfaceBorder text-gray-400 hover:text-white'
                }`}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-gray-300 block">Script / Transcript Content</label>
          <textarea
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            rows={10}
            placeholder="Paste your video narration script or video transcript here..."
            className="w-full bg-background border border-surfaceBorder rounded-xl p-4 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition font-mono leading-relaxed"
            required
          />
          <p className="text-[11px] text-gray-500 text-right font-mono">
            {sourceText.trim().split(/\s+/).filter(Boolean).length} words
          </p>
        </div>

        {error && (
          <div className="p-4 bg-red-950/30 border border-red-500/30 rounded-xl text-red-300 text-sm flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="pt-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center space-x-3 text-base font-bold text-white bg-blue-600 hover:bg-blue-500 px-6 py-4 rounded-xl shadow-xl shadow-blue-600/30 transition active:scale-95 disabled:opacity-50"
          >
            <span>{loading ? 'Creating Project & Triggering Engine...' : 'Build Visual Package'}</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </form>
    </div>
  );
}
