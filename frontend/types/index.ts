/**
 * Types mirroring backend/app/schemas/schemas.py exactly.
 * Field names here MUST match the FastAPI response models — the backend
 * contract is frozen, so any drift is a frontend bug.
 */

/** AssetResponse */
export interface Asset {
  id: string;
  requirement_id: string;
  title: string;
  source: string;
  source_url: string;
  asset_url: string;
  thumbnail_url?: string | null;
  asset_type: string;
  /** 0–100, deterministic score from relevance_scorer.py */
  relevance_score: number;
  license_info: string;
  license_url?: string | null;
  /** Human-readable scoring rationale, includes the raw breakdown string. */
  usage_notes?: string | null;
  /** public_domain | cc_licensed | provider_license | verify_manually */
  usage_status: UsageStatus | string;
  /** recommended (>=80) | alternative (>=55) | flagged (<55) */
  status: AssetStatus | string;
  provider_id?: string | null;
  metadata_json?: Record<string, unknown> | null;
}

export type UsageStatus =
  | 'public_domain'
  | 'cc_licensed'
  | 'provider_license'
  | 'verify_manually';

export type AssetStatus = 'recommended' | 'alternative' | 'flagged';

/** AssetRequirementResponse */
export interface AssetRequirement {
  id: string;
  segment_id: string;
  asset_type: string;
  description: string;
  search_query: string;
  priority: 'high' | 'medium' | 'low' | string;
  reason?: string | null;
  assets: Asset[];
}

/** ContentSegmentResponse */
export interface ContentSegment {
  id: string;
  project_id: string;
  sequence: number;
  start_time?: string | null;
  end_time?: string | null;
  text: string;
  scene_description?: string | null;
  visual_intent?: string | null;
  importance: 'high' | 'medium' | 'low' | string;
  requirements: AssetRequirement[];
}

/** ProcessingJobStatus */
export interface ProcessingJob {
  id: string;
  project_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  current_step: string;
  progress: number;
  error?: string | null;
  /** Provider-level warnings collected during discovery (partial failures). */
  warnings?: string[] | null;
  /** provider name → number of accepted candidates */
  provider_stats?: Record<string, number> | null;
  started_at?: string | null;
  completed_at?: string | null;
}

/** ProjectResponse */
export interface Project {
  id: string;
  name: string;
  source_type: string;
  source_text: string;
  status: 'draft' | 'processing' | 'completed' | 'failed' | string;
  created_at: string;
  updated_at: string;
  segments: ContentSegment[];
  processing_job?: ProcessingJob | null;
}

/** ProjectSummaryResponse */
export interface ProjectSummary {
  project_id: string;
  total_scenes: number;
  total_requirements: number;
  total_assets: number;
  /** count of assets with relevance_score >= 80 */
  high_confidence_matches: number;
  /** count of assets flagged OR usage_status === 'verify_manually' */
  needs_review: number;
  total_sources: number;
  /** source name → asset count */
  provider_breakdown: Record<string, number>;
  /** measured wall-clock pipeline duration */
  actual_processing_seconds: number;
  /** heuristic: 5 min per requirement — an estimate, not a measurement */
  manual_estimate_minutes: number;
}

export type SourceType = 'script' | 'transcript' | 'text';
