import type { ProjectResponse, CreateProjectRequest, ProjectsListResponse } from '@/types/project';
import apiClient from './client';

export async function createProject(name: string, description?: string): Promise<ProjectResponse> {
  const body: CreateProjectRequest = { name, ...(description ? { description } : {}) };
  const res = await apiClient.post<ProjectResponse>('/api/projects', body);
  return res.data;
}

export async function getProjects(limit = 10, offset = 0, name?: string): Promise<ProjectsListResponse> {
  const res = await apiClient.get<ProjectsListResponse>('/api/projects', {
    params: { limit, offset, ...(name ? { name } : {}) },
  });
  return res.data;
}

export async function listProjects(limit = 10, offset = 0, name?: string): Promise<ProjectResponse[]> {
  const { items } = await getProjects(limit, offset, name);
  return items;
}

export async function updateProject(id: string, name: string, description?: string): Promise<ProjectResponse> {
  const res = await apiClient.patch<ProjectResponse>(`/api/projects/${id}`, { name, description });
  return res.data;
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/api/projects/${id}`);
}
