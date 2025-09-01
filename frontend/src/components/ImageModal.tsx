// Create this as frontend/src/components/ImageModal.tsx

import React from 'react';

interface ImageModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string;
  imageData: {
    prompt: string;
    service: string;
    resolution?: string;
    seed?: number;
    steps?: number;
  };
}

export const ImageModal: React.FC<ImageModalProps> = ({ 
  isOpen, 
  onClose, 
  imageUrl, 
  imageData 
}) => {
  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg max-w-4xl max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold text-gray-900">Image Preview</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 p-2"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        {/* Image */}
        <div className="p-4">
          <img
            src={imageUrl}
            alt={imageData.prompt}
            className="max-w-full h-auto mx-auto rounded-lg shadow-lg"
            style={{ maxHeight: '70vh' }}
          />
        </div>
        
        {/* Image Details */}
        <div className="p-4 border-t bg-gray-50">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Generation Details</h3>
              <div className="space-y-1 text-sm text-gray-600">
                <div><span className="font-medium">Service:</span> {imageData.service}</div>
                {imageData.resolution && (
                  <div><span className="font-medium">Resolution:</span> {imageData.resolution}</div>
                )}
                {imageData.steps && (
                  <div><span className="font-medium">Steps:</span> {imageData.steps}</div>
                )}
                {imageData.seed && (
                  <div><span className="font-medium">Seed:</span> {imageData.seed}</div>
                )}
              </div>
            </div>
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Prompt</h3>
              <p className="text-sm text-gray-600 break-words">
                "{imageData.prompt}"
              </p>
            </div>
          </div>
        </div>
        
        {/* Actions */}
        <div className="flex justify-end space-x-3 p-4 border-t">
          <button
            onClick={() => {
              // Download image
              const link = document.createElement('a');
              link.href = imageUrl;
              link.download = `generated_image_${Date.now()}.png`;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Download
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};