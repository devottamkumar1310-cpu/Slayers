import type { Asset, UsageStatus } from '@/types';

/** Turns `product_ui` into `Product UI`. Acronyms stay upper-case. */
const ACRONYMS = new Set(['ui', 'ux', 'api', 'cta']);

export function humanizeIntent(value?: string | null, fallback = 'Stock Footage'): string {
  if (!value) return fallback;
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((w) => (ACRONYMS.has(w.toLowerCase()) ? w.toUpperCase() : w[0].toUpperCase() + w.slice(1)))
    .join(' ');
}

/**
 * The backend writes a deterministic breakdown into `usage_notes`, e.g.
 *   "Semantic=28/35, Type=25/25, Source=20/20, Context=12/20"
 * We parse it rather than invent factors. Returns null when absent so the UI
 * can simply omit the breakdown instead of showing made-up numbers.
 */
export interface ScoreFactor {
  label: string;
  value: number;
  max: number;
}

const BREAKDOWN_RE = /(Semantic|Type|Source|Context)\s*=\s*(\d+)\s*\/\s*(\d+)/g;

const FACTOR_LABELS: Record<string, string> = {
  Semantic: 'Query match',
  Type: 'Visual type',
  Source: 'Source quality',
  Context: 'Scene context',
};

export function parseScoreFactors(usageNotes?: string | null): ScoreFactor[] {
  if (!usageNotes) return [];
  const out: ScoreFactor[] = [];
  for (const m of usageNotes.matchAll(BREAKDOWN_RE)) {
    out.push({ label: FACTOR_LABELS[m[1]] ?? m[1], value: Number(m[2]), max: Number(m[3]) });
  }
  return out;
}

/** The prose part of usage_notes, with the machine breakdown stripped off. */
export function scoreRationale(usageNotes?: string | null): string {
  if (!usageNotes) return '';
  return usageNotes
    .replace(/(Semantic|Type|Source|Context)\s*=\s*\d+\s*\/\s*\d+[,\s]*/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

/**
 * Licence presentation. Wording is deliberately non-committal: the backend
 * records what the provider states, and we never upgrade that into a legal
 * clearance claim.
 */
export interface UsagePresentation {
  label: string;
  note: string;
  tone: 'ok' | 'review';
}

export function describeUsage(status: UsageStatus | string): UsagePresentation {
  switch (status) {
    case 'public_domain':
      return {
        label: 'Public domain',
        note: 'Source states no copyright restrictions. Confirm on the source page.',
        tone: 'ok',
      };
    case 'cc_licensed':
      return {
        label: 'Creative Commons',
        note: 'Attribution terms apply. Check the exact licence on the source page.',
        tone: 'ok',
      };
    case 'provider_license':
      return {
        label: 'Provider licence',
        note: 'Covered by the provider licence shown. Read the terms before publishing.',
        tone: 'ok',
      };
    case 'verify_manually':
    default:
      return {
        label: 'Verify licence',
        note: 'Usage terms were not established automatically. Verify before use.',
        tone: 'review',
      };
  }
}

export interface StatusPresentation {
  label: string;
  hint: string;
  /** tailwind text colour class */
  text: string;
  border: string;
}

export function describeStatus(status: string): StatusPresentation {
  switch (status) {
    case 'recommended':
      return {
        label: 'Recommended',
        hint: 'Scored 80 or above — strong match on query, type and scene context.',
        text: 'text-sage',
        border: 'border-sage/40',
      };
    case 'flagged':
      return {
        label: 'Flagged',
        hint: 'Scored under 55 — low-confidence match. Verify before use.',
        text: 'text-rust',
        border: 'border-rust/40',
      };
    case 'alternative':
    default:
      return {
        label: 'Alternative',
        hint: 'Scored 55–79 — usable backup for this requirement.',
        text: 'text-slate',
        border: 'border-line',
      };
  }
}

export function scoreTone(score: number): string {
  if (score >= 80) return 'text-sage';
  if (score >= 55) return 'text-bone';
  return 'text-rust';
}

/** Every asset attached to a segment, ordered highest score first. */
export function assetsForSegment(requirements: { assets: Asset[] }[]): Asset[] {
  return requirements
    .flatMap((r) => r.assets)
    .slice()
    .sort((a, b) => b.relevance_score - a.relevance_score);
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s ? `${m}m ${s}s` : `${m}m`;
}

export function formatMinutes(mins: number): string {
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export function formatDate(iso: string): string {
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' });
}
