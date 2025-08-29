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
