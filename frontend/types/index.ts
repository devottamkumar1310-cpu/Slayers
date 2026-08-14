export interface Asset {
  id: string;
  requirement_id: string;
  title: string;
  source: string;
  source_url: string;
  asset_url: string;
  thumbnail_url?: string;
  asset_type: 'image' | 'video' | 'logo' | 'screenshot' | string;
  relevance_score: number; // 0 to 100
  license_info: string;
  usage_notes?: string;
  status: 'recommended' | 'alternative' | 'flagged' | string;
  metadata_json?: Record<string, any>;
}

export interface AssetRequirement {
  id: string;
  segment_id: string;
  asset_type: string;
  description: string;
  search_query: string;
  priority: 'high' | 'medium' | 'low';
  reason?: string;
  assets: Asset[];
}

export interface ContentSegment {
  id: string;
  project_id: string;
  sequence: number;
  start_time?: string;
  end_time?: string;
  text: string;
  scene_description?: string;
  visual_intent?: string;
  importance: 'high' | 'medium' | 'low';
  requirements: AssetRequirement[];
}

export interface ProcessingJob {
  id: string;
  project_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  current_step: string;
  progress: number; // 0 to 100
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface Project {
  id: string;
  name: string;
  source_type: string;
  source_text: string;
  status: 'draft' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  segments: ContentSegment[];
  processing_job?: ProcessingJob;
}

export interface ProjectSummary {
  project_id: string;
  total_scenes: number;
  total_requirements: number;
  total_assets: number;
  high_confidence_matches: number;
  total_sources: number;
  manual_review_items: number;
  estimated_manual_time_minutes: number;
  slayers_processing_time_seconds: number;
}
