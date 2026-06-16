import type { ProjectResponse, CreateProjectRequest } from '@/types/project';
import apiClient from './client';

export async function createProject(name: string, description?: string): Promise<ProjectResponse> {
  const body: CreateProjectRequest = { name, ...(description ? { description } : {}) };
  const res = await apiClient.post<ProjectResponse>('/api/projects', body);
  return res.data;
}

export async function listProjects(): Promise<ProjectResponse[]> {
  const res = await apiClient.get<ProjectResponse[]>('/api/projects');
  return res.data;
}
