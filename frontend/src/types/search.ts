export interface PaperResult {
  title: string;
  authors: string[];
  year: number | null;
  abstract: string;
  doi: string | null;
  arxivId: string | null;
  url: string;
  pdfUrl: string | null;
  source: 'arxiv' | 'semantic_scholar';
}

export interface SearchResponse {
  results: PaperResult[];
  warnings: string[];
}
