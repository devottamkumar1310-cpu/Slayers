'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import ErrorNotice from '@/components/ErrorNotice';
import type { SourceType } from '@/types';

/** Mirrors ProjectCreate in backend/app/schemas/schemas.py. */
const MAX_CHARS = 20_000;
const MAX_NAME = 255;
/** Below this the analyser has too little to segment into scenes. */
const MIN_USEFUL_CHARS = 80;

const SOURCE_TYPES: { id: SourceType; label: string; blurb: string }[] = [
  { id: 'script', label: 'Script', blurb: 'Narration written to be read aloud' },
  { id: 'transcript', label: 'Transcript', blurb: 'Text captured from existing audio' },
  { id: 'text', label: 'Article', blurb: 'Prose you want to turn into video' },
];

const EXAMPLES: { title: string; type: SourceType; text: string }[] = [
  {
    title: 'How AI coding agents are changing software development',
    type: 'script',
    text: `The software industry is undergoing a massive shift as AI coding agents emerge.
Developers no longer spend hours writing boilerplate code manually.
Instead, intelligent agents analyze repositories, create implementation plans, and write multi-file features.
For example, modern IDE interfaces now feature AI pair-programmers integrated right into the editor window.
This transformation allows small engineering teams to build complex software in a fraction of the time.
Companies like GitHub, Google, and OpenAI are shipping AI tools that automate repetitive coding tasks.
The market data shows developer productivity increasing by 30 to 55 percent with AI-assisted workflows.`,
  },
  {
    title: 'The next generation of cloud architecture',
    type: 'script',
    text: `Today we are announcing a serverless cloud platform built for real-time applications.
Our new analytics dashboard processes millions of events per second with sub-millisecond latency.
Engineering teams can monitor global data pipelines and microservices as they run.
Here is a live look at the user dashboard interface showing global network metrics.
Behind it sits a distributed database that replicates across every major region.`,
  },
];

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [sourceType, setSourceType] = useState<SourceType>('script');
  const [sourceText, setSourceText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  const chars = sourceText.length;
  const words = useMemo(
    () => sourceText.trim().split(/\s+/).filter(Boolean).length,
    [sourceText]
  );
  const lines = useMemo(
    () => sourceText.split('\n').map((l) => l.trim()).filter(Boolean).length,
    [sourceText]
  );

  const overLimit = chars > MAX_CHARS;
  const tooShort = sourceText.trim().length > 0 && sourceText.trim().length < MIN_USEFUL_CHARS;
  const emptyScript = sourceText.trim().length === 0;
  const emptyName = name.trim().length === 0;

  const scriptProblem = overLimit
    ? `That is ${(chars - MAX_CHARS).toLocaleString()} characters over the ${MAX_CHARS.toLocaleString()} limit. Trim it or split it into two projects.`
    : emptyScript
      ? 'Paste the narration you want visuals for.'
      : tooShort
        ? `A little more text gives the analyser something to work with — around ${MIN_USEFUL_CHARS} characters is the practical minimum.`
        : null;

  const blocked = emptyName || emptyScript || overLimit;

  const submit = async () => {
    setTouched(true);
    if (blocked) return;

    setSubmitting(true);
    setError(null);
    try {
      const project = await api.createProject(name.trim(), sourceText, sourceType);
      await api.startProcessing(project.id);
      router.push(`/projects/${project.id}?autostart=1`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not start the run. Try again.'
      );
      setSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void submit();
  };

  const loadExample = (ex: (typeof EXAMPLES)[number]) => {
    setName(ex.title);
    setSourceType(ex.type);
    setSourceText(ex.text);
    setError(null);
    setTouched(false);
  };

  return (
    <div className="py-10">
      <div className="border-b border-line pb-6">
        <p className="eyebrow">New board</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-bone">
          Give SLAYERS a script
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          Every line becomes a scene. Every scene gets a visual intent, a search query,
          and a ranked set of real candidates. You will land on the board when the run
          finishes.
        </p>
      </div>

      <div className="grid gap-10 pt-8 lg:grid-cols-12 lg:gap-12">
        <form onSubmit={handleSubmit} noValidate className="space-y-8 lg:col-span-8">
          {/* Name */}
          <div>
            <label htmlFor="project-name" className="eyebrow block">
              Project name
            </label>
            <input
              id="project-name"
              type="text"
              value={name}
              maxLength={MAX_NAME}
              onChange={(e) => setName(e.target.value)}
              placeholder="AI coding agents — explainer"
              aria-invalid={touched && emptyName}
              aria-describedby={touched && emptyName ? 'name-error' : undefined}
              className={`field mt-2.5 ${touched && emptyName ? 'border-rust' : ''}`}
            />
            {touched && emptyName && (
              <p id="name-error" className="mt-2 text-xs text-rust">
                Give the board a name so you can find it again.
              </p>
            )}
          </div>

          {/* Source type */}
          <fieldset>
            <legend className="eyebrow">Source type</legend>
            <div className="mt-2.5 grid gap-px border border-line bg-line sm:grid-cols-3">
              {SOURCE_TYPES.map((t) => {
                const active = sourceType === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setSourceType(t.id)}
                    className={`p-3.5 text-left transition-colors ${
                      active ? 'bg-ochre-wash' : 'bg-panel hover:bg-raised'
                    }`}
                  >
                    <span
                      className={`font-mono text-label uppercase ${
                        active ? 'text-ochre' : 'text-bone'
                      }`}
                    >
                      {t.label}
                    </span>
                    <span className="mt-1 block text-xs leading-snug text-muted">{t.blurb}</span>
                  </button>
                );
              })}
            </div>
          </fieldset>

          {/* Script */}
          <div>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <label htmlFor="source-text" className="eyebrow">
                Narration
              </label>
              <p className="font-mono text-micro uppercase text-faint">
                <span className={overLimit ? 'text-rust' : 'text-muted'}>
                  {chars.toLocaleString()}
                </span>
                {' / '}
                {MAX_CHARS.toLocaleString()} chars · {words.toLocaleString()} words ·{' '}
                {lines.toLocaleString()} lines
              </p>
            </div>

            <textarea
              id="source-text"
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              onBlur={() => setTouched(true)}
              rows={16}
              placeholder={
                'One idea per line works best.\n\nThe software industry is undergoing a massive shift as AI coding agents emerge.\nDevelopers no longer spend hours writing boilerplate code manually.'
              }
              aria-invalid={touched && (emptyScript || overLimit)}
              aria-describedby="script-help"
              className={`field mt-2.5 resize-y font-mono text-[13px] leading-relaxed ${
                overLimit || (touched && emptyScript) ? 'border-rust' : ''
              }`}
            />

            <p
              id="script-help"
              className={`mt-2 text-xs leading-relaxed ${
                overLimit || (touched && emptyScript) ? 'text-rust' : 'text-muted'
              }`}
            >
              {scriptProblem ?? 'Each line is treated as a beat and gets its own timecode.'}
            </p>
          </div>

          {error && (
            <ErrorNotice
              message={error}
              onRetry={() => {
                setError(null);
                void submit();
              }}
            />
          )}

          <div className="flex flex-wrap items-center gap-4 border-t border-line pt-6">
            <button type="submit" disabled={submitting || blocked} className="btn-primary">
              {submitting ? 'Starting the run…' : 'Analyse & find visuals'}
            </button>
            <p className="font-mono text-micro uppercase text-faint">
              Runs scene analysis, provider search and ranking — usually under a minute
            </p>
          </div>
        </form>

        {/* Examples */}
        <aside className="lg:col-span-4">
          <div className="panel">
            <p className="border-b border-line px-4 py-2.5 eyebrow">Start from an example</p>
            <ul className="divide-y divide-lineSoft">
              {EXAMPLES.map((ex) => (
                <li key={ex.title}>
                  <button
                    type="button"
                    onClick={() => loadExample(ex)}
                    className="w-full p-4 text-left transition-colors hover:bg-raised"
                  >
                    <p className="text-sm font-medium leading-snug text-bone">{ex.title}</p>
                    <p className="mt-2 line-clamp-2 font-mono text-[11px] leading-relaxed text-faint">
                      {ex.text.split('\n')[0]}
                    </p>
                    <p className="mt-2.5 font-mono text-micro uppercase text-ochre">
                      Load this script →
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-6 border-l-2 border-line pl-4">
            <p className="eyebrow">Writing for better results</p>
            <ul className="mt-3 space-y-2.5 text-xs leading-relaxed text-muted">
              <li>Name concrete things — products, companies, places. Generic lines return generic stock.</li>
              <li>Keep one idea per line so scene boundaries land where you expect.</li>
              <li>Anything the engine cannot source confidently comes back flagged rather than hidden.</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
