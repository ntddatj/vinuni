import apiClient from './client';
import type { SearchResponse } from '@/types/search';

export async function searchPapers(query: string, limit = 10): Promise<SearchResponse> {
  const res = await apiClient.get<SearchResponse>('/api/search', {
    params: { q: query, limit },
  });
  return res.data;
}
