import { AudioFile } from "../types";

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }

  return response.json();
}

// Projects API
export const projectsApi = {
  getAll: () => apiRequest<any[]>('/api/projects'),
  
  getById: (id: string) => apiRequest<any>(`/api/projects/${id}`),
  
  create: (data: { name: string }) => 
    apiRequest<any>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  update: (id: string, data: Partial<any>) =>
    apiRequest<any>(`/api/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: (id: string) =>
    apiRequest(`/api/projects/${id}`, {
      method: 'DELETE',
    }),
  
    // Audio file methods
  uploadAudio: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    return fetch(`${API_BASE_URL}/api/projects/${projectId}/audio`, {
      method: 'POST',
      body: formData,
    }).then(response => {
      if (!response.ok) {
        throw new ApiError(response.status, 'Upload failed');
      }
      return response.json();
    });
  },

  getAudioFiles: (projectId: string) =>
    apiRequest<AudioFile[]>(`/api/projects/${projectId}/audio`),

  removeAudioFile: (projectId: string, fileId: string) =>
    apiRequest(`/api/projects/${projectId}/audio/${fileId}`, {
      method: 'DELETE',
    }),
  
  generateImage: (projectId: string, prompt: any) =>
    apiRequest<any>(`/api/projects/${projectId}/generate-image`, {
      method: 'POST',
      body: JSON.stringify(prompt),
    }),
  
  composeVideo: (projectId: string, settings: any) =>
    apiRequest<any>(`/api/projects/${projectId}/compose-video`, {
      method: 'POST',
      body: JSON.stringify(settings),
    }),
  
  generateImagePreview: (projectId: string, prompt: any) =>
    apiRequest<{
      task_id: string;
      preview_url: string;
      prompt: string;
      service: string;
      status: string;
    }>(`/api/projects/${projectId}/generate-image-preview`, {
      method: 'POST',
      body: JSON.stringify(prompt),
    }),
  
  // New: Batch image generation
  generateImageBatchPreview: (projectId: string, promptData: any, numImages: number) =>
    apiRequest<Array<{
      task_id: string;
      preview_url: string;
      prompt: string;
      service: string;
      status: string;
    }>>(`/api/projects/${projectId}/generate-image-batch-preview`, {
      method: 'POST',
      body: JSON.stringify({
        prompt: promptData,
        num_images: numImages
      }),
    }),

  approveImage: (projectId: string, previewId: string) =>
    apiRequest<any>(`/api/projects/${projectId}/approve-image`, {
      method: 'POST',
      body: JSON.stringify({ preview_id: previewId }),
    }),

  deletePreviewImage: (projectId: string, previewId: string) =>
    apiRequest(`/api/projects/${projectId}/reject-image`, {
      method: 'POST',
      body: JSON.stringify({ preview_id: previewId }),
    }),

  removeImage: (projectId: string, imageId: string) =>
    apiRequest(`/api/projects/${projectId}/images/${imageId}`, {
      method: 'DELETE',
    }), 
  
  getImages: (projectId: string) =>
    apiRequest<any[]>(`/api/projects/${projectId}/images`),
  
  getVideos: (projectId: string) =>
    apiRequest<any[]>(`/api/projects/${projectId}/videos`),

  cleanupOrphanedImages: (projectId: string) =>
    apiRequest<{
      message: string;
      orphaned_removed: number;
      valid_remaining: number;
      orphaned_details: string[];
    }>(`/api/projects/${projectId}/cleanup-orphaned-images`, {
      method: 'POST',
    }),

  // Enhanced video composition that automatically detects multi-audio
  composeVideoEnhanced: (projectId: string, settings: {
    resolution: string;
    fps: number;
    transition_duration: number;
    transition_type: string;
    add_ken_burns: boolean;
    image_distribution?: string; // New setting for multi-audio
  }) =>
    apiRequest<{
      message: string;
      task_id: string;
      job_id: string;
      status: string;
      settings: any;
    }>(`/api/projects/${projectId}/compose-video-enhanced`, {
      method: 'POST',
      body: JSON.stringify(settings),
    }),

  // Get audio composition info
  getAudioCompositionInfo: (projectId: string) =>
    apiRequest<{
      file_count: number;
      total_duration: number;
      files: Array<{
        index: number;
        filename: string;
        duration: number;
        start_time: number;
        end_time: number;
        size: number;
      }>;
      preview: {
        estimated_video_length: string;
        combination_method: string;
        transition_type: string;
      };
    }>(`/api/projects/${projectId}/audio-composition-info`),

  // Get video composition status
  getVideoStatus: (projectId: string, taskId: string) =>
    apiRequest<{
      status: 'pending' | 'progress' | 'success' | 'failed';
      progress: number;
      message?: string;
      result?: any;
      error?: string;
    }>(`/api/projects/${projectId}/video-status/${taskId}`),

  // Cancel video composition
  cancelVideoComposition: (projectId: string, taskId: string) =>
    apiRequest<{
      message: string;
      task_id: string;
      status: string;
    }>(`/api/projects/${projectId}/cancel-video/${taskId}`, {
      method: 'POST',
    }),

  // Multi-audio specific video composition
  composeVideoMultiAudio: (projectId: string, settings: {
    resolution: string;
    fps: number;
    transition_duration: number;
    transition_type: string;
    add_ken_burns: boolean;
    image_distribution: string;
  }) =>
    apiRequest<{
      message: string;
      task_id: string;
      job_id: string;
      status: string;
      audio_info: {
        file_count: number;
        total_duration: number;
        individual_files: string[];
      };
    }>(`/api/projects/${projectId}/compose-video-multi-audio`, {
      method: 'POST',
      body: JSON.stringify(settings),
    }),

  // Get video preview/details
  getVideoPreview: (projectId: string, videoId: string) =>
    apiRequest<{
      id: string;
      project_id: string;
      video_url: string;
      file_path: string;
      duration_seconds: number;
      resolution: string;
      file_size_bytes: number;
      status: string;
      youtube_video_id?: string;
      created_at: string;
      download_url: string;
    }>(`/api/projects/${projectId}/video-preview/${videoId}`),

  // FFmpeg-specific video composition
  composeVideoFFmpeg: (projectId: string, settings: any) =>
    apiRequest<{
      message: string;
      task_id: string;
      job_id: string;
      status: string;
    }>(`/api/projects/${projectId}/compose-video-ffmpeg`, {
      method: 'POST',
      body: JSON.stringify(settings),
    }),
  
  getJobs: (projectId: string) =>
    apiRequest<any[]>(`/api/projects/${projectId}/jobs`),
};

// Health check API
export const healthApi = {
  check: () => apiRequest<any>('/api/health'),
};
