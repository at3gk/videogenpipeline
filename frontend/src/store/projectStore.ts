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
  removeAudioFile: (audioFileId: string) => void;
  
  setGeneratedImages: (images: GeneratedImage[]) => void;
  addGeneratedImage: (image: GeneratedImage) => void;
  
  setVideoOutputs: (videos: VideoOutput[]) => void;
  addVideoOutput: (video: VideoOutput) => void;
  
  // Computed
  getProjectById: (id: string) => Project | undefined;
  getProjectAudioFiles: (projectId: string) => AudioFile[];
  getProjectImages: (projectId: string) => GeneratedImage[];
  getProjectVideos: (projectId: string) => VideoOutput[];
  
  // New computed properties for workflow logic
  hasAudioFiles: (projectId: string) => boolean;
  hasApprovedImages: (projectId: string) => boolean;
  getProjectStatus: (projectId: string) => 'setup' | 'generating' | 'ready' | 'completed';
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
      : state.selectedProject,
    // Also clean up related data
    audioFiles: state.audioFiles.filter(a => a.project_id !== projectId),
    generatedImages: state.generatedImages.filter(i => i.project_id !== projectId),
    videoOutputs: state.videoOutputs.filter(v => v.project_id !== projectId),
  })),
  
  setAudioFiles: (audioFiles) => set({ audioFiles }),
  addAudioFile: (audioFile) => set((state) => ({
    audioFiles: [...state.audioFiles.filter(a => a.id !== audioFile.id), audioFile]
  })),
  
  removeAudioFile: (audioFileId) => set((state) => ({
    audioFiles: state.audioFiles.filter(a => a.id !== audioFileId)
  })),
  
  setGeneratedImages: (images) => set({ generatedImages: images }),
  addGeneratedImage: (image) => set((state) => ({
    generatedImages: [...state.generatedImages, image]
  })),
  
  setVideoOutputs: (videos) => set({ videoOutputs: videos }),
  addVideoOutput: (video) => set((state) => ({
    videoOutputs: [...state.videoOutputs, video]
  })),
  
  // Computed getters
  getProjectById: (id) => get().projects.find(p => p.id === id),
  
  getProjectAudioFiles: (projectId) => 
    get().audioFiles.filter(a => a.project_id === projectId),
  
  getProjectImages: (projectId) => 
    get().generatedImages.filter(i => i.project_id === projectId),
  
  getProjectVideos: (projectId) => 
    get().videoOutputs.filter(v => v.project_id === projectId),
  
  // New workflow helpers
  hasAudioFiles: (projectId) => 
    get().audioFiles.some(a => a.project_id === projectId),
  
  hasApprovedImages: (projectId) => 
    get().generatedImages.some(i => i.project_id === projectId),
  
  getProjectStatus: (projectId) => {
    const state = get();
    const hasAudio = state.hasAudioFiles(projectId);
    const hasImages = state.hasApprovedImages(projectId);
    const hasVideos = state.videoOutputs.some(v => v.project_id === projectId);
    
    if (hasVideos) return 'completed';
    if (hasAudio && hasImages) return 'ready';
    if (hasAudio) return 'generating';
    return 'setup';
  }
}));