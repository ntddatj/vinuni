import { create } from 'zustand';

export type TabKey = 'library' | 'graph' | 'writing';

interface WorkspaceState {
  activeTab: TabKey;
  documentCount: number;
  isUploadModalOpen: boolean;

  setActiveTab: (tab: TabKey) => void;
  setDocumentCount: (count: number) => void;
  setUploadModalOpen: (open: boolean) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()((set) => ({
  activeTab: 'library',
  documentCount: 0,
  isUploadModalOpen: false,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setDocumentCount: (count) => set({ documentCount: count }),
  setUploadModalOpen: (open) => set({ isUploadModalOpen: open }),
}));
