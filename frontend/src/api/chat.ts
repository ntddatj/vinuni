import apiClient from './client';
import type { ChatThread, ChatMessage, SendMessageResponse } from '@/types/chat';

export async function listThreads(projectId: string): Promise<ChatThread[]> {
  const { data } = await apiClient.get<ChatThread[]>('/api/chat/threads', {
    params: { projectId },
  });
  return data;
}

export async function createThread(projectId: string, title?: string): Promise<ChatThread> {
  const { data } = await apiClient.post<ChatThread>('/api/chat/threads', {
    projectId,
    title: title ?? 'Cuộc trò chuyện mới',
  });
  return data;
}

export async function renameThread(threadId: string, title: string): Promise<ChatThread> {
  const { data } = await apiClient.patch<ChatThread>(`/api/chat/threads/${threadId}`, {
    title,
  });
  return data;
}

export async function deleteThread(threadId: string): Promise<void> {
  await apiClient.delete(`/api/chat/threads/${threadId}`);
}

export async function getThreadMessages(threadId: string): Promise<ChatMessage[]> {
  const { data } = await apiClient.get<ChatMessage[]>(`/api/chat/threads/${threadId}/messages`);
  return data;
}

export async function sendMessage(threadId: string, message: string): Promise<SendMessageResponse> {
  const { data } = await apiClient.post<SendMessageResponse>(
    `/api/chat/threads/${threadId}/messages`,
    { message },
  );
  return data;
}

export interface Suggestion {
  label: string;
  actionKey: string;
}

export interface SuggestionsRequest {
  activeTab: string;
  documentCount: number;
  hasDraft: boolean;
}

export async function getSuggestions(payload: SuggestionsRequest): Promise<Suggestion[]> {
  const { data } = await apiClient.post<Suggestion[]>('/api/chat/suggestions', payload);
  return data;
}
