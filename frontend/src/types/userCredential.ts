export interface ApiKeyStatus {
  provider: 'gemini';
  maskedKey: string | null;
  isValid: boolean | null;
  lastTestedAt: string | null;
}

export interface SaveApiKeyPayload {
  apiKey: string;
}

export interface TestApiKeyResult {
  status: 'connected' | 'failed';
  errorCode?: 'timeout' | 'connection_failed';
}
