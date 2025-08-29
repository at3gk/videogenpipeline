import React, { useState } from 'react';
import { ImagePrompt } from '../types';
import { projectsApi } from '../services/api';
import toast from 'react-hot-toast';

interface ImageGeneratorProps {
  projectId: string;
  onImageGenerated: (image: any) => void;
}

export const ImageGenerator: React.FC<ImageGeneratorProps> = ({ 
  projectId, 
  onImageGenerated 
}) => {
  const [prompt, setPrompt] = useState('');
  const [service, setService] = useState('dalle');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a prompt');
      return;
    }

    setIsGenerating(true);
    
    try {
      const imagePrompt: ImagePrompt = {
        prompt: prompt.trim(),
        service,
        size: '1024x1024',
        quality: 'standard'
      };

      const result = await projectsApi.generateImage(projectId, imagePrompt);
      
      toast.success('Image generation started!');
      onImageGenerated(result);
      
      // Reset form
      setPrompt('');
    } catch (error) {
      console.error('Image generation failed:', error);
      toast.error('Image generation failed. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const promptSuggestions = [
    'A beautiful sunset over mountains',
    'Abstract geometric patterns',
    'Vibrant city skyline at night',
    'Peaceful forest scene',
    'Ocean waves crashing on rocks',
    'Space nebula with stars',
    'Vintage retro aesthetic',
    'Modern minimalist design'
  ];

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      <div>
        <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
          Image Prompt
        </label>
        <textarea
          id="prompt"
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          placeholder="Describe the image you want to generate..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        
        <div className="mt-2">
          <p className="text-sm text-gray-500 mb-2">Quick suggestions:</p>
          <div className="flex flex-wrap gap-2">
            {promptSuggestions.map((suggestion, index) => (
              <button
                key={index}
                type="button"
                onClick={() => setPrompt(suggestion)}
                className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <label htmlFor="service" className="block text-sm font-medium text-gray-700 mb-2">
          AI Service
        </label>
        <select
          id="service"
          value={service}
          onChange={(e) => setService(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="dalle">DALL-E 3 (Fast, High Quality)</option>
          <option value="midjourney">Midjourney (Artistic Style)</option>
          <option value="stable_diffusion">Stable Diffusion (Local)</option>
        </select>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-blue-700">
              <strong>Tip:</strong> Be specific and descriptive in your prompt. Include details about style, mood, colors, and composition for better results.
            </p>
          </div>
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={isGenerating || !prompt.trim()}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isGenerating ? (
          <div className="flex items-center justify-center space-x-2">
            <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Generating...</span>
          </div>
        ) : (
          'Generate Image'
        )}
      </button>
    </div>
  );
};
