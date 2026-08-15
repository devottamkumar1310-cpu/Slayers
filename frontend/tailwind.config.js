/** @type {import('tailwindcss').Config} */

/**
 * SLAYERS design system — "research desk".
 *
 * Deliberately NOT a dark-blue SaaS palette: the foundation is a warm-neutral
 * graphite, the only chromatic accent is ochre, and status colours are muted
 * (sage / rust) so that the discovered ASSET IMAGE is the brightest thing on
 * screen. Radii are near-square and there are no shadow tokens — separation
 * comes from hairline rules, the way a production tool separates panels.
 */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // ── Foundation (warm neutral graphite, no blue cast) ────────────────
        ink: '#0C0C0D',      // page
        panel: '#131315',    // panels / cards
        raised: '#1A1A1D',   // inputs, hovered rows
        line: '#26262A',     // hairline rules
        lineSoft: '#1E1E21', // quieter rules

        // ── Type ────────────────────────────────────────────────────────────
        // Contrast against ink / panel, measured: bone 16.5, muted 5.9,
        // faint 4.8 / 4.6 — all clear WCAG AA (4.5) for normal text, which
        // matters because `faint` carries every small uppercase label.
        bone: '#EDECE8',     // primary text
        muted: '#8E8E88',    // secondary text
        faint: '#7E7E79',    // tertiary labels

        // ── Single accent: ochre ────────────────────────────────────────────
        ochre: {
          DEFAULT: '#E0A33E',
          dim: '#B07F2C',
          wash: '#2A2113',
        },

        // ── Status (muted on purpose — must not out-shout the artwork) ───────
        sage: '#8FB573',     // recommended
        rust: '#CE7A45',     // flagged / verify
        slate: '#9DA3A8',    // alternative / neutral
      },
      fontFamily: {
        sans: [
          'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI',
          'Inter', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif',
        ],
        mono: [
          'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas',
          'Liberation Mono', 'monospace',
        ],
      },
      fontSize: {
        // Editorial label scale — small, uppercase, wide-tracked
        label: ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.09em' }],
        micro: ['0.625rem', { lineHeight: '0.875rem', letterSpacing: '0.12em' }],
      },
      borderRadius: {
        none: '0',
        DEFAULT: '2px',
        sm: '2px',
        md: '3px',
        lg: '4px',
        xl: '5px',
      },
      maxWidth: {
        desk: '96rem',
      },
    },
  },
  plugins: [],
};
