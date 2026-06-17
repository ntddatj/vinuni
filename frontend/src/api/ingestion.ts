import apiClient from '@/api/client';
import type {
  AddFromSearchRequest,
  AddFromSearchResponse,
  ConfirmRequest,
  ConfirmResponse,
  PatchPaperRequest,
  PatchPaperResponse,
  ProjectPaper,
  SSETicketResponse,
  UploadResponse,
} from '@/types/document';

export async function uploadDocument(file: File, projectId: string): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('project_id', projectId);
  const res = await apiClient.post<UploadResponse>('/api/ingestion/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function confirmMetadata(data: ConfirmRequest): Promise<ConfirmResponse> {
  const res = await apiClient.post<ConfirmResponse>('/api/ingestion/confirm', data);
  return res.data;
}

export async function getSSETicket(documentId: string): Promise<SSETicketResponse> {
  const res = await apiClient.post<SSETicketResponse>(`/api/ingestion/tasks/${documentId}/ticket`);
  return res.data;
}

export async function getPapersByProject(projectId: string): Promise<ProjectPaper[]> {
  const res = await apiClient.get<ProjectPaper[]>(`/api/projects/${projectId}/papers`);
  return res.data;
}

export async function addPaperFromSearch(
  data: AddFromSearchRequest,
): Promise<AddFromSearchResponse> {
  const res = await apiClient.post<AddFromSearchResponse>('/api/ingestion/from-search', data);
  return res.data;
}

export async function deletePaper(projectId: string, paperId: string): Promise<void> {
  await apiClient.delete(`/api/projects/${projectId}/papers/${paperId}`);
}

export async function patchPaperMetadata(
  projectId: string,
  paperId: string,
  data: PatchPaperRequest,
): Promise<PatchPaperResponse> {
  const res = await apiClient.patch<PatchPaperResponse>(
    `/api/projects/${projectId}/papers/${paperId}`,
    data,
  );
  return res.data;
}

export function getPaperFileUrl(projectId: string, paperId: string): string {
  return `/api/projects/${projectId}/papers/${paperId}/file`;
}
