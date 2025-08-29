import React from 'react';
import { Project } from '../types';

interface ProjectWorkflowProps {
  project: Project;
}

export const ProjectWorkflow: React.FC<ProjectWorkflowProps> = ({ project }) => {
  const getCurrentStep = (project: Project) => {
    // This would be more sophisticated in a real implementation
    // For now, just return a basic step
    return 'upload';
  };

  const getImageStatus = (project: Project) => {
    // Check if project has generated images
    return 'pending';
  };

  const getVideoStatus = (project: Project) => {
    // Check if project has video outputs
    return 'pending';
  };

  const getReviewStatus = (project: Project) => {
    // Check if project is ready for review
    return 'pending';
  };

  const steps = [
    { id: 'upload', name: 'Upload Audio', status: 'completed' },
    { id: 'generate', name: 'Generate Images', status: getImageStatus(project) },
    { id: 'compose', name: 'Compose Video', status: getVideoStatus(project) },
    { id: 'review', name: 'Review & Download', status: getReviewStatus(project) }
  ];

  return (
    <nav className="flex items-center justify-center space-x-4 mb-8">
      {steps.map((step, stepIdx) => (
        <div key={step.id} className="flex items-center">
          <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
            step.status === 'completed' 
              ? 'bg-green-600 border-green-600 text-white'
              : step.status === 'current'
              ? 'bg-blue-600 border-blue-600 text-white'
              : 'border-gray-300 text-gray-500'
          }`}>
            {step.status === 'completed' ? (
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <span className="text-sm font-medium">{stepIdx + 1}</span>
            )}
          </div>
          <span className={`ml-2 text-sm font-medium ${
            step.status === 'completed' ? 'text-green-600' : 'text-gray-900'
          }`}>
            {step.name}
          </span>
          {stepIdx < steps.length - 1 && (
            <div className={`w-8 h-0.5 mx-4 ${
              steps[stepIdx + 1].status === 'completed' ? 'bg-green-600' : 'bg-gray-300'
            }`} />
          )}
        </div>
      ))}
    </nav>
  );
};
