import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/projectStore';
import { projectsApi } from '../services/api';
import { Project, AudioFile, GeneratedImage } from '../types';
import { AudioUpload } from '../components/AudioUpload';
import { ImageGenerator } from '../components/ImageGenerator';
import { ProjectWorkflow } from '../components/ProjectWorkflow';
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
  const [selectedAudioFile, setSelectedAudioFile] = useState<AudioFile | null>(null);
  const [selectedImages, setSelectedImages] = useState<GeneratedImage[]>([]);

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
      // Don't auto-progress anymore - always start at upload to let user choose
      setCurrentStep('upload');
      
    } catch (error) {
      console.error('Failed to determine current step:', error);
      setCurrentStep('upload'); // Default to upload on error
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

  const handleAudioSelected = (audioFile: AudioFile | null) => {
    if (audioFile) {
      setSelectedAudioFile(audioFile);
      addAudioFile(audioFile);
      
      // Always go to generate step after audio selection, regardless of existing images
      setCurrentStep('generate');
      toast.success('Audio selected! Now select or generate images.');
    } else {
      // Audio was deselected
      setSelectedAudioFile(null);
      // Stay on upload step
      setCurrentStep('upload');
    }
  };

  const handleImagesSelected = (images: GeneratedImage[]) => {
    setSelectedImages(images);
    
    // If we have both audio and images, move to compose step
    if (selectedAudioFile && images.length > 0) {
      setCurrentStep('compose');
      toast.success(`${images.length} image${images.length !== 1 ? 's' : ''} selected! Ready to compose video.`);
    }
  };

  const handleStepNavigation = (step: 'upload' | 'generate' | 'compose' | 'review') => {
    setCurrentStep(step);
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
                Listen to and select an audio file, or upload a new one to get started.
              </p>
            </div>
            <AudioUpload 
              projectId={selectedProject.id} 
              onUploadComplete={handleAudioSelected} 
            />
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
          </div>
        );
      case 'compose':
        return (
          <div className="text-center py-8">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Video Composition
            </h3>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
              <div className="flex items-center justify-center space-x-4 text-blue-800">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Audio: {selectedAudioFile?.filename}</span>
                <span>•</span>
                <span>{selectedImages.length} selected image{selectedImages.length !== 1 ? 's' : ''}</span>
              </div>
            </div>
            <p className="text-gray-600 mb-6">
              Ready to create your music video! Video composition feature will be available soon.
            </p>
            <button className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
              Compose Video (Coming Soon)
            </button>
          </div>
        );
      case 'review':
        return (
          <div className="text-center py-8">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Review & Download
            </h3>
            <p className="text-gray-600">
              Review and download feature coming soon...
            </p>
          </div>
        );
      default:
        return null;
    }
  };

  const canNavigateToStep = (step: 'upload' | 'generate' | 'compose' | 'review') => {
    switch (step) {
      case 'upload':
        return true; // Can always go back to upload
      case 'generate':
        return selectedAudioFile !== null; // Need audio to generate
      case 'compose':
        return selectedAudioFile !== null && selectedImages.length > 0; // Need audio + images
      case 'review':
        return false; // Not implemented yet
      default:
        return false;
    }
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
                setSelectedAudioFile(null);
                setSelectedImages([]);
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
                    {step.id === 'upload' && !selectedAudioFile && (
                      <span className="text-xs text-orange-600 mt-1">
                        Selection required
                      </span>
                    )}
                    {step.id === 'generate' && selectedImages.length > 0 && (
                      <span className="text-xs text-green-600 mt-1">
                        {selectedImages.length} image{selectedImages.length !== 1 ? 's' : ''}
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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            YouTube Music Channel Automation
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Create stunning YouTube music videos by uploading audio files and generating AI-powered visual content. 
            Automate your content creation workflow from start to finish.
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

// IMPORTANT: Make sure this is a default export
export default Dashboard;