'use client';

import Link from 'next/link';
import { Film, PlusCircle, Layers, Sparkles } from 'lucide-react';

export default function Navbar() {
  return (
    <header className="border-b border-surfaceBorder bg-surface/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-400 p-0.5 shadow-lg shadow-blue-500/20 group-hover:shadow-blue-500/40 transition">
            <div className="w-full h-full bg-background rounded-[10px] flex items-center justify-center">
              <Film className="w-5 h-5 text-blue-400 group-hover:scale-110 transition-transform" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-xl tracking-tight text-white">SLAYERS</span>
              <span className="bg-blue-500/10 border border-blue-500/30 text-blue-400 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full">
                Hackathon Build
              </span>
            </div>
            <p className="text-xs text-gray-400">Automated Visual Research & Asset Engine</p>
          </div>
        </Link>

        <nav className="flex items-center space-x-4">
          <Link
            href="/projects"
            className="flex items-center space-x-1.5 text-sm text-gray-300 hover:text-white px-3 py-2 rounded-lg hover:bg-surfaceBorder/50 transition"
          >
            <Layers className="w-4 h-4 text-gray-400" />
            <span>Projects</span>
          </Link>

          <Link
            href="/projects/new"
            className="flex items-center space-x-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg shadow-lg shadow-blue-600/25 transition active:scale-95"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Visual Package</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}
