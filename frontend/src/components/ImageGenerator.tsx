import React, { useState, useEffect } from 'react';
import { ImagePrompt, GeneratedImage } from '../types';
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
  const [previewImages, setPreviewImages] = useState<Array<{
    id: string;
    url: string;
    prompt: string;
    service: string;
  }>>([]);
  const [approvedImages, setApprovedImages] = useState<GeneratedImage[]>([]);

  // Load existing approved images
  useEffect(() => {
    loadApprovedImages();
  }, [projectId]);

  const loadApprovedImages = async () => {
    try {
      const images = await projectsApi.getImages(projectId);
      setApprovedImages(images);
    } catch (error) {
      console.error('Failed to load images:', error);
    }
  };

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

      console.log('Generating image with prompt:', imagePrompt);
      
      // Generate preview image
      const result = await projectsApi.generateImagePreview(projectId, imagePrompt);
      
      console.log('Preview result:', result);
      
      // Add to preview images with full URL
      const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const fullImageUrl = result.preview_url.startsWith('http') 
        ? result.preview_url 
        : `${baseUrl}${result.preview_url}`;
      
      const previewImage = {
        id: result.task_id,
        url: fullImageUrl,
        prompt: result.prompt,
        service: result.service
      };
      
      console.log('Adding preview image:', previewImage);
      
      setPreviewImages(prev => [...prev, previewImage]);
      toast.success('Image generated! Review and approve to use in video.');
      
    } catch (error) {
      console.error('Image generation failed:', error);
      toast.error('Image generation failed. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApprove = async (previewId: string) => {
    try {
      console.log('Approving image with ID:', previewId);
      
      // Approve the image - this saves it to the project
      const approvedImage = await projectsApi.approveImage(projectId, previewId);
      
      console.log('Image approved:', approvedImage);
      
      // Remove from preview and add to approved
      setPreviewImages(prev => prev.filter(img => img.id !== previewId));
      setApprovedImages(prev => [...prev, approvedImage]);
      
      toast.success('Image approved and added to project!');
      onImageGenerated(approvedImage);
    } catch (error) {
      console.error('Failed to approve image:', error);
      toast.error('Failed to approve image');
    }
  };

  const handleReject = (previewId: string) => {
    setPreviewImages(prev => prev.filter(img => img.id !== previewId));
    toast.success('Image rejected');
  };

  const handleRemoveApproved = async (imageId: string) => {
    try {
      await projectsApi.removeImage(projectId, imageId);
      setApprovedImages(prev => prev.filter(img => img.id !== imageId));
      toast.success('Image removed from project');
    } catch (error) {
      console.error('Failed to remove image:', error);
      toast.error('Failed to remove image');
    }
  };

  // Helper function to get image URL for display
  const getImageUrl = (image: GeneratedImage) => {
    if (image.image_url?.startsWith('http')) {
      return image.image_url;
    }
    
    const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    if (image.image_url?.startsWith('/')) {
      return `${baseUrl}${image.image_url}`;
    }
    
    if (image.file_path) {
      const filename = image.file_path.split('/').pop();
      return `${baseUrl}/uploads/${filename}`;
    }
    
    return image.image_url || '';
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8">
      {/* Generation Form */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Generate New Image</h3>
        
        <div className="space-y-4">
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
      </div>

      {/* Preview Images (Awaiting Approval) */}
      {previewImages.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Review Generated Images
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {previewImages.map((image) => (
              <div key={image.id} className="bg-white border rounded-lg p-4">
                <div className="mb-3">
                  <img
                    src={image.url}
                    alt={image.prompt}
                    className="w-full h-48 object-cover rounded-md"
                    onError={(e) => {
                      console.error('Image failed to load:', image.url);
                      // Show a placeholder or error message
                      e.currentTarget.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBmb3VuZDwvdGV4dD48L3N2Zz4=';
                    }}
                    onLoad={() => {
                      console.log('Image loaded successfully:', image.url);
                    }}
                  />
                </div>
                <p className="text-sm text-gray-700 mb-2 line-clamp-2">
                  "{image.prompt}"
                </p>
                <p className="text-xs text-gray-500 mb-3">
                  Generated with {image.service}
                </p>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleApprove(image.id)}
                    className="flex-1 px-3 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors"
                  >
                    ✓ Approve
                  </button>
                  <button
                    onClick={() => handleReject(image.id)}
                    className="flex-1 px-3 py-2 bg-red-600 text-white text-sm rounded-md hover:bg-red-700 transition-colors"
                  >
                    ✗ Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approved Images */}
      {approvedImages.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Approved Images ({approvedImages.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {approvedImages.map((image) => (
              <div key={image.id} className="bg-white border rounded-lg p-3">
                <img
                  src={getImageUrl(image)}
                  alt={image.prompt}
                  className="w-full h-32 object-cover rounded-md mb-2"
                  onError={(e) => {
                    console.error('Approved image failed to load:', getImageUrl(image));
                  }}
                />
                <p className="text-xs text-gray-700 mb-2 line-clamp-2">
                  "{image.prompt}"
                </p>
                <button
                  onClick={() => handleRemoveApproved(image.id)}
                  className="w-full px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Status Message */}
      {approvedImages.length === 0 && previewImages.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 002 2z" />
          </svg>
          <p>No images generated yet. Create your first image above!</p>
        </div>
      )}
    </div>
  );
};