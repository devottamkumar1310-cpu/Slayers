'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/projects', label: 'Boards' },
  { href: '/projects/new', label: 'New script' },
];

export default function Masthead() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-ink/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-desk items-stretch justify-between px-4 sm:px-6 lg:px-10">
        <Link
          href="/"
          className="group flex items-center gap-3 py-3.5"
          aria-label="SLAYERS home"
        >
          {/* Crop-mark glyph — a framing bracket, not a gradient chip. */}
          <span
            aria-hidden="true"
            className="relative block h-7 w-7 border border-faint transition-colors group-hover:border-ochre"
          >
            <span className="absolute left-1 top-1 h-1.5 w-1.5 border-l border-t border-ochre" />
            <span className="absolute bottom-1 right-1 h-1.5 w-1.5 border-b border-r border-ochre" />
          </span>

          <span className="flex flex-col leading-none">
            <span className="font-mono text-base font-semibold tracking-[0.22em] text-bone">
              SLAYERS
            </span>
            <span className="mt-1 hidden font-mono text-micro uppercase text-faint sm:block">
              Script → visual plan
            </span>
          </span>
        </Link>

        <nav aria-label="Primary" className="flex items-stretch">
          {NAV.map((item) => {
            const active =
              item.href === '/projects'
                ? pathname === '/projects' || /^\/projects\/(?!new$)/.test(pathname ?? '')
                : pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={`flex items-center border-b-2 px-3 font-mono text-label uppercase transition-colors sm:px-5 ${
                  active
                    ? 'border-ochre text-bone'
                    : 'border-transparent text-muted hover:text-bone'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
