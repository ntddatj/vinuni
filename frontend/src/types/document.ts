export interface UploadResponse {
  fileId: string;
  title: string;
  authors: string[];
  abstract: string;
  year: number | null;
}

export interface ConfirmRequest {
  fileId: string;
  title: string;
  authors: string[];
  abstract: string;
  year: number | null;
  projectId: string;
}

export interface ConfirmResponse {
  documentId: string;
  message: string;
}

export interface ProjectPaper {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  source: 'manual' | 'arxiv' | 'semantic_scholar';
  status: 'pending' | 'processing' | 'indexed' | 'failed';
  createdAt: string;
}

export interface SSETicketResponse {
  ticket: string;
}

export interface AddFromSearchRequest {
  projectId: string;
  title: string;
  authors: string[];
  abstract: string;
  year: number | null;
  doi: string | null;
  arxivId: string | null;
  url: string;
  pdfUrl: string | null;
  source: 'arxiv' | 'semantic_scholar';
}

export interface AddFromSearchResponse {
  documentId: string;
  message: string;
}
