export interface ChatThread {
  id: string;
  userId: string;
  projectId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChatMessage {
  id: string;
  threadId: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  citationMap?: Record<string, string>; // ordinal → chunk UUID (frontend-only, không có trong API response)
}

export interface SendMessageResponse {
  runId: string;
}
