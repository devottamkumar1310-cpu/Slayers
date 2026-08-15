import type { Project, ProjectSummary } from '@/types';

/**
 * Export builders.
 *
 * Both formats walk the FULL tree — every scene, every requirement, every
 * discovered asset — not just the top candidate. Requirements that returned
 * nothing still get a row, so the export reflects the real coverage of a run.
 */

function csvCell(value: unknown): string {
  const s = value === null || value === undefined ? '' : String(value);
  return `"${s.replace(/"/g, '""')}"`;
}

const CSV_HEADER = [
  'scene',
  'start_time',
  'end_time',
  'scene_importance',
  'narration',
  'requirement',
  'visual_intent',
  'priority',
  'search_query',
  'requirement_reason',
  'asset_title',
  'asset_status',
  'match_score',
  'asset_type',
  'source',
  'license_info',
  'license_url',
  'usage_status',
  'usage_notes',
  'source_url',
  'asset_url',
  'thumbnail_url',
];

export function buildCsv(project: Project): string {
  const rows: string[][] = [CSV_HEADER];

  for (const seg of project.segments ?? []) {
    const sceneCells = [
      String(seg.sequence),
      seg.start_time ?? '',
      seg.end_time ?? '',
      seg.importance ?? '',
      seg.text,
    ];

    if (!seg.requirements?.length) {
      rows.push([...sceneCells, ...Array(CSV_HEADER.length - sceneCells.length).fill('')]);
      continue;
    }

    for (const req of seg.requirements) {
      const reqCells = [
        req.description,
        req.asset_type,
        req.priority,
        req.search_query,
        req.reason ?? '',
      ];

      if (!req.assets?.length) {
        rows.push([
          ...sceneCells,
          ...reqCells,
          'NO ASSET FOUND',
          ...Array(CSV_HEADER.length - sceneCells.length - reqCells.length - 1).fill(''),
        ]);
        continue;
      }

      for (const a of req.assets) {
        rows.push([
          ...sceneCells,
          ...reqCells,
          a.title,
          a.status,
          String(a.relevance_score),
          a.asset_type,
          a.source,
          a.license_info,
          a.license_url ?? '',
          a.usage_status,
          a.usage_notes ?? '',
          a.source_url,
          a.asset_url,
          a.thumbnail_url ?? '',
        ]);
      }
    }
  }

  return rows.map((r) => r.map(csvCell).join(',')).join('\r\n');
}

export function buildJson(project: Project, summary: ProjectSummary | null): string {
  const payload = {
    exported_at: new Date().toISOString(),
    generator: 'SLAYERS',
    project: {
      id: project.id,
      name: project.name,
      source_type: project.source_type,
      status: project.status,
      created_at: project.created_at,
      source_text: project.source_text,
    },
    summary,
    processing_job: project.processing_job ?? null,
    scenes: (project.segments ?? []).map((seg) => ({
      sequence: seg.sequence,
      start_time: seg.start_time,
      end_time: seg.end_time,
      importance: seg.importance,
      visual_intent: seg.visual_intent,
      narration: seg.text,
      scene_description: seg.scene_description,
      requirements: (seg.requirements ?? []).map((req) => ({
        id: req.id,
        asset_type: req.asset_type,
        description: req.description,
        search_query: req.search_query,
        priority: req.priority,
        reason: req.reason,
        assets: (req.assets ?? []).map((a) => ({
          id: a.id,
          title: a.title,
          relevance_score: a.relevance_score,
          status: a.status,
          asset_type: a.asset_type,
          source: a.source,
          source_url: a.source_url,
          asset_url: a.asset_url,
          thumbnail_url: a.thumbnail_url,
          license_info: a.license_info,
          license_url: a.license_url,
          usage_status: a.usage_status,
          usage_notes: a.usage_notes,
          provider_id: a.provider_id,
        })),
      })),
    })),
  };

  return JSON.stringify(payload, null, 2);
}

function slugify(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 60) || 'slayers-board'
  );
}

/** Triggers a browser download and releases the object URL afterwards. */
export function downloadFile(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Give the browser a tick to start the download before revoking.
  setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

export function exportProject(
  project: Project,
  summary: ProjectSummary | null,
  format: 'csv' | 'json'
): void {
  const base = `slayers-${slugify(project.name)}`;
  if (format === 'csv') {
    // BOM so Excel reads UTF-8 correctly.
    downloadFile(`﻿${buildCsv(project)}`, `${base}.csv`, 'text/csv;charset=utf-8;');
  } else {
    downloadFile(buildJson(project, summary), `${base}.json`, 'application/json;charset=utf-8;');
  }
}
