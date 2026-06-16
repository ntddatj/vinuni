import apiClient from './client';
import type { ApiKeyStatus, SaveApiKeyPayload, TestApiKeyResult } from '@/types/userCredential';

export async function getApiKeys(): Promise<ApiKeyStatus[]> {
  const res = await apiClient.get<ApiKeyStatus[]>('/api/user/api-keys');
  return res.data;
}

export async function saveApiKey(provider: string, payload: SaveApiKeyPayload): Promise<void> {
  await apiClient.put(`/api/user/api-keys/${provider}`, payload);
}

export async function deleteApiKey(provider: string): Promise<void> {
  await apiClient.delete(`/api/user/api-keys/${provider}`);
}

export async function testApiKey(provider: string): Promise<TestApiKeyResult> {
  const res = await apiClient.post<TestApiKeyResult>(`/api/user/api-keys/${provider}/test`);
  return res.data;
}
