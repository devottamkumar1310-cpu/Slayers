import './globals.css';
import type { Metadata, Viewport } from 'next';
import Masthead from '@/components/Masthead';

export const metadata: Metadata = {
  title: 'SLAYERS — turn a script into a visual plan',
  description:
    'SLAYERS reads a script, works out what each moment needs to show, searches real sources, ranks what it finds, and builds a visual research board you can export.',
};

export const viewport: Viewport = {
  themeColor: '#0c0c0d',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col bg-ink text-bone antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:border focus:border-ochre focus:bg-ink focus:px-4 focus:py-2 focus:font-mono focus:text-label focus:uppercase"
        >
          Skip to content
        </a>

        <Masthead />

        <main id="main" className="mx-auto w-full max-w-desk flex-1 px-4 sm:px-6 lg:px-10">
          {children}
        </main>

        <footer className="border-t border-lineSoft">
          <div className="mx-auto flex w-full max-w-desk flex-col gap-2 px-4 py-6 font-mono text-micro uppercase text-faint sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-10">
            <span>SLAYERS — visual research &amp; asset sourcing</span>
            <span>
              Assets and licence terms are reported as published by each source. Verify before use.
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
