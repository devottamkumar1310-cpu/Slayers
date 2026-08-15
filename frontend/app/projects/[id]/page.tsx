'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import type { Project, ProjectSummary } from '@/types';
import { api, ApiError } from '@/lib/api';
import { exportProject } from '@/lib/export';
import { formatDate } from '@/lib/format';
import BoardSummary from '@/components/BoardSummary';
import ErrorNotice from '@/components/ErrorNotice';
import ProcessingView from '@/components/ProcessingView';
import SceneCard from '@/components/SceneCard';
import StatusDot from '@/components/StatusDot';

export default function ProjectPage() {
  return (
    <Suspense fallback={<BoardSkeleton />}>
      <ProjectBoard />
    </Suspense>
  );
}

function ProjectBoard() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const projectId = params?.id as string;
  const autostart = searchParams?.get('autostart') === '1';

  const [project, setProject] = useState<Project | null>(null);
  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showProcessing, setShowProcessing] = useState(autostart);
  const [starting, setStarting] = useState(false);

  const load = useCallback(async () => {
    if (!projectId) return;
    setError(null);
    setNotFound(false);
    try {
      const proj = await api.getProject(projectId);
      setProject(proj);

      const running =
        proj.status === 'processing' || proj.processing_job?.status === 'processing';
      setShowProcessing(running);

      if (proj.status === 'completed') {
        try {
          setSummary(await api.getProjectSummary(projectId));
        } catch {
          // A missing summary must not blank the board — the scenes still render.
          setSummary(null);
        }
      } else {
        setSummary(null);
      }
    } catch (err) {
      if (err instanceof ApiError && err.isNotFound) {
        setNotFound(true);
      } else {
        setError(err instanceof ApiError ? err.message : 'Could not load this board.');
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleProcessingDone = useCallback(() => {
    setShowProcessing(false);
    setLoading(true);
    void load();
  }, [load]);

  const startRun = async () => {
    setStarting(true);
    setActionError(null);
    try {
      await api.startProcessing(projectId);
      setShowProcessing(true);
    } catch (err) {
      if (err instanceof ApiError && err.isConflict) {
        // Already running elsewhere — follow it rather than showing an error.
        setShowProcessing(true);
      } else {
        setActionError(err instanceof ApiError ? err.message : 'Could not start the run.');
      }
    } finally {
      setStarting(false);
    }
  };

  const handleExport = (format: 'csv' | 'json') => {
    if (project) exportProject(project, summary, format);
  };

  if (loading) return <BoardSkeleton />;

  if (notFound) {
    return (
      <div className="mx-auto max-w-lg py-24 text-center">
        <p className="eyebrow">404</p>
        <h1 className="mt-4 text-2xl font-semibold tracking-tight text-bone">
          No board with that id
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          It may have been deleted, or the link may be incomplete.
        </p>
        <Link href="/projects" className="btn-ghost mt-6">
          Back to boards
        </Link>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="mx-auto max-w-lg py-24">
        <ErrorNotice message={error ?? 'Could not load this board.'} onRetry={load} />
        <Link
          href="/projects"
          className="mt-6 inline-block font-mono text-label uppercase text-muted hover:text-bone"
        >
          ← Back to boards
        </Link>
      </div>
    );
  }

  const scenes = project.segments ?? [];
  const isDraft = project.status === 'draft' && !showProcessing;
  const isFailed = project.status === 'failed' && !showProcessing;

  return (
    <div className="py-8">
      {/* ── Board header ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-6">
        <div className="min-w-0">
          <Link
            href="/projects"
            className="font-mono text-micro uppercase text-faint hover:text-bone"
          >
            ← Boards
          </Link>
          <div className="mt-3 flex items-center gap-2.5">
            <StatusDot status={project.status} />
            <h1 className="truncate text-2xl font-semibold tracking-tight text-bone">
              {project.name}
            </h1>
          </div>
          <p className="mt-2 font-mono text-micro uppercase text-faint">
            {project.source_type} · created {formatDate(project.created_at)} ·{' '}
            {project.source_text.length.toLocaleString()} chars
          </p>
        </div>

        {!showProcessing && (
          <button type="button" onClick={startRun} disabled={starting} className="btn-ghost">
            {starting ? 'Starting…' : isDraft ? 'Analyse & find visuals' : 'Re-run pipeline'}
          </button>
        )}
      </div>

      {actionError && (
        <div className="max-w-xl pt-6">
          <ErrorNotice message={actionError} />
        </div>
      )}

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      {showProcessing ? (
        <ProcessingView projectId={projectId} onCompleted={handleProcessingDone} />
      ) : isDraft ? (
        <div className="mx-auto max-w-xl py-24 text-center">
          <p className="eyebrow">Not started</p>
          <h2 className="mt-4 text-xl font-semibold tracking-tight text-bone">
            The script is saved. Nothing has been searched yet.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Running the pipeline splits it into scenes, decides what each one needs to show,
            and searches every configured source for it.
          </p>
          <button type="button" onClick={startRun} disabled={starting} className="btn-primary mt-6">
            {starting ? 'Starting…' : 'Analyse & find visuals'}
          </button>
        </div>
      ) : isFailed ? (
        <div className="mx-auto max-w-xl py-20">
          <ErrorNotice
            message={
              project.processing_job?.error ||
              'The last run failed before it produced a board.'
            }
            hint="The script is unchanged — re-running starts the pipeline from the beginning."
            onRetry={startRun}
            retryLabel={starting ? 'Restarting…' : 'Re-run pipeline'}
          />
        </div>
      ) : (
        <div className="pt-8">
          {summary && (
            <BoardSummary
              summary={summary}
              job={project.processing_job}
              onExport={handleExport}
            />
          )}

          <div className="flex flex-wrap items-baseline justify-between gap-3 pt-10">
            <h2 className="text-lg font-semibold tracking-tight text-bone">Visual board</h2>
            <p className="font-mono text-micro uppercase text-faint">
              Script on the left · what it needs and what was found on the right
            </p>
          </div>

          {scenes.length === 0 ? (
            <div className="mt-6 border border-dashed border-line px-6 py-20 text-center">
              <p className="eyebrow">Empty board</p>
              <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-muted">
                The run finished without producing any scenes. That usually means the script
                was too short or contained no usable sentences.
              </p>
              <button type="button" onClick={startRun} className="btn-ghost mt-6">
                Re-run pipeline
              </button>
            </div>
          ) : (
            <div className="mt-2">
              {scenes.map((segment) => (
                <SceneCard key={segment.id} segment={segment} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BoardSkeleton() {
  return (
    <div className="py-10" aria-busy="true">
      <div className="h-3 w-24 animate-pulse bg-line" />
      <div className="mt-4 h-6 w-2/3 max-w-md animate-pulse bg-line" />
      <div className="mt-10 grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-panel p-4">
            <div className="h-2 w-16 animate-pulse bg-line" />
            <div className="mt-3 h-6 w-10 animate-pulse bg-line" />
          </div>
        ))}
      </div>
      <p className="sr-only">Loading board…</p>
    </div>
  );
}
