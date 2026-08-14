'use client';

import { useEffect, useState } from 'react';
import { ProcessingJob } from '@/types';
import { api } from '@/lib/api';
import { Loader2, CheckCircle2, AlertCircle, Sparkles, Search, Layers, ShieldCheck, Cpu } from 'lucide-react';

interface ProcessingViewProps {
  projectId: string;
  onCompleted: () => void;
}

const PIPELINE_STEPS = [
  { label: 'Content analyzed & beats identified', minProgress: 15, icon: Cpu },
  { label: 'Scenes & timestamps detected', minProgress: 35, icon: Layers },
  { label: 'Visual requirements & intents generated', minProgress: 55, icon: Sparkles },
  { label: 'Assets searched across providers', minProgress: 75, icon: Search },
  { label: 'Relevance scored & licenses verified', minProgress: 90, icon: ShieldCheck },
  { label: 'Visual asset package assembled', minProgress: 100, icon: CheckCircle2 },
];

export default function ProcessingView({ projectId, onCompleted }: ProcessingViewProps) {
  const [job, setJob] = useState<ProcessingJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;
    let isMounted = true;

    const pollStatus = async () => {
      if (!isMounted) return;
      try {
        const status = await api.getProjectStatus(projectId);
        if (!isMounted) return;
        setJob(status);

        if (status.status === 'completed') {
          if (intervalId) clearInterval(intervalId);
          isMounted = false;
          setTimeout(() => {
            onCompleted();
          }, 800);
        } else if (status.status === 'failed') {
          if (intervalId) clearInterval(intervalId);
          isMounted = false;
          setError(status.error || 'Pipeline processing failed.');
        }
      } catch (err: any) {
        if (!isMounted) return;
        console.error('Status polling error:', err);
        if (err.message && err.message.includes('404')) {
          if (intervalId) clearInterval(intervalId);
          isMounted = false;
          setError('Project not found (404). It may have been deleted.');
        }
      }
    };

    pollStatus();
    intervalId = setInterval(pollStatus, 1200);

    return () => {
      isMounted = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [projectId, onCompleted]);

  const progress = job?.progress || 5;

  return (
    <div className="max-w-3xl mx-auto my-12 p-8 bg-surface border border-surfaceBorder rounded-2xl shadow-2xl space-y-8">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-medium">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>SLAYERS ASSET ENGINE WORKING</span>
        </div>
        <h2 className="text-2xl font-bold text-white">Analyzing Script & Sourcing Visual Assets</h2>
        <p className="text-sm text-gray-400">
          Automating scene segmentation, visual intent extraction, provider searches, and relevance scoring.
        </p>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs font-semibold text-gray-300">
          <span>{job?.current_step || 'Initializing...'}</span>
          <span className="text-blue-400">{progress}%</span>
        </div>
        <div className="w-full bg-background rounded-full h-3 overflow-hidden p-0.5 border border-surfaceBorder">
          <div
            className="bg-gradient-to-r from-blue-600 to-indigo-400 h-full rounded-full transition-all duration-500 ease-out shadow-md shadow-blue-500/50"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Pipeline Checklist */}
      <div className="space-y-3 pt-4 border-t border-surfaceBorder">
        {PIPELINE_STEPS.map((step, idx) => {
          const isDone = progress >= step.minProgress;
          const isCurrent = progress < step.minProgress && (idx === 0 || progress >= PIPELINE_STEPS[idx - 1].minProgress);
          const StepIcon = step.icon;

          return (
            <div
              key={idx}
              className={`flex items-center justify-between p-3.5 rounded-xl border transition ${
                isDone
                  ? 'bg-blue-950/20 border-blue-500/30 text-blue-200'
                  : isCurrent
                  ? 'bg-surfaceBorder/40 border-blue-500/50 text-white animate-pulse'
                  : 'bg-background/40 border-transparent text-gray-500'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    isDone
                      ? 'bg-blue-500/20 text-blue-400'
                      : isCurrent
                      ? 'bg-blue-600/30 text-blue-300'
                      : 'bg-surfaceBorder/40 text-gray-600'
                  }`}
                >
                  <StepIcon className="w-4 h-4" />
                </div>
                <span className="text-sm font-medium">{step.label}</span>
              </div>

              <div>
                {isDone ? (
                  <CheckCircle2 className="w-5 h-5 text-emeraldGlow" />
                ) : isCurrent ? (
                  <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                ) : (
                  <div className="w-2 h-2 rounded-full bg-gray-700" />
                )}
              </div>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="p-4 bg-red-950/30 border border-red-500/30 rounded-xl text-red-300 text-sm flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Processing Failure</p>
            <p className="text-xs text-red-400/80 mt-1">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
