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
  
  getJobs: (projectId: string) =>
    apiRequest<any[]>(`/api/projects/${projectId}/jobs`),
};

// Health check API
export const healthApi = {
  check: () => apiRequest<any>('/api/health'),
};
