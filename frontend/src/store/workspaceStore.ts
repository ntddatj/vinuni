import { create } from 'zustand';

export type TabKey = 'library' | 'graph' | 'writing';

interface WorkspaceState {
  activeTab: TabKey;
  documentCount: number;
  isUploadModalOpen: boolean;
  pendingChatInput: string | null;

  setActiveTab: (tab: TabKey) => void;
  setDocumentCount: (count: number) => void;
  setUploadModalOpen: (open: boolean) => void;
  setPendingChatInput: (msg: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()((set) => ({
  activeTab: 'library',
  documentCount: 0,
  isUploadModalOpen: false,
  pendingChatInput: null,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setDocumentCount: (count) => set({ documentCount: count }),
  setUploadModalOpen: (open) => set({ isUploadModalOpen: open }),
  setPendingChatInput: (msg) => set({ pendingChatInput: msg }),
}));
