'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { api, ApiError } from '@/lib/api';
import ErrorNotice from '@/components/ErrorNotice';

/* ─────────────────────────────────────────────────────────────────────────────
   Worked example used in the hero. These strings describe the SHAPE of the
   board (fields the engine really produces); they are labelled as an example
   and deliberately contain no fabricated asset imagery or scores presented as
   a real run.
   ────────────────────────────────────────────────────────────────────────── */

const EXAMPLE_LINES = [
  'The software industry is undergoing a massive shift as AI coding agents emerge.',
  'Developers no longer spend hours writing boilerplate code manually.',
  'Modern IDE interfaces now feature AI pair-programmers inside the editor window.',
  'Small engineering teams can build complex software in a fraction of the time.',
];

const STAGES = [
  { n: '01', name: 'Script', body: 'Paste narration, a transcript, or an article.' },
  { n: '02', name: 'Understand', body: 'Split into scenes with timecodes and read what each beat is about.' },
  { n: '03', name: 'Find', body: 'Query Wikimedia, Pexels, Unsplash and brand sources concurrently.' },
  { n: '04', name: 'Rank', body: 'Score every candidate 0–100 on four explainable factors.' },
  { n: '05', name: 'Build', body: 'Assemble a scene-by-scene board and export it as CSV or JSON.' },
];

const CAPABILITIES = [
  {
    k: 'Scene segmentation',
    v: 'Narration is broken into ordered scenes, each with a start and end timecode.',
  },
  {
    k: 'Visual intent',
    v: 'Each scene is classified into one of 16 intents — product UI, logo, diagram, location, data visualisation and so on — which decides how it is searched for.',
  },
  {
    k: 'Concurrent sourcing',
    v: 'Providers are queried in parallel and isolated: one failing source degrades the result set, it does not fail the run.',
  },
  {
    k: 'Explainable scoring',
    v: 'Query match, visual type, source quality and scene context each contribute a fixed share of the 0–100 score. The breakdown is shown on every card.',
  },
  {
    k: 'Licence capture',
    v: 'Whatever the source publishes about licensing is recorded and displayed verbatim, with a link back to the source page.',
  },
  {
    k: 'Export',
    v: 'The whole board — every scene, requirement and discovered asset — exports to CSV or JSON.',
  },
];

export default function LandingPage() {
  const router = useRouter();
  const [demoState, setDemoState] = useState<'idle' | 'loading'>('idle');
  const [error, setError] = useState<string | null>(null);

  const runSample = async () => {
    setDemoState('loading');
    setError(null);
    try {
      const project = await api.createDemoProject();
      router.push(`/projects/${project.id}?autostart=1`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not start the sample run.');
      setDemoState('idle');
    }
  };

  return (
    <div className="pb-24">
      {/* ── Hero: asymmetric, left-aligned, no centred gradient headline ────── */}
      <section className="grid gap-10 border-b border-line py-14 lg:grid-cols-12 lg:gap-12 lg:py-20">
        <div className="lg:col-span-5">
          <p className="eyebrow">Visual research for editors</p>

          <h1 className="mt-5 text-4xl font-semibold leading-[1.05] tracking-tight text-bone sm:text-5xl">
            Turn a script into
            <br />a visual plan.
          </h1>

          <p className="mt-6 max-w-md text-[0.95rem] leading-relaxed text-muted">
            SLAYERS reads your narration, works out what each moment needs to show,
            searches real sources for it, ranks what comes back, and lays the whole
            thing out as a board you can work from.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/projects/new" className="btn-primary">
              Start with a script
            </Link>
            <a href="#how" className="btn-ghost">
              See how it works
            </a>
          </div>

          <div className="mt-6 border-t border-lineSoft pt-6">
            <button
              type="button"
              onClick={runSample}
              disabled={demoState === 'loading'}
              className="font-mono text-label uppercase text-ochre underline underline-offset-4 transition-colors hover:text-bone disabled:opacity-50"
            >
              {demoState === 'loading'
                ? 'Starting sample run…'
                : 'Or run the built-in sample script →'}
            </button>
            <p className="mt-2 font-mono text-micro uppercase text-faint">
              Runs the real pipeline against live sources
            </p>
          </div>

          {error && (
            <div className="mt-5 max-w-md">
              <ErrorNotice message={error} onRetry={runSample} />
            </div>
          )}
        </div>

        {/* Product representation: script → requirement → ranked candidates. */}
        <div className="lg:col-span-7">
          <figure className="panel">
            <figcaption className="flex items-center justify-between border-b border-line px-4 py-2.5">
              <span className="eyebrow">Example board layout</span>
              <span className="font-mono text-micro uppercase text-faint">Scene 03</span>
            </figcaption>

            <div className="grid divide-y divide-lineSoft md:grid-cols-3 md:divide-x md:divide-y-0">
              {/* 1 — the script */}
              <div className="p-4">
                <p className="eyebrow">Narration</p>
                <ol className="mt-3 space-y-2">
                  {EXAMPLE_LINES.map((line, i) => (
                    <li
                      key={line}
                      className={`border-l-2 pl-3 text-xs leading-relaxed ${
                        i === 2
                          ? 'border-ochre text-bone'
                          : 'border-lineSoft text-faint'
                      }`}
                    >
                      {line}
                    </li>
                  ))}
                </ol>
              </div>

              {/* 2 — what the engine decided */}
              <div className="space-y-4 p-4">
                <div>
                  <p className="eyebrow">Visual intent</p>
                  <p className="mt-2 inline-block border border-ochre/50 bg-ochre-wash px-2 py-1 font-mono text-label uppercase text-ochre">
                    Product UI
                  </p>
                </div>
                <div>
                  <p className="eyebrow">Search query</p>
                  <p className="mt-2 font-mono text-xs text-bone">ide ai pair programmer editor</p>
                </div>
                <div>
                  <p className="eyebrow">Timecode</p>
                  <p className="mt-2 font-mono text-xs text-bone">00:16 – 00:24</p>
                </div>
              </div>

              {/* 3 — ranked candidates (structure only, no invented artwork) */}
              <div className="p-4">
                <p className="eyebrow">Ranked candidates</p>
                <ul className="mt-3 space-y-2.5">
                  {[
                    { score: 92, label: 'Recommended', src: 'Wikimedia Commons', tone: 'text-sage' },
                    { score: 74, label: 'Alternative', src: 'Pexels', tone: 'text-slate' },
                    { score: 43, label: 'Flagged', src: 'Brand source', tone: 'text-rust' },
                  ].map((c) => (
                    <li key={c.score} className="border border-lineSoft">
                      <div className="flex items-stretch">
                        <div
                          aria-hidden="true"
                          className="flex h-12 w-16 shrink-0 items-center justify-center border-r border-lineSoft bg-raised font-mono text-micro text-faint"
                        >
                          IMG
                        </div>
                        <div className="flex min-w-0 flex-1 items-center justify-between px-3">
                          <div className="min-w-0">
                            <p className={`font-mono text-label ${c.tone}`}>{c.label}</p>
                            <p className="truncate font-mono text-micro uppercase text-faint">
                              {c.src}
                            </p>
                          </div>
                          <span className={`font-mono text-sm ${c.tone}`}>{c.score}</span>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <p className="border-t border-line px-4 py-2.5 font-mono text-micro uppercase text-faint">
              Illustration of the board structure — run a script to see real results
            </p>
          </figure>
        </div>
      </section>

      {/* ── Pipeline rail ───────────────────────────────────────────────────── */}
      <section id="how" className="scroll-mt-20 border-b border-line py-14">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-xl font-semibold tracking-tight text-bone">
            What happens to your script
          </h2>
          <p className="font-mono text-micro uppercase text-faint">Five stages, one pass</p>
        </div>

        <ol className="mt-8 grid gap-px border border-line bg-line sm:grid-cols-2 lg:grid-cols-5">
          {STAGES.map((s) => (
            <li key={s.n} className="bg-panel p-5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-label text-ochre">{s.n}</span>
                <span aria-hidden="true" className="h-px flex-1 bg-line" />
              </div>
              <h3 className="mt-3 font-mono text-label uppercase text-bone">{s.name}</h3>
              <p className="mt-2 text-xs leading-relaxed text-muted">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ── Capability spec sheet (definition list, not feature cards) ──────── */}
      <section className="py-14">
        <h2 className="text-xl font-semibold tracking-tight text-bone">
          What the engine actually does
        </h2>

        <dl className="mt-8 divide-y divide-lineSoft border-y border-line">
          {CAPABILITIES.map((c) => (
            <div key={c.k} className="grid gap-1 py-4 sm:grid-cols-12 sm:gap-6">
              <dt className="font-mono text-label uppercase text-bone sm:col-span-3">{c.k}</dt>
              <dd className="text-sm leading-relaxed text-muted sm:col-span-9">{c.v}</dd>
            </div>
          ))}
        </dl>

        <div className="mt-10 flex flex-wrap items-center gap-4">
          <Link href="/projects/new" className="btn-primary">
            Start with a script
          </Link>
          <Link href="/projects" className="btn-ghost">
            Open existing boards
          </Link>
        </div>
      </section>
    </div>
  );
}
