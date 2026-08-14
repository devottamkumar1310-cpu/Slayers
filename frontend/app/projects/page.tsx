'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Project } from '@/types';
import { api } from '@/lib/api';
import { Layers, PlusCircle, ArrowRight, Clock, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';

export default function ProjectsListPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listProjects()
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Visual Asset Projects</h1>
          <p className="text-sm text-gray-400">All your analyzed scripts and organized visual packages.</p>
        </div>

        <Link
          href="/projects/new"
          className="inline-flex items-center space-x-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 px-4 py-2.5 rounded-xl shadow-lg shadow-blue-600/25 transition active:scale-95"
        >
          <PlusCircle className="w-4 h-4" />
          <span>New Project</span>
        </Link>
      </div>

      {loading ? (
        <div className="py-20 text-center space-y-3">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
          <p className="text-sm text-gray-400">Loading projects...</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-surface border border-surfaceBorder rounded-2xl p-12 text-center space-y-4">
          <Layers className="w-12 h-12 text-gray-600 mx-auto" />
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white">No Projects Found</h3>
            <p className="text-sm text-gray-400">Get started by creating your first visual asset package project.</p>
          </div>
          <Link
            href="/projects/new"
            className="inline-flex items-center space-x-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-xl transition"
          >
            <span>Create Visual Package</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="bg-surface border border-surfaceBorder hover:border-gray-600 rounded-2xl p-6 transition space-y-4 flex flex-col justify-between group"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded border border-blue-500/20">
                    {project.source_type}
                  </span>
                  {project.status === 'completed' ? (
                    <span className="inline-flex items-center space-x-1 text-[11px] font-medium text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Ready</span>
                    </span>
                  ) : project.status === 'processing' ? (
                    <span className="inline-flex items-center space-x-1 text-[11px] font-medium text-blue-400">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Processing</span>
                    </span>
                  ) : (
                    <span className="text-[11px] text-gray-500 uppercase">{project.status}</span>
                  )}
                </div>

                <h3 className="text-lg font-bold text-white group-hover:text-blue-300 transition line-clamp-2">
                  {project.name}
                </h3>

                <p className="text-xs text-gray-400 line-clamp-3 italic">
                  &ldquo;{project.source_text}&rdquo;
                </p>
              </div>

              <div className="pt-4 border-t border-surfaceBorder/80 flex items-center justify-between text-xs text-gray-500">
                <span className="flex items-center space-x-1 font-mono">
                  <Clock className="w-3 h-3 text-gray-600" />
                  <span>{new Date(project.created_at).toLocaleDateString()}</span>
                </span>

                <span className="text-blue-400 font-semibold group-hover:translate-x-1 transition-transform flex items-center space-x-1">
                  <span>View Package</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
