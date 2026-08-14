'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { Project, ProjectSummary } from '@/types';
import { api } from '@/lib/api';
import ProcessingView from '@/components/ProcessingView';
import SceneCard from '@/components/SceneCard';
import ProjectSummaryView from '@/components/ProjectSummary';
import { Loader2, ArrowLeft, RefreshCw, Play, Layers, AlertCircle } from 'lucide-react';
import Link from 'next/link';

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjectData = useCallback(async () => {
    try {
      setError(null);
      const proj = await api.getProject(projectId);
      setProject(proj);

      if (proj.status === 'processing' || (proj.processing_job && proj.processing_job.status === 'processing')) {
        setIsProcessing(true);
      } else {
        setIsProcessing(false);
        if (proj.status === 'completed') {
          const sum = await api.getProjectSummary(projectId);
          setSummary(sum);
        }
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to load project details.');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      loadProjectData();
    }
  }, [projectId, loadProjectData]);

  const handleExport = (format: 'json' | 'csv') => {
    if (!project) return;

    if (format === 'json') {
      const exportData = {
        project_name: project.name,
        source_type: project.source_type,
        source_text: project.source_text,
        exported_at: new Date().toISOString(),
        summary: summary,
        scenes: project.segments.map((seg) => ({
          scene_sequence: seg.sequence,
          start_time: seg.start_time,
          end_time: seg.end_time,
          visual_intent: seg.visual_intent,
          narration: seg.text,
          requirements: seg.requirements.map((req) => ({
            description: req.description,
            search_query: req.search_query,
            priority: req.priority,
            reason: req.reason,
            assets: req.assets.map((a) => ({
              title: a.title,
              relevance_score: a.relevance_score,
              status: a.status,
              source: a.source,
              source_url: a.source_url,
              asset_url: a.asset_url,
              thumbnail_url: a.thumbnail_url,
              license_info: a.license_info,
              usage_notes: a.usage_notes,
            })),
          })),
        })),
      };

      const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(exportData, null, 2))}`;
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', jsonString);
      downloadAnchor.setAttribute('download', `slayers_package_${project.id.slice(0, 8)}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } else {
      // Export ALL assets across all scenes and requirements to CSV
      const rows = [
        ['Scene', 'Start_Time', 'End_Time', 'Visual_Intent', 'Narration', 'Requirement', 'Priority', 'Asset_Title', 'Asset_Status', 'Match_Score', 'Source', 'License', 'Source_URL', 'Asset_URL']
      ];

      project.segments.forEach((seg) => {
        seg.requirements.forEach((req) => {
          if (req.assets.length === 0) {
            rows.push([
              `Scene ${seg.sequence}`,
              seg.start_time || '',
              seg.end_time || '',
              seg.visual_intent || '',
              seg.text,
              req.description,
              req.priority,
              'No assets discovered',
              '',
              '',
              '',
              '',
              '',
              '',
            ]);
          } else {
            req.assets.forEach((asset) => {
              rows.push([
                `Scene ${seg.sequence}`,
                seg.start_time || '',
                seg.end_time || '',
                seg.visual_intent || '',
                seg.text,
                req.description,
                req.priority,
                asset.title,
                asset.status,
                String(asset.relevance_score),
                asset.source,
                asset.license_info,
                asset.source_url,
                asset.asset_url,
              ]);
            });
          }
        });
      });

      const csvContent = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `slayers_package_manifest_${project.id.slice(0, 8)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    }
  };

  const handleStartProcessing = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      await api.startProcessing(projectId);
      setIsProcessing(true);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to start processing.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-3">
        <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
        <p className="text-sm text-gray-400">Loading project detail...</p>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="py-16 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">{error || 'Project Not Found'}</h2>
        <Link href="/projects" className="inline-block text-sm text-blue-400 hover:underline">
          &larr; Return to Projects List
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 py-4">
      {/* Navigation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <Link
            href="/projects"
            className="p-2 rounded-lg bg-surface border border-surfaceBorder hover:bg-surfaceBorder text-gray-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 block">
              VISUAL ASSET PACKAGE
            </span>
            <h1 className="text-2xl font-extrabold text-white">{project.name}</h1>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {project.status === 'draft' ? (
            <button
              onClick={handleStartProcessing}
              className="flex items-center space-x-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 px-4 py-2.5 rounded-xl shadow-lg shadow-blue-600/30 transition active:scale-95"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Start Discovery Pipeline</span>
            </button>
          ) : (
            <button
              onClick={handleStartProcessing}
              className="flex items-center space-x-2 text-xs font-semibold text-gray-300 bg-surface border border-surfaceBorder hover:bg-surfaceBorder px-3.5 py-2 rounded-xl transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Re-run Pipeline</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {isProcessing ? (
        <ProcessingView
          projectId={projectId}
          onCompleted={() => {
            setIsProcessing(false);
            loadProjectData();
          }}
        />
      ) : project.status === 'draft' ? (
        <div className="bg-surface border border-surfaceBorder rounded-2xl p-12 text-center space-y-4 max-w-2xl mx-auto my-8">
          <Layers className="w-12 h-12 text-blue-400 mx-auto" />
          <h3 className="text-xl font-bold text-white">Project Ready for Analysis</h3>
          <p className="text-sm text-gray-400">
            Your script has been saved. Click below to analyze scenes, extract visual intents, and discover matching assets across providers.
          </p>
          <button
            onClick={handleStartProcessing}
            className="inline-flex items-center space-x-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-xl shadow-xl shadow-blue-600/25 transition active:scale-95"
          >
            <Play className="w-4 h-4" />
            <span>Build Visual Package Now</span>
          </button>
        </div>
      ) : (
        <div className="space-y-10">
          {/* Summary Header */}
          {summary && <ProjectSummaryView summary={summary} onExport={handleExport} />}

          {/* Interactive Scene Cards / Asset Board */}
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-surfaceBorder pb-4">
              <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                <Layers className="w-5 h-5 text-blue-400" />
                <span>Visual Asset Board ({project.segments.length} Scenes)</span>
              </h2>
            </div>

            {project.segments.length === 0 ? (
              <div className="bg-surface border border-surfaceBorder rounded-2xl p-12 text-center space-y-3">
                <AlertCircle className="w-10 h-10 text-gray-500 mx-auto" />
                <h3 className="text-lg font-bold text-white">No Scenes Generated</h3>
                <p className="text-xs text-gray-400">Try re-running the pipeline or checking the script format.</p>
              </div>
            ) : (
              <div className="space-y-8">
                {project.segments.map((segment) => (
                  <SceneCard key={segment.id} segment={segment} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
