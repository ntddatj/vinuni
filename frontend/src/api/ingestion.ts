import apiClient from '@/api/client';
import type { ConfirmRequest, ConfirmResponse, UploadResponse } from '@/types/document';

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
