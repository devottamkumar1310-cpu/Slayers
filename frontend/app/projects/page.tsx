'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import type { Project } from '@/types';
import { api, ApiError } from '@/lib/api';
import { formatDate } from '@/lib/format';
import ErrorNotice from '@/components/ErrorNotice';
import StatusDot from '@/components/StatusDot';

export default function ProjectsIndexPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setProjects(await api.listProjects());
    } catch (err) {
      setProjects(null);
      setError(err instanceof ApiError ? err.message : 'Could not load your boards.');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="py-10">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-6">
        <div>
          <p className="eyebrow">Index</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-bone">Boards</h1>
        </div>
        <Link href="/projects/new" className="btn-primary">
          New script
        </Link>
      </div>

      {error ? (
        <div className="max-w-xl py-10">
          <ErrorNotice message={error} onRetry={load} />
        </div>
      ) : projects === null ? (
        <ul className="divide-y divide-lineSoft border-b border-line" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <li key={i} className="flex items-center gap-4 py-5">
              <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-line" />
              <span className="h-3 w-1/3 animate-pulse bg-line" />
              <span className="ml-auto h-3 w-16 animate-pulse bg-line" />
            </li>
          ))}
          <li className="sr-only">Loading boards…</li>
        </ul>
      ) : projects.length === 0 ? (
        <div className="border border-dashed border-line px-6 py-16 text-center">
          <p className="eyebrow">Nothing here yet</p>
          <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-muted">
            Paste a script and SLAYERS will break it into scenes, work out what each one
            needs to show, and go find it.
          </p>
          <Link href="/projects/new" className="btn-primary mt-6">
            Start with a script
          </Link>
        </div>
      ) : (
        <>
          <p className="py-4 font-mono text-micro uppercase text-faint">
            {projects.length} board{projects.length === 1 ? '' : 's'}
          </p>

          <ul className="divide-y divide-lineSoft border-y border-line">
            {projects.map((p) => {
              const scenes = p.segments?.length ?? 0;
              const assets =
                p.segments?.reduce(
                  (n, s) => n + s.requirements.reduce((m, r) => m + r.assets.length, 0),
                  0
                ) ?? 0;

              return (
                <li key={p.id}>
                  <Link
                    href={`/projects/${p.id}`}
                    className="group grid min-w-0 gap-3 py-5 transition-colors hover:bg-panel sm:grid-cols-12 sm:items-center sm:gap-4 sm:px-3"
                  >
                    {/* min-w-0 throughout: grid/flex children default to
                        min-width:auto, which lets a long title force the track
                        wider than the viewport and defeats `truncate`. */}
                    <div className="min-w-0 sm:col-span-6">
                      <div className="flex min-w-0 items-center gap-2.5">
                        <StatusDot status={p.status} />
                        <h2 className="truncate text-sm font-medium text-bone group-hover:text-ochre">
                          {p.name}
                        </h2>
                      </div>
                      <p className="mt-1.5 line-clamp-1 pl-[18px] text-xs text-faint">
                        {p.source_text.split('\n')[0]}
                      </p>
                    </div>

                    <dl className="flex min-w-0 gap-6 pl-[18px] font-mono text-micro uppercase sm:col-span-4 sm:pl-0">
                      <div>
                        <dt className="text-faint">Scenes</dt>
                        <dd className="mt-0.5 text-sm text-bone">{scenes || '—'}</dd>
                      </div>
                      <div>
                        <dt className="text-faint">Assets</dt>
                        <dd className="mt-0.5 text-sm text-bone">{assets || '—'}</dd>
                      </div>
                      <div>
                        <dt className="text-faint">Type</dt>
                        <dd className="mt-0.5 text-sm text-bone">{p.source_type}</dd>
                      </div>
                    </dl>

                    <div className="min-w-0 pl-[18px] font-mono text-micro uppercase text-faint sm:col-span-2 sm:pl-0 sm:text-right">
                      {formatDate(p.created_at)}
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
