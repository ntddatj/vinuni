import apiClient from './client';

export interface CitationDetail {
  title: string;
  text: string;
}

export async function getCitationDetail(citationId: string): Promise<CitationDetail> {
  const { data } = await apiClient.get<CitationDetail>(`/api/citations/${citationId}`);
  return data;
}
