import React, { useState, useEffect } from 'react';
import { projectsApi } from '../services/api';
import toast from 'react-hot-toast';

interface VideoComposerProps {
  projectId: string;
  audioFileName?: string;
  selectedImagesCount: number;
  isMultiAudio?: boolean; // New prop
  totalAudioDuration?: number; // New prop
  onVideoCreated?: (videoData: any) => void;
}

interface VideoSettings {
  resolution: string;
  fps: number;
  transition_duration: number;
  transition_type: string;
  add_ken_burns: boolean;
  image_distribution: string; // New setting for multi-audio
}

interface TaskStatus {
  status: 'pending' | 'progress' | 'success' | 'failed';
  progress: number;
  message?: string;
  result?: any;
  error?: string;
}

export const VideoComposer: React.FC<VideoComposerProps> = ({ 
  projectId, 
  audioFileName, 
  selectedImagesCount,
  isMultiAudio = false,
  totalAudioDuration = 0,
  onVideoCreated 
}) => {
  const [isComposing, setIsComposing] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [videoSettings, setVideoSettings] = useState<VideoSettings>({
    resolution: '1920x1080',
    fps: 30,
    transition_duration: 1.0,
    transition_type: 'fade',
    add_ken_burns: false,
    image_distribution: 'equal' // New setting
  });
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const [createdVideo, setCreatedVideo] = useState<any>(null);

  // Poll task status when composing
  useEffect(() => {
    let pollInterval: NodeJS.Timeout;
    
    if (isComposing && taskId) {
      pollInterval = setInterval(async () => {
        try {
          const status = await projectsApi.getVideoStatus(projectId, taskId);
          setTaskStatus(status);
          
          if (status.status === 'success') {
            setIsComposing(false);
            setCreatedVideo(status.result);
            onVideoCreated?.(status.result);
            
            if (isMultiAudio) {
              toast.success('Multi-audio video created successfully! 🎵🎬');
            } else {
              toast.success('Video created successfully! 🎉');
            }
            clearInterval(pollInterval);
          } else if (status.status === 'failed') {
            setIsComposing(false);
            toast.error(`Video creation failed: ${status.error || 'Unknown error'}`);
            clearInterval(pollInterval);
          }
        } catch (error) {
          console.error('Error polling task status:', error);
        }
      }, 2000);
    }
    
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [isComposing, taskId, projectId, onVideoCreated, isMultiAudio]);

  const handleStartComposition = async () => {
    if (selectedImagesCount === 0) {
      toast.error('Please select at least one image first');
      return;
    }
    
    if (!audioFileName) {
      toast.error('Please select audio file(s) first');
      return;
    }

    setIsComposing(true);
    setTaskStatus({ 
      status: 'pending', 
      progress: 0, 
      message: isMultiAudio ? 'Starting multi-audio video composition...' : 'Starting video composition...'
    });
    
    try {
      // Use the enhanced API endpoint that automatically detects multi-audio
      const response = await projectsApi.composeVideoEnhanced(projectId, videoSettings);
      setTaskId(response.task_id);
      
      if (isMultiAudio) {
        toast.success(`Multi-audio video composition started! Combining ${audioFileName} with ${selectedImagesCount} images. This may take several minutes...`);
      } else {
        toast.success('Video composition started! This may take several minutes...');
      }
    } catch (error: any) {
      setIsComposing(false);
      setTaskStatus(null);
      
      const errorMessage = error.message || 'Failed to start video composition';
      toast.error(errorMessage);
      console.error('Video composition error:', error);
    }
  };

  const handleCancelComposition = async () => {
    if (!taskId) return;
    
    try {
      await projectsApi.cancelVideoComposition(projectId, taskId);
      setIsComposing(false);
      setTaskStatus(null);
      setTaskId(null);
      toast.success('Video composition cancelled');
    } catch (error) {
      console.error('Error cancelling composition:', error);
      toast.error('Failed to cancel video composition');
    }
  };

  const handleDownloadVideo = () => {
    if (createdVideo?.video_path) {
      const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const downloadUrl = `${baseUrl}/uploads/${createdVideo.video_path}`;
      
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = createdVideo.video_path;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const getResolutionLabel = (resolution: string) => {
    const labels: { [key: string]: string } = {
      '1280x720': '720p HD',
      '1920x1080': '1080p Full HD', 
      '2560x1440': '1440p QHD',
      '3840x2160': '4K UHD'
    };
    return labels[resolution] || resolution;
  };

  const formatFileSize = (bytes: number) => {
    if (!bytes) return '0 MB';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const formatDuration = (seconds: number) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Project Summary - Enhanced for Multi-Audio */}
      <div className={`border rounded-lg p-4 ${isMultiAudio ? 'bg-purple-50 border-purple-200' : 'bg-blue-50 border-blue-200'}`}>
        <h3 className={`font-medium mb-2 ${isMultiAudio ? 'text-purple-900' : 'text-blue-900'}`}>
          {isMultiAudio ? 'Multi-Audio Video Composition' : 'Ready for Video Composition'}
        </h3>
        <div className={`text-sm space-y-1 ${isMultiAudio ? 'text-purple-700' : 'text-blue-700'}`}>
          <div className="flex justify-between">
            <span>📄 Audio:</span>
            <span>{audioFileName || 'No audio selected'}</span>
          </div>
          {isMultiAudio && totalAudioDuration > 0 && (
            <div className="flex justify-between">
              <span>⏱️ Total Duration:</span>
              <span>{formatDuration(totalAudioDuration)}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span>🖼️ Images:</span>
            <span>{selectedImagesCount} selected</span>
          </div>
          {isMultiAudio && (
            <div className="mt-2 pt-2 border-t border-purple-200 text-xs text-purple-600">
              💡 Multiple audio files will be combined sequentially to create a longer video
            </div>
          )}
        </div>
      </div>

      {/* Video Settings */}
      <div className="bg-white border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Video Settings</h3>
          <button
            onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {showAdvancedSettings ? 'Hide' : 'Show'} Advanced Settings
          </button>
        </div>

        <div className="space-y-4">
          {/* Basic Settings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Resolution
              </label>
              <select
                value={videoSettings.resolution}
                onChange={(e) => setVideoSettings(prev => ({ ...prev, resolution: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="1280x720">720p HD (Faster)</option>
                <option value="1920x1080">1080p Full HD (Balanced)</option>
                <option value="2560x1440">1440p QHD (High Quality)</option>
                <option value="3840x2160">4K UHD (Best Quality)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Frame Rate
              </label>
              <select
                value={videoSettings.fps}
                onChange={(e) => setVideoSettings(prev => ({ ...prev, fps: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value={24}>24 FPS (Cinematic)</option>
                <option value={30}>30 FPS (Standard)</option>
                <option value={60}>60 FPS (Smooth)</option>
              </select>
            </div>
          </div>

          {/* Advanced Settings */}
          {showAdvancedSettings && (
            <div className="border-t pt-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Transition Duration ({videoSettings.transition_duration}s)
                  </label>
                  <input
                    type="range"
                    min="0.1"
                    max="3.0"
                    step="0.1"
                    value={videoSettings.transition_duration}
                    onChange={(e) => setVideoSettings(prev => ({ 
                      ...prev, 
                      transition_duration: parseFloat(e.target.value) 
                    }))}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Transition Type
                  </label>
                  <select
                    value={videoSettings.transition_type}
                    onChange={(e) => setVideoSettings(prev => ({ ...prev, transition_type: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="fade">Fade (Smooth)</option>
                    <option value="dissolve">Dissolve</option>
                    <option value="wipe">Wipe</option>
                    <option value="slide">Slide</option>
                  </select>
                </div>
              </div>

              {/* Multi-Audio Specific Settings */}
              {isMultiAudio && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Image Distribution Strategy
                  </label>
                  <select
                    value={videoSettings.image_distribution}
                    onChange={(e) => setVideoSettings(prev => ({ ...prev, image_distribution: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="equal">Equal Time (Each image gets same duration)</option>
                    <option value="proportional">Proportional (Varied timing based on position)</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    How to distribute {selectedImagesCount} images across {formatDuration(totalAudioDuration)} of audio
                  </p>
                </div>
              )}

              {/* Effect Options */}
              <div className="space-y-3">
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={videoSettings.add_ken_burns}
                    onChange={(e) => setVideoSettings(prev => ({ 
                      ...prev, 
                      add_ken_burns: e.target.checked 
                    }))}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-gray-700">Ken Burns Effect</span>
                    <p className="text-xs text-gray-500">Add zoom and pan movements to images</p>
                  </div>
                </label>
              </div>

              {/* Multi-Audio Preview */}
              {isMultiAudio && (
                <div className="bg-gray-50 border rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-800 mb-2">Composition Preview</h4>
                  <div className="space-y-2 text-xs text-gray-600">
                    <div className="flex justify-between">
                      <span>Expected Video Length:</span>
                      <span className="font-medium">{formatDuration(totalAudioDuration)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Images per Minute:</span>
                      <span className="font-medium">
                        {totalAudioDuration > 0 ? (selectedImagesCount / (totalAudioDuration / 60)).toFixed(1) : '0'} images/min
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg. Image Duration:</span>
                      <span className="font-medium">
                        {selectedImagesCount > 0 ? formatDuration(totalAudioDuration / selectedImagesCount) : '0:00'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Composition Status */}
      {isComposing && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-yellow-900">
              {isMultiAudio ? 'Creating Multi-Audio Video' : 'Creating Video'}
            </h3>
            <button
              onClick={handleCancelComposition}
              className="text-sm text-red-600 hover:text-red-700 px-3 py-1 border border-red-200 rounded-md hover:bg-red-50"
            >
              Cancel
            </button>
          </div>

          {taskStatus && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-yellow-700">
                  {taskStatus.message || 'Processing...'}
                </span>
                <span className="text-yellow-600">
                  {taskStatus.progress}%
                </span>
              </div>
              
              <div className="w-full bg-yellow-200 rounded-full h-2">
                <div 
                  className="bg-yellow-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${taskStatus.progress}%` }}
                />
              </div>
              
              {taskStatus.progress > 0 && taskStatus.progress < 100 && (
                <p className="text-xs text-yellow-600">
                  {isMultiAudio 
                    ? 'Combining multiple audio files and rendering video. This may take longer than usual.'
                    : 'This may take several minutes depending on video length and quality settings.'
                  }
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Created Video */}
      {createdVideo && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-green-900">
              {isMultiAudio ? 'Multi-Audio Video Created Successfully!' : 'Video Created Successfully!'}
            </h3>
            <div className="flex space-x-2">
              <button
                onClick={handleDownloadVideo}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors text-sm"
              >
                Download Video
              </button>
            </div>
          </div>

          {/* Multi-Audio specific info */}
          {createdVideo.audio_info && (
            <div className="bg-white border rounded p-3 mb-4">
              <h4 className="text-sm font-medium text-gray-800 mb-2">Audio Composition Details</h4>
              <div className="grid grid-cols-2 gap-4 text-xs text-gray-600">
                <div>
                  <span className="font-medium">Source Files:</span> {createdVideo.audio_info.file_count}
                </div>
                <div>
                  <span className="font-medium">Combined Duration:</span> {formatDuration(createdVideo.audio_info.total_duration)}
                </div>
              </div>
              {createdVideo.audio_info.individual_files && (
                <div className="mt-2 pt-2 border-t">
                  <div className="text-xs text-gray-500">
                    Files: {createdVideo.audio_info.individual_files.join(' → ')}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-green-700 font-medium">Duration:</span>
              <p className="text-green-600">{formatDuration(createdVideo.duration)}</p>
            </div>
            <div>
              <span className="text-green-700 font-medium">Resolution:</span>
              <p className="text-green-600">{getResolutionLabel(createdVideo.resolution)}</p>
            </div>
            <div>
              <span className="text-green-700 font-medium">File Size:</span>
              <p className="text-green-600">{formatFileSize(createdVideo.file_size)}</p>
            </div>
            <div>
              <span className="text-green-700 font-medium">Format:</span>
              <p className="text-green-600">MP4</p>
            </div>
          </div>

          {/* Video Preview */}
          <div className="mt-4">
            <video
              controls
              className="w-full max-w-md mx-auto rounded-md shadow-lg"
              src={`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/uploads/${createdVideo.video_path}`}
            >
              Your browser does not support the video tag.
            </video>
          </div>
        </div>
      )}

      {/* Compose Button */}
      {!isComposing && !createdVideo && (
        <div className="text-center">
          <button
            onClick={handleStartComposition}
            disabled={selectedImagesCount === 0 || !audioFileName}
            className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-lg font-medium"
          >
            🎬 {isMultiAudio ? 'Create Multi-Audio Video' : 'Create Video'}
          </button>
          
          {(selectedImagesCount === 0 || !audioFileName) && (
            <p className="text-sm text-gray-500 mt-2">
              Please select audio file(s) and at least one image to create a video
            </p>
          )}
          
          {isMultiAudio && (
            <p className="text-sm text-blue-600 mt-2">
              💫 This will create a longer video by combining multiple audio tracks
            </p>
          )}
        </div>
      )}

      {/* Reset Button */}
      {createdVideo && (
        <div className="text-center">
          <button
            onClick={() => {
              setCreatedVideo(null);
              setTaskStatus(null);
              setTaskId(null);
            }}
            className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            Create Another Video
          </button>
        </div>
      )}
    </div>
  );
};