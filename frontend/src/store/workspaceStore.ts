import { create } from 'zustand';

export type TabKey = 'library' | 'graph' | 'gaps' | 'writing';
export type LibrarySubTab = 'documents' | 'search';

interface WorkspaceState {
  activeTab: TabKey;
  librarySubTab: LibrarySubTab;
  documentCount: number;
  isUploadModalOpen: boolean;
  pendingChatInput: string | null;
  gapFocusRequest: { paperId: string } | null;

  setActiveTab: (tab: TabKey) => void;
  setLibrarySubTab: (sub: LibrarySubTab) => void;
  setDocumentCount: (count: number) => void;
  setUploadModalOpen: (open: boolean) => void;
  setPendingChatInput: (msg: string | null) => void;
  requestGapFocus: (paperId: string) => void;
  clearGapFocus: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>()((set) => ({
  activeTab: 'library',
  librarySubTab: 'documents',
  documentCount: 0,
  isUploadModalOpen: false,
  pendingChatInput: null,
  gapFocusRequest: null,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setLibrarySubTab: (sub) => set({ librarySubTab: sub }),
  setDocumentCount: (count) => set({ documentCount: count }),
  setUploadModalOpen: (open) => set({ isUploadModalOpen: open }),
  setPendingChatInput: (msg) => set({ pendingChatInput: msg }),
  requestGapFocus: (paperId) => set({ gapFocusRequest: { paperId } }),
  clearGapFocus: () => set({ gapFocusRequest: null }),
}));
