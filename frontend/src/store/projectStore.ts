import { create } from 'zustand';
import { Project, AudioFile, GeneratedImage, VideoOutput } from '../types';

interface ProjectState {
  projects: Project[];
  selectedProject: Project | null;
  audioFiles: AudioFile[];
  generatedImages: GeneratedImage[];
  videoOutputs: VideoOutput[];
  
  // Actions
  setProjects: (projects: Project[]) => void;
  setSelectedProject: (project: Project | null) => void;
  addProject: (project: Project) => void;
  updateProject: (projectId: string, updates: Partial<Project>) => void;
  deleteProject: (projectId: string) => void;
  
  setAudioFiles: (audioFiles: AudioFile[]) => void;
  addAudioFile: (audioFile: AudioFile) => void;
  
  setGeneratedImages: (images: GeneratedImage[]) => void;
  addGeneratedImage: (image: GeneratedImage) => void;
  
  setVideoOutputs: (videos: VideoOutput[]) => void;
  addVideoOutput: (video: VideoOutput) => void;
  
  // Computed
  getProjectById: (id: string) => Project | undefined;
  getProjectAudioFile: (projectId: string) => AudioFile | undefined;
  getProjectImages: (projectId: string) => GeneratedImage[];
  getProjectVideos: (projectId: string) => VideoOutput[];
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  selectedProject: null,
  audioFiles: [],
  generatedImages: [],
  videoOutputs: [],
  
  setProjects: (projects) => set({ projects }),
  setSelectedProject: (project) => set({ selectedProject: project }),
  
  addProject: (project) => set((state) => ({
    projects: [...state.projects, project]
  })),
  
  updateProject: (projectId, updates) => set((state) => ({
    projects: state.projects.map(p => 
      p.id === projectId ? { ...p, ...updates } : p
    ),
    selectedProject: state.selectedProject?.id === projectId 
      ? { ...state.selectedProject, ...updates }
      : state.selectedProject
  })),
  
  deleteProject: (projectId) => set((state) => ({
    projects: state.projects.filter(p => p.id !== projectId),
    selectedProject: state.selectedProject?.id === projectId 
      ? null 
      : state.selectedProject
  })),
  
  setAudioFiles: (audioFiles) => set({ audioFiles }),
  addAudioFile: (audioFile) => set((state) => ({
    audioFiles: [...state.audioFiles, audioFile]
  })),
  
  setGeneratedImages: (images) => set({ generatedImages: images }),
  addGeneratedImage: (image) => set((state) => ({
    generatedImages: [...state.generatedImages, image]
  })),
  
  setVideoOutputs: (videos) => set({ videoOutputs: videos }),
  addVideoOutput: (video) => set((state) => ({
    videoOutputs: [...state.videoOutputs, video]
  })),
  
  getProjectById: (id) => get().projects.find(p => p.id === id),
  getProjectAudioFile: (projectId) => get().audioFiles.find(a => a.project_id === projectId),
  getProjectImages: (projectId) => get().generatedImages.filter(i => i.project_id === projectId),
  getProjectVideos: (projectId) => get().videoOutputs.filter(v => v.project_id === projectId),
}));
