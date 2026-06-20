import type { GraphResponse, GapResponse, SyncStatus } from '@/types/graph';
import apiClient from './client';

export async function fetchGraph(projectId: string): Promise<GraphResponse> {
  const res = await apiClient.get<GraphResponse>(`/api/projects/${projectId}/graph`);
  return res.data;
}

export async function expandNode(
  projectId: string,
  nodeId: string,
  existingIds: string[],
): Promise<GraphResponse> {
  const res = await apiClient.get<GraphResponse>(
    `/api/projects/${projectId}/graph/nodes/${nodeId}/expand`,
    { params: { existing_ids: existingIds.join(',') } },
  );
  return res.data;
}

export async function getSyncStatus(projectId: string): Promise<SyncStatus> {
  const res = await apiClient.get<SyncStatus>(`/api/projects/${projectId}/graph/sync-status`);
  return res.data;
}

export async function fetchGaps(projectId: string): Promise<GapResponse> {
  const res = await apiClient.get<GapResponse>(`/api/projects/${projectId}/graph/gaps`);
  return res.data;
}
