import React, { useState, useEffect } from 'react';
import { ImagePrompt, GeneratedImage } from '../types';
import { projectsApi } from '../services/api';
import { ImageModal } from './ImageModal';
import toast from 'react-hot-toast';

interface ImageGeneratorProps {
  projectId: string;
  onImagesSelected: (images: GeneratedImage[]) => void;
  onImagesApproved?: (images: GeneratedImage[]) => void; // This is for approval workflow
}

interface PreviewImage {
  id: string;
  url: string;
  prompt: string;
  service: string;
  resolution?: string;
  steps?: number;
  seed?: number;
}

export const ImageGenerator: React.FC<ImageGeneratorProps> = ({ 
  projectId, 
  onImagesSelected 
}) => {
  const [prompt, setPrompt] = useState('');
  const [service, setService] = useState('stable_diffusion');
  const [resolution, setResolution] = useState('1024x1024');
  const [qualitySteps, setQualitySteps] = useState('25');
  const [numImages, setNumImages] = useState(2); // New: number of images to generate
  const [isGenerating, setIsGenerating] = useState(false);
  const [previewImages, setPreviewImages] = useState<PreviewImage[]>([]);
  const [existingImages, setExistingImages] = useState<GeneratedImage[]>([]);
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set());
  const [selectedForVideo, setSelectedForVideo] = useState<Set<string>>(new Set()); // NEW: Track video selection
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  // Modal state
  const [modalImage, setModalImage] = useState<{
    url: string;
    data: any;
  } | null>(null);

  // Load existing approved images
  useEffect(() => {
    loadExistingImages();
  }, [projectId]);

  const loadExistingImages = async () => {
    setIsLoading(true);
    try {
      console.log(`🔄 Loading images for project ${projectId}...`);
      
      // First, auto-cleanup any orphaned images
      console.log('🧹 Running auto-cleanup of orphaned images...');
      try {
        const cleanupResult = await projectsApi.cleanupOrphanedImages(projectId);
        
        if (cleanupResult.orphaned_removed > 0) {
          console.log(`Auto-cleanup removed ${cleanupResult.orphaned_removed} orphaned images`);
          toast.success(
            `🧹 Auto-cleanup: Removed ${cleanupResult.orphaned_removed} orphaned image${cleanupResult.orphaned_removed !== 1 ? 's' : ''} with missing files`,
            {
              duration: 4000,
              style: {
                background: '#f59e0b',
                color: 'white',
              }
            }
          );
        } else {
          console.log('No orphaned images found during auto-cleanup');
        }
        
        // Log details if any
        if (cleanupResult.orphaned_details && cleanupResult.orphaned_details.length > 0) {
          console.log('Orphaned image details:', cleanupResult.orphaned_details);
        }
        
      } catch (cleanupError) {
        console.warn('Auto-cleanup failed (non-critical):', cleanupError);
        toast.error('Auto-cleanup failed, but continuing with image loading', {
          duration: 3000
        });
        // Don't fail the whole operation if cleanup fails
      }
      
      // Then load the remaining valid images
      console.log('📥 Loading remaining valid images...');
      const images = await projectsApi.getImages(projectId);
      setExistingImages(images);
      
      console.log(`✅ Loaded ${images.length} valid images`);
      
      if (images.length === 0) {
        setShowGenerateForm(true);
        // ✅ FIXED: Use toast() with custom styling instead of toast.info()
        toast('💡 No images found. Generate some images to get started!', {
          duration: 3000,
          icon: 'ℹ️',
          style: {
            background: '#3b82f6',
            color: 'white',
          }
        });
      }
      
    } catch (error) {
      console.error('Failed to load images:', error);
      toast.error('Failed to load images. Please try refreshing.');
      setShowGenerateForm(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a prompt');
      return;
    }

    setIsGenerating(true);
    
    try {
      console.log(`Generating ${numImages} images...`);
      
      // Generate multiple preview images
      const generatedPreviews: PreviewImage[] = [];
      
      for (let i = 0; i < numImages; i++) {
        try {
          const imagePrompt: ImagePrompt = {
            prompt: prompt.trim(),
            service,
            size: resolution,
            quality: qualitySteps
          };

          console.log(`Generating image ${i + 1}/${numImages}:`, imagePrompt);
          
          const result = await projectsApi.generateImagePreview(projectId, imagePrompt);
          
          const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
          const fullImageUrl = result.preview_url.startsWith('http') 
            ? result.preview_url 
            : `${baseUrl}${result.preview_url}`;
          
          const previewImage: PreviewImage = {
            id: result.task_id,
            url: fullImageUrl,
            prompt: result.prompt,
            service: result.service,
            resolution: resolution,
            steps: parseInt(qualitySteps),
            seed: Math.floor(Math.random() * 1000000) + i // Simple seed variation
          };
          
          generatedPreviews.push(previewImage);
          console.log(`Generated preview ${i + 1}:`, previewImage);
          
        } catch (error) {
          console.error(`Failed to generate image ${i + 1}:`, error);
          toast.error(`Failed to generate image ${i + 1}`);
        }
      }
      
      if (generatedPreviews.length > 0) {
        setPreviewImages(prev => [...prev, ...generatedPreviews]);
        toast.success(`Generated ${generatedPreviews.length} image${generatedPreviews.length !== 1 ? 's' : ''}! Review and approve to add to collection.`);
      } else {
        toast.error('Failed to generate any images');
      }
      
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
      
      const approvedImage = await projectsApi.approveImage(projectId, previewId);
      console.log('Image approved:', approvedImage);
      
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
      const previewImage = previewImages.find(img => img.id === previewId);
      
      if (previewImage && previewImage.url.includes('/uploads/')) {
        console.log('Deleting rejected preview file:', previewImage.url);
        
        try {
          await projectsApi.deletePreviewImage(projectId, previewId);
        } catch (error) {
          console.error('Failed to delete preview file:', error);
        }
      }
      
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

  const handleVideoSelection = (imageId: string, isSelected: boolean) => {
    const newSelected = new Set(selectedForVideo);
    if (isSelected) {
      newSelected.add(imageId);
    } else {
      newSelected.delete(imageId);
    }
    setSelectedForVideo(newSelected);
    
    // Send the selected images to parent (Dashboard)
    const selectedImagesList = existingImages.filter(img => newSelected.has(img.id));
    onImagesSelected(selectedImagesList);
    
    if (selectedImagesList.length > 0) {
      toast.success(`${selectedImagesList.length} image${selectedImagesList.length !== 1 ? 's' : ''} selected for video`);
    }
  };

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

  const openModal = (imageUrl: string, imageData: any) => {
    setModalImage({ url: imageUrl, data: imageData });
  };

  const closeModal = () => {
    setModalImage(null);
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
              Select Images for Video ({existingImages.length} approved images available)
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
              const isSelectedForVideo = selectedForVideo.has(image.id);
              const imageUrl = getImageUrl(image);
              
              return (
                <div
                  key={image.id}
                  className={`border rounded-lg p-3 transition-all ${
                    isSelectedForVideo 
                      ? 'border-green-500 bg-green-50 shadow-md' 
                      : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
                  }`}
                >
                  {/* Video Selection Checkbox */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleVideoSelection(image.id, !isSelectedForVideo)}
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                          isSelectedForVideo 
                            ? 'border-green-500 bg-green-500' 
                            : 'border-gray-300 hover:border-green-400'
                        }`}
                      >
                        {isSelectedForVideo && (
                          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </button>
                      <span className="text-sm text-green-600 font-medium">
                        {isSelectedForVideo ? 'Selected for Video' : 'Select for Video'}
                      </span>
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
                  
                  {/* Image Display */}
                  <img
                    src={imageUrl}
                    alt={image.prompt}
                    className="w-full h-32 object-cover rounded-md mb-2 cursor-pointer hover:opacity-90 transition-opacity"
                    onClick={() => openModal(imageUrl, {
                      prompt: image.prompt,
                      service: image.generator_service,
                      resolution: image.generation_params?.size,
                      steps: image.generation_params?.quality,
                      seed: image.generation_params?.seed
                    })}
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

          {/* Selection Status - UPDATED */}
          {selectedForVideo.size > 0 ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <svg className="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="font-medium text-green-800">
                    {selectedForVideo.size} image{selectedForVideo.size !== 1 ? 's' : ''} selected for video
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
                    No images selected for video
                  </p>
                  <p className="text-sm text-yellow-600">
                    Please select images above to include in your video
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

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

              <div>
                <label htmlFor="numImages" className="block text-sm font-medium text-gray-700 mb-2">
                  Number of Images
                </label>
                <select
                  id="numImages"
                  value={numImages}
                  onChange={(e) => setNumImages(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value={1}>1 Image</option>
                  <option value={2}>2 Images</option>
                  <option value={3}>3 Images</option>
                  <option value={4}>4 Images</option>
                  <option value={6}>6 Images</option>
                </select>
              </div>
            </div>

            {service === 'stable_diffusion' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Resolution
                  </label>
                  <select 
                    value={resolution}
                    onChange={(e) => setResolution(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="512x512">512x512 (Fast)</option>
                    <option value="768x768">768x768 (Balanced)</option>
                    <option value="1024x1024">1024x1024 (High Quality)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Quality Steps
                  </label>
                  <select 
                    value={qualitySteps}
                    onChange={(e) => setQualitySteps(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="15">15 (Fast)</option>
                    <option value="25">25 (Balanced)</option>
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
                  <span>Generating {numImages} image{numImages !== 1 ? 's' : ''}...</span>
                </div>
              ) : (
                `Generate ${numImages} Image${numImages !== 1 ? 's' : ''}`
              )}
            </button>
          </div>
        </div>
      )}

      {/* Preview Images (Awaiting Approval) */}
      {previewImages.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Review Generated Images ({previewImages.length} pending approval)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {previewImages.map((image) => (
              <div key={image.id} className="bg-white border rounded-lg p-4">
                <div className="mb-3">
                  <img
                    src={image.url}
                    alt={image.prompt}
                    className="w-full h-48 object-cover rounded-md cursor-pointer hover:opacity-90 transition-opacity"
                    onClick={() => openModal(image.url, {
                      prompt: image.prompt,
                      service: image.service,
                      resolution: image.resolution,
                      steps: image.steps,
                      seed: image.seed
                    })}
                    onError={(e) => {
                      console.error('Preview image failed to load:', image.url);
                    }}
                  />
                </div>
                <p className="text-sm text-gray-700 mb-2 line-clamp-2">
                  "{image.prompt}"
                </p>
                <div className="text-xs text-gray-500 mb-3 space-y-1">
                  <div>Generated with {image.service}</div>
                  {image.resolution && <div>Resolution: {image.resolution}</div>}
                  {image.steps && <div>Steps: {image.steps}</div>}
                  {image.seed && <div>Seed: {image.seed}</div>}
                </div>
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
            Generate Your First Images
          </button>
        </div>
      )}

      {/* Image Modal */}
      {modalImage && (
        <ImageModal
          isOpen={true}
          onClose={closeModal}
          imageUrl={modalImage.url}
          imageData={modalImage.data}
        />
      )}
    </div>
  );
};