import React, { useState, useEffect } from 'react';
import { ImagePrompt, GeneratedImage } from '../types';
import { projectsApi } from '../services/api';
import toast from 'react-hot-toast';

interface ImageGeneratorProps {
  projectId: string;
  onImagesSelected: (images: GeneratedImage[]) => void;
}

export const ImageGenerator: React.FC<ImageGeneratorProps> = ({ 
  projectId, 
  onImagesSelected 
}) => {
  const [prompt, setPrompt] = useState('');
  const [service, setService] = useState('stable_diffusion');
  const [isGenerating, setIsGenerating] = useState(false);
  const [previewImages, setPreviewImages] = useState<Array<{
    id: string;
    url: string;
    prompt: string;
    service: string;
  }>>([]);
  const [existingImages, setExistingImages] = useState<GeneratedImage[]>([]);
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set());
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Load existing approved images
  useEffect(() => {
    loadExistingImages();
  }, [projectId]);

  const loadExistingImages = async () => {
    setIsLoading(true);
    try {
      const images = await projectsApi.getImages(projectId);
      setExistingImages(images);
      
      // Don't auto-select - let user choose
      if (images.length === 0) {
        setShowGenerateForm(true);
      }
    } catch (error) {
      console.error('Failed to load images:', error);
      setShowGenerateForm(true);
    } finally {
      setIsLoading(false);
    }
  };

  const [resolution, setResolution] = useState('1024x1024');
  const [qualitySteps, setQualitySteps] = useState('25');

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
        size: resolution,  // This will be passed as 'size'
        quality: qualitySteps  // This will be passed as 'quality'
      };

      console.log('Generating image with parameters:', imagePrompt);
      
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
      
      setPreviewImages(prev => [...prev, previewImage]);
      toast.success('Image generated! Review and approve to add to collection.');
      
      // Reset form
      setPrompt('');
      
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
      
      // Remove from preview and add to existing
      setPreviewImages(prev => prev.filter(img => img.id !== previewId));
      setExistingImages(prev => [...prev, approvedImage]);
      
      toast.success('Image approved and added to collection!');
    } catch (error) {
      console.error('Failed to approve image:', error);
      toast.error('Failed to approve image');
    }
  };

  const handleReject = async (previewId: string) => {
    try {
      // Find the preview image to get the file path
      const previewImage = previewImages.find(img => img.id === previewId);
      
      if (previewImage) {
        // If it's a local file (from stable diffusion), we need to delete it
        if (previewImage.url.includes('/uploads/')) {
          console.log('Deleting rejected preview file:', previewImage.url);
          
          // Call backend to delete the preview file
          try {
            await projectsApi.deletePreviewImage(projectId, previewId);
          } catch (error) {
            console.error('Failed to delete preview file:', error);
            // Continue with UI update even if file deletion failed
          }
        }
      }
      
      // Remove from preview list
      setPreviewImages(prev => prev.filter(img => img.id !== previewId));
      toast.success('Image rejected and removed');
    } catch (error) {
      console.error('Error rejecting image:', error);
      toast.error('Error rejecting image');
    }
  };

  const handleImageSelect = (imageId: string, selected: boolean) => {
    const newSelected = new Set(selectedImages);
    if (selected) {
      newSelected.add(imageId);
    } else {
      newSelected.delete(imageId);
    }
    setSelectedImages(newSelected);
    
    // Get selected images and pass to parent
    const selectedImagesList = existingImages.filter(img => newSelected.has(img.id));
    onImagesSelected(selectedImagesList);
    
    if (selectedImagesList.length > 0) {
      toast.success(`${selectedImagesList.length} image${selectedImagesList.length !== 1 ? 's' : ''} selected`);
    }
  };

  const handleRemoveImage = async (imageId: string) => {
    try {
      await projectsApi.removeImage(projectId, imageId);
      setExistingImages(prev => prev.filter(img => img.id !== imageId));
      
      // Remove from selection if it was selected
      const newSelected = new Set(selectedImages);
      newSelected.delete(imageId);
      setSelectedImages(newSelected);
      
      const selectedImagesList = existingImages.filter(img => newSelected.has(img.id));
      onImagesSelected(selectedImagesList);
      
      toast.success('Image removed from collection');
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

  if (isLoading) {
    return (
      <div className="w-full max-w-4xl mx-auto text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-2 text-gray-600">Loading images...</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      {/* Existing Images Selection */}
      {existingImages.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">
              Select Images for Video ({existingImages.length} available)
            </h3>
            <button
              onClick={() => setShowGenerateForm(!showGenerateForm)}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              {showGenerateForm ? 'Cancel Generate' : '+ Generate New'}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {existingImages.map((image) => {
              const isSelected = selectedImages.has(image.id);
              return (
                <div
                  key={image.id}
                  className={`border rounded-lg p-3 cursor-pointer transition-all ${
                    isSelected 
                      ? 'border-blue-500 bg-blue-50 shadow-md' 
                      : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
                  }`}
                  onClick={() => handleImageSelect(image.id, !isSelected)}
                >
                  {/* Selection indicator */}
                  <div className="flex items-center justify-between mb-2">
                    <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                      isSelected 
                        ? 'border-blue-500 bg-blue-500' 
                        : 'border-gray-300 hover:border-blue-400'
                    }`}>
                      {isSelected && (
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveImage(image.id);
                      }}
                      className="text-red-600 hover:text-red-800 p-1 opacity-70 hover:opacity-100"
                      title="Remove image"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                  
                  <img
                    src={getImageUrl(image)}
                    alt={image.prompt}
                    className="w-full h-32 object-cover rounded-md mb-2"
                    onError={(e) => {
                      console.error('Image failed to load:', getImageUrl(image));
                    }}
                  />
                  
                  <p className="text-xs text-gray-700 mb-2 line-clamp-2">
                    "{image.prompt}"
                  </p>
                  
                  <p className="text-xs text-gray-500">
                    Generated with {image.generator_service}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Selection Status */}
          {selectedImages.size > 0 ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <svg className="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="font-medium text-green-800">
                    {selectedImages.size} image{selectedImages.size !== 1 ? 's' : ''} selected
                  </p>
                  <p className="text-sm text-green-600">
                    Ready to proceed to video composition
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <svg className="h-6 w-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div>
                  <p className="font-medium text-yellow-800">
                    No images selected
                  </p>
                  <p className="text-sm text-yellow-600">
                    Please select images above or generate new ones below to continue
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Generate New Images Section */}
      {(showGenerateForm || existingImages.length === 0) && (
        <div className="bg-white border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              {existingImages.length > 0 ? 'Generate New Images' : 'Generate Images'}
            </h3>
            {existingImages.length > 0 && (
              <button
                onClick={() => setShowGenerateForm(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
          
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
                <option value="stable_diffusion">Stable Diffusion (Local - GPU)</option>
                <option value="dalle">DALL-E 3 (Fast, High Quality)</option>
                <option value="midjourney">Midjourney (Artistic Style)</option>
              </select>
            </div>

            {service === 'stable_diffusion' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Resolution
                  </label>
                  <select 
                    value = {resolution}
                    onChange={(e) => setResolution(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                    <option value="512x512">512x512 (Fast)</option>
                    <option value="768x768" selected>768x768 (Balanced)</option>
                    <option value="1024x1024">1024x1024 (High Quality)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Quality Steps
                  </label>
                  <select 
                    value = {qualitySteps}
                    onChange={(e) => setQualitySteps(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                    <option value="15">15 (Fast)</option>
                    <option value="25" selected>25 (Balanced)</option>
                    <option value="50">50 (High Quality)</option>
                  </select>
                </div>
              </div>
            )}

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
      )}

      {/* Preview Images (Awaiting Approval) */}
      {previewImages.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Review Generated Images
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {previewImages.map((image) => (
              <div key={image.id} className="bg-white border rounded-lg p-4">
                <div className="mb-3">
                  <img
                    src={image.url}
                    alt={image.prompt}
                    className="w-full h-48 object-cover rounded-md"
                    onError={(e) => {
                      console.error('Image failed to load:', image.url);
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

      {/* Empty State */}
      {existingImages.length === 0 && previewImages.length === 0 && !showGenerateForm && (
        <div className="text-center py-8 text-gray-500">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 002 2z" />
          </svg>
          <p>No images available yet.</p>
          <button
            onClick={() => setShowGenerateForm(true)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Generate Your First Image
          </button>
        </div>
      )}
    </div>
  );
};