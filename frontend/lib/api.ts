import { Project, ProcessingJob, ProjectSummary, ContentSegment, AssetRequirement, Asset } from '@/types';

function getApiBaseUrl(): string {
  // Check browser environment variable or fallback to localhost
  let url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  url = url.trim().replace(/\/+$/, ''); // Remove any trailing slashes
  if (!url.endsWith('/api')) {
    url = `${url}/api`;
  }
  return url;
}

const API_BASE_URL = getApiBaseUrl();

async function fetchJSON<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${getApiBaseUrl()}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error (${response.status}): ${errorText || response.statusText}`);
  }

  return response.json();
}

export const api = {
  createProject: (name: string, source_text: string, source_type: string = 'script'): Promise<Project> => {
    return fetchJSON<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, source_text, source_type }),
    });
  },

  createDemoProject: (): Promise<Project> => {
    return fetchJSON<Project>('/projects/demo', {
      method: 'POST',
    });
  },

  listProjects: (): Promise<Project[]> => {
    return fetchJSON<Project[]>('/projects');
  },

  getProject: (id: string): Promise<Project> => {
    return fetchJSON<Project>(`/projects/${id}`);
  },

  startProcessing: (id: string): Promise<ProcessingJob> => {
    return fetchJSON<ProcessingJob>(`/projects/${id}/process`, {
      method: 'POST',
    });
  },

  getProjectStatus: (id: string): Promise<ProcessingJob> => {
    return fetchJSON<ProcessingJob>(`/projects/${id}/status`);
  },

  getProjectSegments: (id: string): Promise<ContentSegment[]> => {
    return fetchJSON<ContentSegment[]>(`/projects/${id}/segments`);
  },

  getProjectRequirements: (id: string): Promise<AssetRequirement[]> => {
    return fetchJSON<AssetRequirement[]>(`/projects/${id}/requirements`);
  },

  getProjectAssets: (id: string): Promise<Asset[]> => {
    return fetchJSON<Asset[]>(`/projects/${id}/assets`);
  },

  getProjectSummary: (id: string): Promise<ProjectSummary> => {
    return fetchJSON<ProjectSummary>(`/projects/${id}/summary`);
  },

  getAsset: (id: string): Promise<Asset> => {
    return fetchJSON<Asset>(`/assets/${id}`);
  },
};
