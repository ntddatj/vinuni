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
