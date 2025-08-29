import React from 'react';
import { Project } from '../types';

interface ProjectWorkflowProps {
  project: Project;
  approvedImagesCount?: number;
}

export const ProjectWorkflow: React.FC<ProjectWorkflowProps> = ({ 
  project, 
  approvedImagesCount = 0 
}) => {
  const steps = [
    { 
      id: 'upload', 
      name: 'Upload Audio', 
      status: 'completed', // You'd determine this based on whether audio exists
      description: 'Upload your music track'
    },
    { 
      id: 'generate', 
      name: 'Generate & Approve Images', 
      status: approvedImagesCount > 0 ? 'completed' : 'current',
      description: `${approvedImagesCount} approved image${approvedImagesCount !== 1 ? 's' : ''}`
    },
    { 
      id: 'compose', 
      name: 'Compose Video', 
      status: approvedImagesCount > 0 ? 'available' : 'pending',
      description: 'Create final video'
    },
    { 
      id: 'review', 
      name: 'Review & Publish', 
      status: 'pending',
      description: 'Final review and upload to YouTube'
    }
  ];

  const getStepIcon = (step: any, index: number) => {
    if (step.status === 'completed') {
      return (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      );
    }
    
    if (step.status === 'current') {
      return (
        <div className="w-3 h-3 bg-current rounded-full animate-pulse"></div>
      );
    }
    
    return <span className="text-sm font-medium">{index + 1}</span>;
  };

  const getStepStyles = (step: any) => {
    switch (step.status) {
      case 'completed':
        return 'bg-green-600 border-green-600 text-white';
      case 'current':
        return 'bg-blue-600 border-blue-600 text-white';
      case 'available':
        return 'bg-yellow-500 border-yellow-500 text-white';
      default:
        return 'border-gray-300 text-gray-500';
    }
  };

  const getTextStyles = (step: any) => {
    switch (step.status) {
      case 'completed':
        return 'text-green-600';
      case 'current':
        return 'text-blue-600 font-semibold';
      case 'available':
        return 'text-yellow-600';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <nav className="flex items-center justify-center space-x-4 mb-8">
      {steps.map((step, stepIdx) => (
        <div key={step.id} className="flex items-center">
          <div className="text-center">
            <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${getStepStyles(step)}`}>
              {getStepIcon(step, stepIdx)}
            </div>
            <div className="mt-2">
              <span className={`text-sm font-medium ${getTextStyles(step)}`}>
                {step.name}
              </span>
              <p className="text-xs text-gray-500 mt-1">
                {step.description}
              </p>
            </div>
          </div>
          
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