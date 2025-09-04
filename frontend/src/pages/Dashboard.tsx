import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/projectStore';
import { projectsApi } from '../services/api';
import { Project, AudioFile, GeneratedImage } from '../types';
import { AudioUpload } from '../components/AudioUpload';
import { ImageGenerator } from '../components/ImageGenerator';
import { VideoComposer } from '../components/VideoComposer';
import toast from 'react-hot-toast';

const Dashboard: React.FC = () => {
  const { 
    projects, 
    selectedProject, 
    setProjects, 
    setSelectedProject,
    addProject,
    addAudioFile
  } = useProjectStore();
  
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [currentStep, setCurrentStep] = useState<'upload' | 'generate' | 'compose' | 'review'>('upload');
  const [selectedAudioFiles, setSelectedAudioFiles] = useState<AudioFile[]>([]);
  const [selectedImages, setSelectedImages] = useState<GeneratedImage[]>([]);
  const [createdVideo, setCreatedVideo] = useState<any>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      determineCurrentStep();
      loadSelectedImagesCount();
    }
  }, [selectedProject]);

  const loadProjects = async () => {
    try {
      const projectsData = await projectsApi.getAll();
      setProjects(projectsData);
    } catch (error) {
      console.error('Failed to load projects:', error);
      toast.error('Failed to load projects');
    }
  };

  const determineCurrentStep = async () => {
    if (!selectedProject) return;

    try {
      setCurrentStep('upload');
    } catch (error) {
      console.error('Failed to determine current step:', error);
      setCurrentStep('upload');
    }
  };

  const loadSelectedImagesCount = async () => {
    if (!selectedProject) return;
    
    try {
      const images = await projectsApi.getImages(selectedProject.id);
      setSelectedImages(images);
    } catch (error) {
      console.error('Failed to load images:', error);
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      toast.error('Please enter a project name');
      return;
    }

    setIsCreatingProject(true);
    
    try {
      const newProject = await projectsApi.create({ name: newProjectName.trim() });
      addProject(newProject);
      setSelectedProject(newProject);
      setNewProjectName('');
      setIsCreatingProject(false);
      toast.success('Project created successfully!');
    } catch (error) {
      console.error('Failed to create project:', error);
      toast.error('Failed to create project');
      setIsCreatingProject(false);
    }
  };

  // 🔧 FIXED: Updated to not automatically advance step
  const handleAudioSelected = (audioFiles: AudioFile[]) => {
    setSelectedAudioFiles(audioFiles);
    
    // Add all files to store
    audioFiles.forEach(file => addAudioFile(file));
    
    // ✅ DON'T automatically advance step - let user choose when to proceed
    if (audioFiles.length > 0) {
      const totalDuration = audioFiles.reduce((sum, file) => sum + (file.duration_seconds || 0), 0);
      
      if (audioFiles.length === 1) {
        toast.success('Audio file selected! Select more files or click "Continue to Images" when ready.');
      } else {
        toast.success(`${audioFiles.length} audio files selected (${formatTime(totalDuration)} total)! Add more or continue to images.`);
      }
    }
  };

  // 🔧 NEW: Manual step advancement functions
  const handleProceedToImages = () => {
    if (selectedAudioFiles.length === 0) {
      toast.error('Please select at least one audio file first');
      return;
    }

    const totalDuration = selectedAudioFiles.reduce((sum, file) => sum + (file.duration_seconds || 0), 0);
    setCurrentStep('generate');
    
    if (selectedAudioFiles.length === 1) {
      toast.success('Now select or generate images for your music video.');
    } else {
      toast.success(`Ready to create images for your ${formatTime(totalDuration)} multi-track video!`);
    }
  };

  const handleProceedToComposition = () => {
    if (selectedImages.length === 0) {
      toast.error('Please select at least one image first');
      return;
    }

    setCurrentStep('compose');
    const totalDuration = selectedAudioFiles.reduce((sum, file) => sum + (file.duration_seconds || 0), 0);
    toast.success(`${selectedImages.length} image${selectedImages.length !== 1 ? 's' : ''} selected! Ready to compose ${formatTime(totalDuration)} video.`);
  };

  const handleImagesSelected = (images: GeneratedImage[]) => {
    setSelectedImages(images);
    
    // ✅ DON'T automatically advance step here either
    if (images.length > 0) {
      toast.success(`${images.length} image${images.length !== 1 ? 's' : ''} selected! Click "Continue to Video Composition" when ready.`);
    }
  };

  const handleStepNavigation = (step: 'upload' | 'generate' | 'compose' | 'review') => {
    setCurrentStep(step);
  };

  const formatTime = (seconds: number) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const renderStepContent = () => {
    if (!selectedProject) return null;

    switch (currentStep) {
      case 'upload':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Audio Setup
              </h3>
              <p className="text-gray-600 mb-6">
                Select one or more audio files to create your video soundtrack. Multiple files will be combined sequentially.
              </p>
            </div>
            
            <AudioUpload 
              projectId={selectedProject.id} 
              onUploadComplete={handleAudioSelected} 
            />

            {/* 🔧 NEW: Manual Continue Button */}
            {selectedAudioFiles.length > 0 && (
              <div className="text-center pt-6 border-t">
                <div className="mb-4">
                  <div className="inline-flex items-center px-4 py-2 bg-green-100 border border-green-200 rounded-lg">
                    <svg className="w-5 h-5 text-green-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-green-800 font-medium">
                      {selectedAudioFiles.length} audio file{selectedAudioFiles.length !== 1 ? 's' : ''} selected
                    </span>
                    <span className="text-green-600 ml-2">
                      ({formatTime(selectedAudioFiles.reduce((sum, file) => sum + (file.duration_seconds || 0), 0))})
                    </span>
                  </div>
                </div>
                
                <button
                  onClick={handleProceedToImages}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  Continue to Images →
                </button>
                
                <p className="text-sm text-gray-500 mt-2">
                  Or select more audio files above to create a longer video
                </p>
              </div>
            )}
          </div>
        );
      
      case 'generate':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Image Selection
              </h3>
              <p className="text-gray-600 mb-6">
                Select existing images or generate new ones for your music video.
              </p>
            </div>
            
            <ImageGenerator 
              projectId={selectedProject.id} 
              onImagesSelected={handleImagesSelected} 
            />

            {/* 🔧 NEW: Manual Continue Button for Images */}
            {selectedImages.length > 0 && (
              <div className="text-center pt-6 border-t">
                <div className="mb-4">
                  <div className="inline-flex items-center px-4 py-2 bg-green-100 border border-green-200 rounded-lg">
                    <svg className="w-5 h-5 text-green-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-green-800 font-medium">
                      {selectedImages.length} image{selectedImages.length !== 1 ? 's' : ''} selected
                    </span>
                  </div>
                </div>
                
                <button
                  onClick={handleProceedToComposition}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  Continue to Video Composition →
                </button>
                
                <p className="text-sm text-gray-500 mt-2">
                  Or select more images above to add variety to your video
                </p>
              </div>
            )}
          </div>
        );
      
      case 'compose':
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Video Composition
              </h3>
              <p className="text-gray-600">
                Create your final music video with customizable settings and effects.
              </p>
            </div>

            {/* Multi-Audio Summary */}
            {selectedAudioFiles.length > 1 && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
                <h4 className="font-medium text-purple-900 mb-2">Multi-Track Audio</h4>
                <div className="text-sm text-purple-700 space-y-1">
                  <div className="flex justify-between">
                    <span>Files:</span>
                    <span>{selectedAudioFiles.length} tracks</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Duration:</span>
                    <span>{formatTime(selectedAudioFiles.reduce((sum, file) => sum + (file.duration_seconds || 0), 0))}</span>
                  </div>
                  <div className="mt-2 pt-2 border-t border-purple-200">
                    <div className="text-xs text-purple-600">
                      Tracks will play sequentially:
                    </div>
                    {selectedAudioFiles.map((file, index) => (
                      <div key={file.id} className="flex justify-between text-xs text-purple-600 mt-1">
                        <span>#{index + 1}: {file.filename}</span>
                        <span>{formatTime(file.duration_seconds || 0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <VideoComposer
              projectId={selectedProject.id}
              audioFileName={
                selectedAudioFiles.length === 1 
                  ? selectedAudioFiles[0].filename
                  : `${selectedAudioFiles.length} audio files`
              }
              selectedImagesCount={selectedImages.length}
              selectedImages={selectedImages}
              isMultiAudio={selectedAudioFiles.length > 1}
              totalAudioDuration={selectedAudioFiles.reduce((sum, file) => sum + (file.duration_seconds || 0), 0)}
              onVideoCreated={(videoData) => {
                console.log('Video created:', videoData);
                setCurrentStep('review');
                setCreatedVideo(videoData);
              }}
            />
          </div>
        );
      
      case 'review':
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Review & Download
              </h3>
              <p className="text-gray-600">
                Your music video is ready! Review, download, or share it.
              </p>
            </div>

            {createdVideo ? (
              <div className="bg-white border rounded-lg p-6">
                {/* Multi-Audio Video Info */}
                {createdVideo.audio_info && createdVideo.audio_info.file_count > 1 && (
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
                    <h4 className="font-medium text-purple-900 mb-2">Multi-Track Composition</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm text-purple-700">
                      <div>
                        <span className="font-medium">Audio Tracks:</span> {createdVideo.audio_info.file_count}
                      </div>
                      <div>
                        <span className="font-medium">Combined Duration:</span> {formatTime(createdVideo.audio_info.total_duration)}
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-purple-200">
                      <div className="text-xs text-purple-600 mb-1">Source files:</div>
                      <div className="text-xs text-purple-600">
                        {createdVideo.audio_info.individual_files?.join(', ')}
                      </div>
                    </div>
                  </div>
                )}

                {/* Video Preview */}
                <div className="text-center mb-6">
                  <video
                    controls
                    className="w-full max-w-2xl mx-auto rounded-lg shadow-lg"
                    src={`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/uploads/${createdVideo.video_path}`}
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>

                {/* Video Info */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 text-sm">
                  <div className="text-center">
                    <span className="block font-medium text-gray-700">Duration</span>
                    <span className="text-gray-600">
                      {formatTime(createdVideo.duration || 0)}
                    </span>
                  </div>
                  <div className="text-center">
                    <span className="block font-medium text-gray-700">Resolution</span>
                    <span className="text-gray-600">{createdVideo.resolution || 'Unknown'}</span>
                  </div>
                  <div className="text-center">
                    <span className="block font-medium text-gray-700">File Size</span>
                    <span className="text-gray-600">
                      {((createdVideo.file_size || 0) / (1024 * 1024)).toFixed(1)} MB
                    </span>
                  </div>
                  <div className="text-center">
                    <span className="block font-medium text-gray-700">Status</span>
                    <span className="text-green-600 font-medium">{createdVideo.status || 'completed'}</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-wrap justify-center gap-4">
                  <button
                    onClick={() => {
                      const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
                      const link = document.createElement('a');
                      link.href = `${baseUrl}/uploads/${createdVideo.video_path}`;
                      link.download = createdVideo.video_path;
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                    }}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    📥 Download Video
                  </button>
                  
                  <button
                    onClick={() => {
                      toast('YouTube upload feature coming soon!', {
                        icon: '📺',
                        duration: 3000,
                      });
                    }}
                    className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                  >
                    📺 Upload to YouTube
                  </button>
                  
                  <button
                    onClick={() => {
                      if (navigator.share) {
                        navigator.share({
                          title: `${selectedProject.name} - Music Video`,
                          text: 'Check out my music video!',
                          url: window.location.href
                        });
                      } else {
                        navigator.clipboard.writeText(window.location.href);
                        toast.success('Link copied to clipboard!');
                      }
                    }}
                    className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    🔗 Share
                  </button>
                </div>

                {/* Create Another Video */}
                <div className="text-center mt-6 pt-6 border-t">
                  <button
                    onClick={() => {
                      setCreatedVideo(null);
                      setCurrentStep('compose');
                    }}
                    className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                  >
                    ← Create Another Video with Different Settings
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <p className="mb-4">No video created yet</p>
                <button
                  onClick={() => setCurrentStep('compose')}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Go to Video Composition
                </button>
              </div>
            )}
          </div>
        );
      
      default:
        return null;
    }
  };

  const canNavigateToStep = (step: 'upload' | 'generate' | 'compose' | 'review') => {
    switch (step) {
      case 'upload':
        return true;
      case 'generate':
        return selectedAudioFiles.length > 0;
      case 'compose':
        return selectedAudioFiles.length > 0 && selectedImages.length > 0;
      case 'review':
        return createdVideo !== null;
      default:
        return false;
    }
  };

  const getTotalAudioDuration = () => {
    return selectedAudioFiles.reduce((sum, file) => sum + (file.duration_seconds || 0), 0);
  };

  if (selectedProject) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <button
              onClick={() => {
                setSelectedProject(null);
                setCurrentStep('upload');
                setSelectedAudioFiles([]);
                setSelectedImages([]);
                setCreatedVideo(null);
              }}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Projects
            </button>
          </div>
          
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">
              {selectedProject.name}
            </h1>
            
            {/* Interactive Workflow Navigation */}
            <nav className="flex items-center justify-center space-x-4 mb-8">
              {[
                { id: 'upload', name: 'Audio Setup', icon: '🎵' },
                { id: 'generate', name: 'Select Images', icon: '🎨' },
                { id: 'compose', name: 'Compose Video', icon: '🎬' },
                { id: 'review', name: 'Review & Publish', icon: '🚀' }
              ].map((step, stepIdx) => (
                <div key={step.id} className="flex items-center">
                  <button
                    onClick={() => canNavigateToStep(step.id as any) && handleStepNavigation(step.id as any)}
                    disabled={!canNavigateToStep(step.id as any)}
                    className={`flex flex-col items-center p-3 rounded-lg transition-colors ${
                      currentStep === step.id
                        ? 'bg-blue-100 text-blue-700 border-2 border-blue-300'
                        : canNavigateToStep(step.id as any)
                        ? 'bg-gray-100 text-gray-700 hover:bg-gray-200 border-2 border-transparent'
                        : 'bg-gray-50 text-gray-400 border-2 border-transparent cursor-not-allowed'
                    }`}
                  >
                    <span className="text-2xl mb-2">{step.icon}</span>
                    <span className="text-sm font-medium">{step.name}</span>
                    
                    {/* Updated status indicators for multi-audio */}
                    {step.id === 'upload' && selectedAudioFiles.length === 0 && (
                      <span className="text-xs text-orange-600 mt-1">
                        Selection required
                      </span>
                    )}
                    {step.id === 'upload' && selectedAudioFiles.length > 0 && (
                      <span className="text-xs text-green-600 mt-1">
                        {selectedAudioFiles.length} file{selectedAudioFiles.length !== 1 ? 's' : ''} ({formatTime(getTotalAudioDuration())})
                      </span>
                    )}
                    {step.id === 'generate' && selectedImages.length > 0 && (
                      <span className="text-xs text-green-600 mt-1">
                        {selectedImages.length} image{selectedImages.length !== 1 ? 's' : ''}
                      </span>
                    )}
                    {step.id === 'review' && createdVideo && (
                      <span className="text-xs text-green-600 mt-1">
                        Video ready
                      </span>
                    )}
                  </button>
                  {stepIdx < 3 && (
                    <div className="w-8 h-0.5 mx-2 bg-gray-300" />
                  )}
                </div>
              ))}
            </nav>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border p-6">
            {renderStepContent()}
          </div>
        </div>
      </div>
    );
  }

  // Project list view (unchanged)
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            YouTube Music Channel Automation
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Create stunning YouTube music videos by uploading multiple audio files and generating AI-powered visual content. 
            Combine multiple tracks for longer, more engaging videos.
          </p>
        </div>

        <div className="max-w-md mx-auto mb-8">
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Create New Project</h2>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Enter project name"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                onClick={handleCreateProject}
                disabled={isCreatingProject || !newProjectName.trim()}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isCreatingProject ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.id}
              className="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSelectedProject(project)}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900 truncate">
                  {project.name}
                </h3>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  project.status === 'completed' ? 'bg-green-100 text-green-800' :
                  project.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {project.status}
                </span>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                Created {new Date(project.created_at).toLocaleDateString()}
              </p>
              <div className="flex space-x-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedProject(project);
                  }}
                  className="flex-1 px-3 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Open
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // Handle delete
                  }}
                  className="px-3 py-2 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>

        {projects.length === 0 && (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No projects</h3>
            <p className="mt-1 text-sm text-gray-500">Get started by creating a new project.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;