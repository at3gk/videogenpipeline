export interface User {
  id: string;
  email: string;
  username: string;
  created_at: string;
}

export interface Project {
  id: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
  user_id: string;
}

export interface AudioFile {
  id: string;
  project_id: string;
  filename: string;
  file_path: string;
  duration_seconds?: number;
  file_size_bytes?: number;
  mime_type?: string;
  uploaded_at: string;
}

export interface GeneratedImage {
  id: string;
  project_id: string;
  prompt: string;
  image_url?: string;
  file_path?: string;
  generator_service: string;
  generation_params?: any;
  generated_at: string;
}

export interface VideoOutput {
  id: string;
  project_id: string;
  file_path: string;
  duration_seconds?: number;
  resolution?: string;
  file_size_bytes?: number;
  status: string;
  youtube_video_id?: string;
  created_at: string;
}

export interface ProcessingJob {
  id: string;
  project_id: string;
  job_type: string;
  status: string;
  progress: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ImagePrompt {
  prompt: string;
  service: string;
  size?: string;
  quality?: string;
}

export interface VideoCompositionSettings {
  resolution: string;
  fps: number;
  transition_duration: number;
  add_audio_visualization: boolean;
}

export interface YouTubePublishSettings {
  title: string;
  description?: string;
  tags?: string[];
  privacy_status: string;
  category_id: string;
}
