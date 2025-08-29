import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { AudioFile } from '../types';
import { projectsApi } from '../services/api';
import toast from 'react-hot-toast';

interface AudioUploadProps {
  projectId: string;
  onUploadComplete: (file: AudioFile) => void;
  maxFileSize?: number;
  acceptedFormats?: string[];
}

export const AudioUpload: React.FC<AudioUploadProps> = ({ 
  projectId, 
  onUploadComplete,
  maxFileSize = 100 * 1024 * 1024, // 100MB
  acceptedFormats = ['.mp3', '.wav', '.m4a', '.flac']
}) => {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<AudioFile | null>(null);

  const handleFileUpload = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    setIsUploading(true);
    setUploadProgress(0);
    
    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);
      
      const audioFile = await projectsApi.uploadAudio(projectId, file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setUploadedFile(audioFile);
      onUploadComplete(audioFile);
      
      toast.success('Audio file uploaded successfully!');
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'audio/mpeg': ['.mp3'],
      'audio/wav': ['.wav'],
      'audio/mp4': ['.m4a'],
      'audio/flac': ['.flac']
    },
    maxSize: maxFileSize,
    multiple: false,
    onDrop: handleFileUpload
  });

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (uploadedFile) {
    return (
      <div className="w-full max-w-2xl mx-auto">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <svg className="h-8 w-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-green-800 truncate">
                {uploadedFile.filename}
              </p>
              <p className="text-sm text-green-600">
                {uploadedFile.file_size_bytes && formatFileSize(uploadedFile.file_size_bytes)}
                {uploadedFile.duration_seconds && ` • ${Math.round(uploadedFile.duration_seconds)}s`}
              </p>
            </div>
            <button
              onClick={() => {
                setUploadedFile(null);
                onUploadComplete(null as any);
              }}
              className="text-green-600 hover:text-green-800"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        {isUploading ? (
          <div className="space-y-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="text-gray-600">Uploading... {uploadProgress}%</p>
          </div>
        ) : (
          <div className="space-y-4">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <div>
              <p className="text-xl font-medium text-gray-900">
                Drop your audio file here
              </p>
              <p className="text-gray-500">
                or click to browse ({acceptedFormats.join(', ')}) - max {formatFileSize(maxFileSize)}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
