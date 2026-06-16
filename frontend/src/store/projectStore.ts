import { create } from 'zustand';
import type { ProjectResponse } from '@/types/project';

interface ProjectState {
  projects: ProjectResponse[];
  isLoading: boolean;
  activeProjectId: string | null;
  setProjects: (projects: ProjectResponse[]) => void;
  addProject: (project: ProjectResponse) => void;
  removeProject: (id: string) => void;
  updateProject: (project: ProjectResponse) => void;
  setLoading: (loading: boolean) => void;
  setActiveProjectId: (id: string | null) => void;
}

export const useProjectStore = create<ProjectState>()((set) => ({
  projects: [],
  isLoading: false,
  activeProjectId: null,
  setProjects: (projects) => set({ projects }),
  addProject: (project) =>
    set((s) => ({
      projects: [project, ...s.projects].slice(0, 10),
    })),
  removeProject: (id) =>
    set((s) => ({
      projects: s.projects.filter((p) => p.id !== id),
    })),
  updateProject: (updated) =>
    set((s) => ({
      projects: s.projects.map((p) => (p.id === updated.id ? updated : p)),
    })),
  setLoading: (isLoading) => set({ isLoading }),
  setActiveProjectId: (id) => set({ activeProjectId: id }),
}));
